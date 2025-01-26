"""Builds every ranker by name so the evaluation and the API share one list.

The embedding ranker loads its vectors from models/ when they are there and
trains in memory when they are not.
"""
from __future__ import annotations

import pandas as pd

from .baselines import BruteForceRanker, TfidfRanker
from .data import Vocabulary
from .embeddings import VECTORS_PATH, EmbeddingRanker, IngredientIndex, OverlapRanker, load_vectors, train_vectors


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


def build_rankers(recipes: pd.DataFrame, vocab: Vocabulary, only: list[str] | None = None) -> dict:
    parts = _Parts(recipes, vocab)
    builders = {
        "brute_force": parts.brute,
        "tfidf": parts.tfidf,
        "overlap": parts.overlap,
        "embedding": parts.embedding,
    }
    names = only or list(builders)
    return {name: builders[name]() for name in names}
