"""Free-text recipe search ("something creamy and spicy with spinach").

Two searchers with the same interface:

- :class:`SemanticSearch`  MiniLM sentence embeddings, cosine similarity
- :class:`TfidfSearch`     TF-IDF over the same text, the baseline

Both build one text per recipe with :func:`recipe_texts`. The embedding matrix
is cached in ``models/text_embeddings.npy`` (float16) with a JSON sidecar, and
is rebuilt only when the model, the row count or the input text changes.

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
    """

    name = "minilm"

    def __init__(self, recipes: pd.DataFrame, fields=DEFAULT_FIELDS, cache: bool = True,
                 model_name: str = MODEL_NAME, batch_size: int = 64):
        self.model_name = model_name
        self.fields = tuple(fields)
        self.texts = recipe_texts(recipes, self.fields)
        self._model = None
        self.matrix = self._load_or_build(cache, batch_size)

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # slow import, keep it lazy

            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """L2-normalised float32 embeddings."""
        vecs = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)
        return vecs.astype(np.float32)

    def _load_or_build(self, cache: bool, batch_size: int) -> np.ndarray:
        digest = _digest(self.texts, self.model_name)
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
                    "fields": list(self.fields), "hash": digest}
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
