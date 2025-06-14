"""Builds every ranker by name so the evaluation and the API share one list.

The embedding and learned rankers load their artefacts from models/ when they
are there (``python -m recsys.train`` writes them) and train in memory when
they are not.
"""
from __future__ import annotations

import pandas as pd

from .baselines import BruteForceRanker, TfidfRanker
from .data import Vocabulary
from .embeddings import VECTORS_PATH, EmbeddingRanker, IngredientIndex, OverlapRanker, load_vectors, train_vectors
from .ranker import FeatureBuilder, LearnedRanker, TreeEnsemble, load_ranker, train_ranker


class _Parts:
    """Builds shared pieces once, on first use."""

    def __init__(self, recipes: pd.DataFrame, vocab: Vocabulary):
        self.recipes = recipes
        self.vocab = vocab
        self._cache: dict = {}

    def get(self, name: str, make):
        if name not in self._cache:
            self._cache[name] = make()
        return self._cache[name]

    def brute(self):
        return self.get("brute", lambda: BruteForceRanker(self.recipes))

    def tfidf(self):
        return self.get("tfidf", lambda: TfidfRanker(self.recipes))

    def index(self):
        return self.get("index", lambda: IngredientIndex(self.recipes, self.vocab))

    def overlap(self):
        return self.get("overlap", lambda: OverlapRanker(self.recipes, self.vocab, self.index()))

    def embedding(self):
        def make():
            vectors = load_vectors() if VECTORS_PATH.exists() else train_vectors(self.recipes)
            return EmbeddingRanker(self.recipes, self.vocab, vectors, self.index())
        return self.get("embedding", make)

    def learned(self):
        def make():
            from .evaluate import build_queries

            loaded = load_ranker()
            if loaded is not None:
                booster, meta = loaded
                features = self._features(meta["n_candidates"])
            else:
                features = self._features()
                queries = build_queries(self.recipes, self.vocab, "tune")
                booster, _ = train_ranker(features, [q for qs in queries.values() for q in qs])
                booster = TreeEnsemble.from_text(booster.model_to_string(num_iteration=booster.best_iteration))
            return LearnedRanker(features, booster, len(self.recipes))
        return self.get("learned", make)

    def _features(self, n_candidates: int | None = None) -> FeatureBuilder:
        kwargs = {} if n_candidates is None else {"n_candidates": n_candidates}
        return FeatureBuilder(self.recipes, self.vocab, self.embedding(), tfidf=self.tfidf(),
                              overlap=self.overlap(), **kwargs)


def build_rankers(recipes: pd.DataFrame, vocab: Vocabulary, only: list[str] | None = None) -> dict:
    parts = _Parts(recipes, vocab)
    builders = {
        "brute_force": parts.brute,
        "tfidf": parts.tfidf,
        "overlap": parts.overlap,
        "embedding": parts.embedding,
        "learned": parts.learned,
    }
    names = only or list(builders)
    return {name: builders[name]() for name in names}
