"""Builds every ranker by name so the evaluation and the API share one list."""
from __future__ import annotations

import pandas as pd

from .baselines import BruteForceRanker, TfidfRanker
from .data import Vocabulary


def build_rankers(recipes: pd.DataFrame, vocab: Vocabulary, only: list[str] | None = None) -> dict:
    builders = {
        "brute_force": lambda: BruteForceRanker(recipes),
        "tfidf": lambda: TfidfRanker(recipes),
    }
    names = only or list(builders)
    return {name: builders[name]() for name in names}
