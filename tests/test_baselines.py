import pandas as pd

from recsys.baselines import BruteForceRanker, TfidfRanker

FRAME = pd.DataFrame({"ingredients_name": [
    "Paneer, Tomato, Cream",
    "Rice, Onion, Peas",
    "Paneer, Peas, Rice",
    "Chicken, Onion",
]})


def test_brute_force_counts_matches():
    scores = BruteForceRanker(FRAME).score(["paneer", "peas"])
    assert list(scores) == [1, 1, 2, 0]


def test_brute_force_ignores_case_and_punctuation():
    scores = BruteForceRanker(FRAME).score(["PANEER!", "Tomato."])
    assert list(scores) == [2, 0, 1, 0]


def test_brute_force_empty_query_scores_zero():
    assert BruteForceRanker(FRAME).score([]).sum() == 0


def test_tfidf_prefers_the_matching_recipe():
    ranker = TfidfRanker(FRAME)
    scores = ranker.score(["chicken", "onion"])
    assert scores.argmax() == 3
    assert scores[0] == 0


def test_tfidf_unknown_word_scores_zero():
    assert TfidfRanker(FRAME).score(["unicorn"]).sum() == 0


def test_scores_are_one_per_recipe(recipes):
    for ranker in (BruteForceRanker(recipes), TfidfRanker(recipes)):
        scores = ranker.score(["paneer", "tomato"])
        assert scores.shape == (len(recipes),)
        assert scores.max() > 0
