import numpy as np

from recsys.evaluate import STYLES, Query, build_queries, evaluate, rank_of


def test_rank_of_no_ties():
    assert rank_of(np.array([0.1, 0.9, 0.5]), 2) == 2
    assert rank_of(np.array([0.1, 0.9, 0.5]), 1) == 1


def test_rank_of_ties_share_the_middle_of_their_block():
    # Four recipes tie at the top: expected rank is 2.5.
    assert rank_of(np.array([1.0, 1.0, 1.0, 1.0, 0.0]), 0) == 2.5
    # All tied: expected rank is the middle of the whole list.
    assert rank_of(np.zeros(5), 3) == 3


def test_queries_are_deterministic(recipes, vocab):
    a = build_queries(recipes, vocab, "test")
    b = build_queries(recipes, vocab, "test")
    for style in STYLES:
        assert [(q.source, q.items) for q in a[style]] == [(q.source, q.items) for q in b[style]]


def test_splits_are_disjoint_by_parity(recipes, vocab):
    test = build_queries(recipes, vocab, "test")
    tune = build_queries(recipes, vocab, "tune")
    odd = {recipes.loc[q.source, "raw_id"] % 2 for q in test["exact"]}
    even = {recipes.loc[q.source, "raw_id"] % 2 for q in tune["exact"]}
    assert odd == {1} and even == {0}


def test_query_shapes(recipes, vocab):
    queries = build_queries(recipes, vocab, "test")
    assert len(queries["typed"]) == len(queries["exact"]) == len(queries["pantry"]) > 1000
    assert all(len(q.items) == 4 for q in queries["exact"])
    assert all(len(q.items) >= 13 for q in queries["pantry"])


def test_evaluate_with_a_perfect_ranker():
    class Perfect:
        def score(self, items):
            out = np.zeros(10)
            out[int(items[0])] = 1
            return out

    result = evaluate(Perfect(), [Query(3, "exact", ["3"]), Query(7, "exact", ["7"])])
    assert result["hit@1"] == 1.0
    assert result["mrr"] == 1.0
    assert result["n"] == 2
