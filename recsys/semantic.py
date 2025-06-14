"""Free-text recipe search ("something creamy and spicy with spinach").

Two searchers with the same interface:

- :class:`SemanticSearch`  MiniLM sentence embeddings (ONNX Runtime), cosine similarity
- :class:`TfidfSearch`     TF-IDF over the same text, the baseline

Both build one text per recipe with :func:`recipe_texts`. The embedding matrix
is cached in ``models/text_embeddings.npy`` (float16) with a JSON sidecar, and
is rebuilt only when the model file, the row count or the input text changes.

The model is the 8-bit quantised all-MiniLM-L6-v2 in ``models/minilm/`` run with
ONNX Runtime and the ``tokenizers`` package. No torch, no network at runtime.

Hindi: MiniLM is an English model and reads Devanagari as unknown tokens. Hindi
recipe names are "<hindi> - <English title>", so we keep the English part and
drop Devanagari descriptions. About 90 rows are Hindi after de-duplication.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .data import ROOT, strip_alias

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_DIR = ROOT / "models"
ONNX_DIR = MODEL_DIR / "minilm"
ONNX_PATH = ONNX_DIR / "model.onnx"
TOKENIZER_PATH = ONNX_DIR / "tokenizer.json"
MAX_SEQ_LENGTH = 256
EMB_PATH = MODEL_DIR / "text_embeddings.npy"
META_PATH = MODEL_DIR / "text_embeddings.json"

# Chosen by measurement on the tune split, see eval_semantic.py.
DEFAULT_FIELDS = ("title", "description", "cuisine", "course", "ingredients")
MAX_INGREDIENTS = 12

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_RECIPE_WORD = re.compile(r"\brecipes?\b", re.I)
_HINDI_NOTE = re.compile(r"\(\s*(recipes?\s+)?in hindi\s*\)", re.I)
_SPACES = re.compile(r"\s+")
_EDGE_PUNCT = " -:,"


def _clean(text: str) -> str:
    return _SPACES.sub(" ", text).strip(_EDGE_PUNCT)


def clean_title(name: str) -> str:
    """Drop Devanagari text, the word "Recipe" and "(In Hindi)" from a name."""
    name = _HINDI_NOTE.sub(" ", _DEVANAGARI.sub(" ", str(name)))
    return _clean(_RECIPE_WORD.sub(" ", name))


def clean_description(text: str) -> str:
    """Empty string for Hindi descriptions, which the model cannot read."""
    text = str(text)
    if not text:
        return ""
    if len(_DEVANAGARI.findall(text)) > 0.2 * len(text):
        return ""
    return _SPACES.sub(" ", text).strip()


def recipe_texts(recipes: pd.DataFrame, fields=DEFAULT_FIELDS) -> list[str]:
    """One searchable string per recipe from the chosen fields.

    Fields: title, description, cuisine, course, ingredients.
    """
    out = []
    for row in recipes.itertuples():
        parts = []
        if "title" in fields:
            parts.append(clean_title(row.name))
        if "cuisine" in fields and row.cuisine:
            parts.append(f"{row.cuisine}.")
        if "course" in fields and row.course:
            parts.append(f"{row.course}.")
        if "description" in fields:
            parts.append(clean_description(row.description))
        if "ingredients" in fields:
            names = list(dict.fromkeys(strip_alias(r) for r in row.ingredients_raw))[:MAX_INGREDIENTS]
            if names:
                parts.append("Ingredients: " + ", ".join(names) + ".")
        out.append(" ".join(p for p in parts if p))
    return out


_file_ids: dict[str, str] = {}


def _file_id(path: Path) -> str:
    """SHA-256 of a file, computed once per process."""
    key = str(path)
    if key not in _file_ids:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        _file_ids[key] = h.hexdigest()
    return _file_ids[key]


class OnnxEncoder:
    """Sentence embeddings from an ONNX MiniLM: tokenise, run, mean-pool, L2-normalise.

    The tokenizer and the session load on first use, so importing this module is cheap.
    """

    def __init__(self, model_path: Path = ONNX_PATH, tokenizer_path: Path = TOKENIZER_PATH,
                 max_length: int = MAX_SEQ_LENGTH):
        self.model_path = Path(model_path)
        self.tokenizer_path = Path(tokenizer_path)
        self.max_length = max_length
        self._tokenizer = None
        self._session = None
        self._input_names: set[str] = set()

    @property
    def identity(self) -> str:
        """Hash of the model file, part of the cache key."""
        return _file_id(self.model_path)

    def _load(self) -> None:
        if self._session is not None:
            return
        import onnxruntime as ort
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(str(self.tokenizer_path))
        tok.enable_truncation(max_length=self.max_length)
        tok.no_padding()  # pad per batch in encode()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        self._session = ort.InferenceSession(str(self.model_path), opts, providers=["CPUExecutionProvider"])
        self._input_names = {i.name for i in self._session.get_inputs()}
        self._tokenizer = tok

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        encs = self._tokenizer.encode_batch(texts)
        width = max(len(e.ids) for e in encs)
        ids = np.zeros((len(encs), width), dtype=np.int64)
        mask = np.zeros((len(encs), width), dtype=np.int64)
        for i, e in enumerate(encs):
            ids[i, :len(e.ids)] = e.ids
            mask[i, :len(e.ids)] = 1
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = np.zeros_like(ids)
        hidden = self._session.run(None, {k: v for k, v in feed.items() if k in self._input_names})[0]
        m = mask[:, :, None].astype(np.float32)
        pooled = (hidden * m).sum(axis=1) / np.maximum(m.sum(axis=1), 1e-9)
        return pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)

    def encode(self, texts: list[str], batch_size: int = 1) -> np.ndarray:
        """L2-normalised float32 embeddings, one row per text.

        The model is dynamically quantised, so an activation scale is set per batch and
        padding shifts a vector slightly (cosine about 0.995 between batch sizes). Batch
        size 1 needs no padding, is as fast on one thread, and makes a text encode the
        same way in the catalogue and as a query.
        """
        self._load()
        texts = list(texts)
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        # Sort by length so a larger batch pads little, then restore the order.
        order = np.argsort([len(t) for t in texts], kind="stable")
        parts = [self._encode_batch([texts[j] for j in order[i:i + batch_size]])
                 for i in range(0, len(texts), batch_size)]
        sorted_vecs = np.concatenate(parts).astype(np.float32)
        out = np.empty_like(sorted_vecs)
        out[order] = sorted_vecs
        return out


def _digest(texts: list[str], model_name: str) -> str:
    h = hashlib.sha256(model_name.encode())
    for t in texts:
        h.update(t.encode())
        h.update(b"\0")
    return h.hexdigest()


def _top_k(scores: np.ndarray, k: int, mask: np.ndarray | None):
    """Indices and scores of the k best rows, best first, honouring the mask."""
    scores = np.asarray(scores, dtype=np.float32)
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
        k = min(k, int(np.count_nonzero(mask)))
    k = min(k, len(scores))
    if k <= 0:
        return np.empty(0, dtype=int), np.empty(0, dtype=np.float32)
    top = np.argpartition(-scores, k - 1)[:k]
    top = top[np.argsort(-scores[top], kind="stable")]
    return top, scores[top]


class SemanticSearch:
    """Embed every recipe once, then rank by cosine similarity to the query.

    ``fields`` picks the text (see :func:`recipe_texts`). ``cache=False`` skips
    the files in ``models/``; use it for experiments with other fields.
    ``model_path`` and ``tokenizer_path`` default to the files in ``models/minilm/``.
    """

    name = "minilm"

    def __init__(self, recipes: pd.DataFrame, fields=DEFAULT_FIELDS, cache: bool = True,
                 model_name: str = MODEL_NAME, batch_size: int = 1,
                 model_path: Path = ONNX_PATH, tokenizer_path: Path = TOKENIZER_PATH):
        self.model_name = model_name
        self.fields = tuple(fields)
        self.texts = recipe_texts(recipes, self.fields)
        self.encoder = OnnxEncoder(model_path, tokenizer_path)
        self.matrix = self._load_or_build(cache, batch_size)

    def encode(self, texts: list[str], batch_size: int = 1) -> np.ndarray:
        """L2-normalised float32 embeddings."""
        return self.encoder.encode(texts, batch_size)

    def _load_or_build(self, cache: bool, batch_size: int) -> np.ndarray:
        digest = _digest(self.texts, f"{self.model_name}:{self.encoder.identity}")
        if cache and EMB_PATH.exists() and META_PATH.exists():
            try:
                meta = json.loads(META_PATH.read_text())
                if meta.get("hash") == digest and meta.get("rows") == len(self.texts):
                    return np.load(EMB_PATH).astype(np.float32)
            except (OSError, ValueError):
                pass  # unreadable cache, rebuild
        matrix = self.encode(self.texts, batch_size)
        if cache:
            MODEL_DIR.mkdir(exist_ok=True)
            np.save(EMB_PATH, matrix.astype(np.float16))
            meta = {"model": self.model_name, "rows": len(self.texts), "dim": int(matrix.shape[1]),
                    "fields": list(self.fields), "model_sha256": self.encoder.identity, "hash": digest}
            META_PATH.write_text(json.dumps(meta, indent=2))
        return matrix

    def score(self, text: str) -> np.ndarray:
        """Cosine similarity of the query to every recipe."""
        return self.matrix @ self.encode([text])[0]

    def search(self, text: str, k: int = 24, mask: np.ndarray | None = None):
        """Top-k row indices and scores. ``mask`` is a boolean array, True = allowed."""
        return _top_k(self.score(text), k, mask)


class TfidfSearch:
    """TF-IDF over the same text. Same interface, no model."""

    name = "tfidf_text"

    def __init__(self, recipes: pd.DataFrame, fields=DEFAULT_FIELDS, min_df: int = 2):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.texts = recipe_texts(recipes, fields)
        self.vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True, ngram_range=(1, 2),
                                          min_df=min_df, strip_accents="unicode")
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def score(self, text: str) -> np.ndarray:
        vec = self.vectorizer.transform([text])
        return np.asarray((self.matrix @ vec.T).todense()).ravel().astype(np.float32)

    def search(self, text: str, k: int = 24, mask: np.ndarray | None = None):
        return _top_k(self.score(text), k, mask)
