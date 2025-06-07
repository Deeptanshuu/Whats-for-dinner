"""Two simple rankers, kept as baselines.

They take the raw strings a person typed and score every recipe, so they can
be measured next to the learned models.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

_CLEAN = re.compile(r"[^a-zA-Z0-9\s]")


def _preprocess(text: str) -> str:
    return _CLEAN.sub("", str(text).lower())


class BruteForceRanker:
    """Counts how many typed ingredients appear as substrings of the recipe's
    ingredient text."""

    name = "brute_force"

    def __init__(self, recipes: pd.DataFrame):
        self._texts = [_preprocess(t) for t in recipes["ingredients_name"].fillna("")]
        self._cache: dict[str, np.ndarray] = {}

    def _contains(self, needle: str) -> np.ndarray:
        hit = self._cache.get(needle)
        if hit is None:
            hit = np.fromiter((needle in t for t in self._texts), dtype=np.float32, count=len(self._texts))
            self._cache[needle] = hit
        return hit

    def score(self, query: list[str]) -> np.ndarray:
        total = np.zeros(len(self._texts), dtype=np.float32)
        for item in query:
            total += self._contains(_preprocess(item))
        return total


class TfidfRanker:
    """Binary TF-IDF over ingredient words with cosine similarity."""

    name = "tfidf"

    def __init__(self, recipes: pd.DataFrame):
        texts = recipes["ingredients_name"].fillna("").apply(lambda x: " ".join(str(x).strip().split(",")))
        self.vectorizer = TfidfVectorizer(binary=True)
        self.matrix = self.vectorizer.fit_transform(texts)

    def score(self, query: list[str]) -> np.ndarray:
        vec = self.vectorizer.transform([" ".join(query)])
        return np.asarray((self.matrix @ vec.T).todense()).ravel().astype(np.float32)
