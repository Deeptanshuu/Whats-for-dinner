import numpy as np
import pytest

from recsys.data import Vocabulary
from recsys.embeddings import (EmbeddingRanker, FuzzyMatcher, IngredientIndex, OverlapRanker, load_vectors,
                               save_vectors, train_vectors)

FAST = {"vector_size": 16, "epochs": 5}


@pytest.fixture(scope="module")
def small(recipes):
    """First 800 recipes with their own vocabulary, so training stays quick."""
    part = recipes.head(800).reset_index(drop=True)
    return part, Vocabulary.build(part)


@pytest.fixture(scope="module")
def vectors(small):
    return train_vectors(small[0], **FAST)


@pytest.fixture(scope="module")
def ranker(small, vectors):
    part, vocab = small
    return EmbeddingRanker(part, vocab, vectors)


def test_training_is_deterministic(small, vectors):
    again = train_vectors(small[0], **FAST)
    assert again.keys == vectors.keys
    np.testing.assert_array_equal(again.vectors, vectors.vectors)


def test_every_ingredient_gets_a_vector(small, vectors):
    _, vocab = small
    assert set(vocab.counts) == set(vectors.keys)


def test_save_and_load_round_trip(tmp_path, vectors):
    path = save_vectors(vectors, tmp_path / "vec.npz")
    loaded = load_vectors(path)
    assert loaded.keys == vectors.keys
    assert loaded.params == vectors.params
    np.testing.assert_allclose(loaded.vectors, vectors.vectors, atol=1e-2)


def test_scores_are_one_float32_per_recipe(small, ranker):
    part, _ = small
    scores = ranker.score(["onion", "tomato", "paneer"])
    assert scores.shape == (len(part),)
    assert scores.dtype == np.float32
    assert scores.max() <= 1.0 + 1e-5


def test_full_ingredient_list_finds_its_recipe(small, ranker):
    part, _ = small
    row = 10
    scores = ranker.score(list(part["ingredients"][row]))
    assert scores[row] == pytest.approx(scores.max(), abs=1e-5)


def test_unknown_query_scores_zero(ranker):
    assert not ranker.score(["qwzx unicorn"]).any()


def test_most_similar_excludes_itself(ranker):
    out = ranker.most_similar_ingredients("onion", k=5)
    assert len(out) == 5
    assert all(name.lower() != "onion" for name, _ in out)
    sims = [s for _, s in out]
    assert sims == sorted(sims, reverse=True)


def test_most_similar_unknown_is_empty(ranker):
    assert ranker.most_similar_ingredients("qwzx unicorn") == []


def test_fuzzy_matcher_fixes_near_misses(vocab):
    fuzzy = FuzzyMatcher(vocab, threshold=0.7)
    assert fuzzy.match("curry leave") == "curry leaf"
    assert fuzzy.match("green chilly") == "green chilli"
    assert fuzzy.match("qwzx") is None


def test_resolve_counts_what_it_cannot_place(small):
    part, vocab = small
    index = IngredientIndex(part, vocab)
    cols, missing = index.resolve(["onion", "Onions", "qwzx unicorn"])
    assert len(cols) == 1
    assert missing == 1


def test_overlap_prefers_the_exact_recipe(small):
    part, vocab = small
    ranker = OverlapRanker(part, vocab)
    row = 25
    scores = ranker.score(list(part["ingredients"][row]))
    assert scores.dtype == np.float32
    assert scores[row] == pytest.approx(scores.max())
