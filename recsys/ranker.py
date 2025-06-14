"""Learned ranker: LightGBM lambdarank over features from the cheap rankers.

For each query the cheap rankers each nominate their top recipes. The union
is the candidate set, and the model re-orders it. Training uses only queries
built from the tune split, with the source recipe as the single positive.
Part of tune is held out, by recipe, for early stopping.
"""
from __future__ import annotations

import json
import re
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


class TreeEnsemble:
    """LightGBM trees evaluated with NumPy only, so serving needs no lightgbm.

    Reads LightGBM's own text model. It handles what this model uses: numeric
    splits that go left when value <= threshold, leaf values that already
    include the learning rate, and a plain sum over all trees. Features must
    not be NaN. Every tree is flattened into one set of arrays, with leaves as
    nodes that point to themselves, and all rows walk all trees together.
    """

    def __init__(self, feature_names: list[str], feature: np.ndarray, threshold: np.ndarray,
                 left: np.ndarray, right: np.ndarray, value: np.ndarray, roots: np.ndarray, depth: int):
        self.feature_names = feature_names
        self.feature, self.threshold, self.left, self.right = feature, threshold, left, right
        self.value, self.roots, self.depth = value, roots, depth

    @classmethod
    def from_file(cls, path: Path) -> "TreeEnsemble":
        return cls.from_text(Path(path).read_text())

    @classmethod
    def from_text(cls, text: str) -> "TreeEnsemble":
        head, *blocks = re.split(r"^Tree=\d+\s*$", text, flags=re.M)
        names = re.search(r"^feature_names=(.*)$", head, re.M).group(1).split()
        feature, threshold, left, right, value, roots = [], [], [], [], [], []
        offset, depth = 0, 0
        for block in blocks:
            f = {k: v for k, v in re.findall(r"^(\w+)=(.*)$", block.split("end of trees")[0], re.M)}
            if int(f["num_cat"]) or f.get("is_linear", "0") != "0":
                raise ValueError("only numeric, non-linear trees are supported")
            n_leaves = int(f["num_leaves"])
            n_int = n_leaves - 1
            leaf_value = np.array(f["leaf_value"].split(), dtype=np.float64)
            roots.append(offset)
            if n_int == 0:  # a tree that is a single leaf
                feature.append([0]); threshold.append([np.inf]); left.append([offset]); right.append([offset])
                value.append(leaf_value[:1])
                offset += 1
                continue
            kinds = np.array(f["decision_type"].split(), dtype=np.int64)
            if (kinds & 1).any() or ((kinds >> 2) & 3).any():
                raise ValueError("categorical or missing-value splits are not supported")

            def child(c):  # internal node c >= 0, leaf ~c otherwise
                c = np.array(c.split(), dtype=np.int64)
                return np.where(c >= 0, c, n_int + (-c - 1)) + offset

            leaf_ids = np.arange(n_int, n_int + n_leaves) + offset
            feature.append(np.concatenate([np.array(f["split_feature"].split(), dtype=np.int64),
                                           np.zeros(n_leaves, dtype=np.int64)]))
            threshold.append(np.concatenate([np.array(f["threshold"].split(), dtype=np.float64),
                                             np.full(n_leaves, np.inf)]))
            left.append(np.concatenate([child(f["left_child"]), leaf_ids]))
            right.append(np.concatenate([child(f["right_child"]), leaf_ids]))
            value.append(np.concatenate([np.zeros(n_int), leaf_value]))
            offset += n_int + n_leaves
            depth = max(depth, _tree_depth(left[-1] - roots[-1], right[-1] - roots[-1], n_int))
        return cls(names, np.concatenate(feature), np.concatenate(threshold), np.concatenate(left),
                   np.concatenate(right), np.concatenate(value), np.array(roots), depth)

    def predict(self, X: np.ndarray, **_) -> np.ndarray:
        """Raw score per row: the sum of the leaf each tree sends the row to."""
        X = np.asarray(X, dtype=np.float64)
        if np.isnan(X).any():
            raise ValueError("features must not contain NaN")
        rows = np.arange(len(X))[None, :]
        node = np.repeat(self.roots[:, None], len(X), axis=1)
        for _ in range(self.depth):
            go_left = X[rows, self.feature[node]] <= self.threshold[node]
            node = np.where(go_left, self.left[node], self.right[node])
        return self.value[node].sum(axis=0)

    def feature_name(self) -> list[str]:
        return list(self.feature_names)


def _tree_depth(left: np.ndarray, right: np.ndarray, n_int: int) -> int:
    depth, level = 0, [0]
    while level:
        level = [c for n in level for c in (left[n], right[n]) if c < n_int]
        depth += 1
    return depth


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
        pred = self.booster.predict(X)
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
    """Return (trees, meta) or None if missing or built for other features.
    The trees run on NumPy alone; lightgbm is only needed to train."""
    if not (path.exists() and meta.exists()):
        return None
    info = json.loads(meta.read_text())
    trees = TreeEnsemble.from_file(path)
    if trees.feature_name() != list(FEATURES):
        return None
    return trees, info
