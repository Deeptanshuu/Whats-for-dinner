"""Learned ranker: LightGBM lambdarank over features from the cheap rankers.

For each query the cheap rankers each nominate their top recipes. The union
is the candidate set, and the model re-orders it. Training uses only queries
built from the tune split, with the source recipe as the single positive.
Part of tune is held out, by recipe, for early stopping.
"""
from __future__ import annotations

import json
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from .baselines import TfidfRanker
from .data import Vocabulary
from .embeddings import MODELS_DIR, EmbeddingRanker, OverlapRanker

MODEL_PATH = MODELS_DIR / "ranker.txt"
META_PATH = MODELS_DIR / "ranker.json"
SEED = 7
N_CANDIDATES = 50  # per cheap ranker, before the union

FEATURES = (
    "emb_cos", "tfidf_cos", "overlap",
    "matched", "query_cov", "recipe_cov", "idf_query_cov", "idf_recipe_cov",
    "soft_cov", "recipe_len", "extra", "n_items", "n_keys", "n_missing",
    "emb_gap", "tfidf_gap", "overlap_gap", "soft_gap",
)

LGB_PARAMS = {
    "objective": "lambdarank",
    "metric": "ndcg",
    "eval_at": [1, 6],
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambdarank_truncation_level": 20,
    "seed": SEED,
    "deterministic": True,
    "force_row_wise": True,
    "num_threads": 4,
    "verbosity": -1,
}


class FeatureBuilder:
    """Candidates and their feature rows for one query."""

    def __init__(self, recipes: pd.DataFrame, vocab: Vocabulary, embedding: EmbeddingRanker,
                 n_candidates: int = N_CANDIDATES, tfidf: TfidfRanker | None = None,
                 overlap: OverlapRanker | None = None):
        self.embedding = embedding
        self.index = embedding.index
        self.tfidf = tfidf or TfidfRanker(recipes)
        self.overlap = overlap or OverlapRanker(recipes, vocab, self.index)
        self.n_candidates = n_candidates

    def build(self, query: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (candidate rows, feature matrix, overlap scores for all rows)."""
        idx = self.index
        cols, missing = idx.resolve(query)

        tfidf = self.tfidf.score(query)
        matched, matched_idf = idx.matched(cols)
        overlap = self.overlap.score_matched(cols, matched_idf)
        emb = self.embedding.score_cols(cols)

        k = self.n_candidates
        picks = [_top(s, k) for s in (overlap, tfidf, emb)]
        cands = np.unique(np.concatenate(picks))

        n_keys = len(cols)
        q_idf = float(idx.idf[cols].sum()) if cols else 0.0
        r_len = idx.recipe_len[cands]
        m = matched[cands]
        m_idf = matched_idf[cands]
        soft = self._soft_coverage(cols, cands)

        cols_by_name = {
            "emb_cos": emb[cands],
            "tfidf_cos": tfidf[cands],
            "overlap": overlap[cands],
            "matched": m,
            "query_cov": m / max(n_keys, 1),
            "recipe_cov": m / np.maximum(r_len, 1),
            "idf_query_cov": m_idf / max(q_idf, 1e-6),
            "idf_recipe_cov": m_idf / np.maximum(idx.recipe_idf[cands], 1e-6),
            "soft_cov": soft,
            "recipe_len": r_len,
            "extra": r_len - m,
            "n_items": len(query),
            "n_keys": n_keys,
            "n_missing": missing,
        }
        # Gap to the best candidate for this query, so scores compare across queries.
        for name in ("emb", "tfidf", "overlap", "soft"):
            base = cols_by_name[{"emb": "emb_cos", "tfidf": "tfidf_cos", "overlap": "overlap", "soft": "soft_cov"}[name]]
            cols_by_name[f"{name}_gap"] = base - base.max()
        X = np.empty((len(cands), len(FEATURES)), dtype=np.float32)
        for j, name in enumerate(FEATURES):
            X[:, j] = cols_by_name[name]
        return cands, X, overlap

    def _soft_coverage(self, cols: list[int], cands: np.ndarray) -> np.ndarray:
        """IDF-weighted mean, over query ingredients, of the best cosine to any
        ingredient in the recipe. Exact matches count as 1."""
        if not cols:
            return np.zeros(len(cands), dtype=np.float32)
        table = self.embedding.table
        # Last column is the padding slot in index.padded.
        sims = np.full((len(cols), len(table) + 1), -1.0, dtype=np.float32)
        sims[:, :-1] = table[cols] @ table.T
        sims[np.arange(len(cols)), cols] = 1.0
        best = sims[:, self.index.padded[cands]].max(axis=2)  # (query, candidate)
        w = self.index.idf[cols] + 1e-3
        return (w @ best / w.sum()).astype(np.float32)


def _top(scores: np.ndarray, k: int) -> np.ndarray:
    k = min(k, len(scores))
    return np.argpartition(-scores, k - 1)[:k]


class LearnedRanker:
    """Scores every catalogue row. Rows outside the candidate set sit below
    every candidate, ordered among themselves by the overlap score."""

    name = "learned"

    def __init__(self, features: FeatureBuilder, booster, n_rows: int):
        self.features = features
        self.booster = booster
        self.n_rows = n_rows

    def score(self, query: list[str]) -> np.ndarray:
        cands, X, overlap = self.features.build(query)
        pred = self.booster.predict(X, num_threads=1)
        floor = float(pred.min()) - 2.0
        out = floor + 0.5 * overlap / max(float(overlap.max()), 1e-6)
        out[cands] = pred
        return out.astype(np.float32)


def _is_valid(source: int, valid_frac: float) -> bool:
    return zlib.crc32(f"valid:{source}".encode()) % 1000 < valid_frac * 1000


def build_dataset(features: FeatureBuilder, queries: list) -> dict:
    """Feature rows for a list of Query objects. Queries whose source is not
    among the candidates are counted and skipped."""
    Xs, ys, groups, sources = [], [], [], []
    missed = 0
    for q in queries:
        cands, X, _ = features.build(q.items)
        y = (cands == q.source).astype(np.float32)
        if not y.any():
            missed += 1
            continue
        Xs.append(X)
        ys.append(y)
        groups.append(len(cands))
        sources.append(q.source)
    return {"X": np.vstack(Xs), "y": np.concatenate(ys), "group": np.array(groups),
            "source": np.array(sources), "missed": missed, "total": len(queries)}


def train_ranker(features: FeatureBuilder, queries: list, valid_frac: float = 0.2,
                 params: dict | None = None, rounds: int = 2000):
    """Fit lambdarank on tune queries. Returns (booster, info)."""
    import lightgbm as lgb

    params = {**LGB_PARAMS, **(params or {})}
    data = build_dataset(features, queries)
    valid_q = np.array([_is_valid(s, valid_frac) for s in data["source"]])
    row_q = np.repeat(np.arange(len(data["group"])), data["group"])
    train_rows, valid_rows = ~valid_q[row_q], valid_q[row_q]

    def subset(rows, qmask):
        return lgb.Dataset(data["X"][rows], data["y"][rows], group=data["group"][qmask],
                           feature_name=list(FEATURES), free_raw_data=False)

    dtrain = subset(train_rows, ~valid_q)
    dvalid = subset(valid_rows, valid_q)
    booster = lgb.train(params, dtrain, num_boost_round=rounds, valid_sets=[dvalid], valid_names=["valid"],
                        callbacks=[lgb.early_stopping(100, verbose=False)])
    info = {
        "best_iteration": booster.best_iteration,
        "valid": {k: float(v) for k, v in booster.best_score["valid"].items()},
        "train_queries": int((~valid_q).sum()),
        "valid_queries": int(valid_q.sum()),
        "rows": int(len(data["y"])),
        "candidate_recall": 1 - data["missed"] / data["total"],
        "params": params,
    }
    return booster, info


def save_ranker(booster, info: dict, n_candidates: int, path: Path = MODEL_PATH, meta: Path = META_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(path), num_iteration=booster.best_iteration)
    importance = dict(zip(booster.feature_name(), booster.feature_importance("gain").round(1).tolist()))
    meta.write_text(json.dumps({**info, "features": list(FEATURES), "n_candidates": n_candidates,
                                "importance_gain": importance}, indent=2))


def load_ranker(path: Path = MODEL_PATH, meta: Path = META_PATH):
    """Return (booster, meta) or None if missing or built for other features."""
    import lightgbm as lgb

    if not (path.exists() and meta.exists()):
        return None
    info = json.loads(meta.read_text())
    booster = lgb.Booster(model_file=str(path))
    if booster.feature_name() != list(FEATURES):
        return None
    return booster, info
