import numpy as np
import pytest

from recsys.similar import TasteProfile, combine, similar_recipes


def unit(rows):
    m = np.asarray(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


@pytest.fixture
def matrix():
    # rows 0,1 close, row 2 near them, rows 3,4 a second cluster, row 5 apart
    return unit([[1, 0, 0], [0.95, 0.1, 0], [0.8, 0.5, 0], [0, 1, 0.1], [0, 0.98, 0.2], [0, 0, 1]])


def test_similar_excludes_self_and_orders(matrix):
    idx, scores = similar_recipes(matrix, 0, k=3)
    assert 0 not in idx
    assert list(idx[:2]) == [1, 2]
    assert np.all(np.diff(scores) <= 1e-6)


def test_similar_mask_and_small_k(matrix):
    mask = np.array([True, False, True, True, True, True])
    idx, _ = similar_recipes(matrix, 0, k=10, mask=mask)
    assert 1 not in idx and 0 not in idx and len(idx) == 4


def test_combine_scores_are_weighted_mean_of_cosines():
    a = unit([[1, 0], [0, 1], [1, 1]])
    b = unit([[1, 0, 0], [1, 0, 0], [0, 0, 1]])
    m = combine([a, b], [3, 1])
    assert m.shape == (3, 5)
    got = float(m[0] @ m[1])
    assert got == pytest.approx(0.75 * float(a[0] @ a[1]) + 0.25 * float(b[0] @ b[1]), abs=1e-6)
    assert float(m[0] @ m[0]) == pytest.approx(1.0, abs=1e-6)


def test_combine_rejects_bad_input():
    a = unit([[1, 0], [0, 1]])
    with pytest.raises(ValueError):
        combine([a, a], [1])
    with pytest.raises(ValueError):
        combine([a, unit([[1, 0]])])
    with pytest.raises(ValueError):
        combine([a], [0])


def test_profile_vector_is_mean_of_liked(matrix):
    p = TasteProfile(matrix)
    assert p.vector is None and len(p) == 0
    assert not p.similarity().any()
    p.like(0)
    p.like(1)
    p.like(1)  # liking twice counts once
    assert len(p) == 2
    expected = matrix[:2].mean(axis=0)
    expected /= np.linalg.norm(expected)
    assert np.allclose(p.vector, expected, atol=1e-6)
    p.unlike(1)
    assert np.allclose(p.vector, matrix[0], atol=1e-6)


def test_rerank_pulls_towards_taste(matrix):
    p = TasteProfile(matrix)
    p.like(0)
    base = np.array([0, 0, 0, 1.0, 0.9, 0.1], dtype=np.float32)  # base prefers the other cluster
    idx, _ = p.rerank(base, weight=0.0, k=2)
    assert list(idx) == [3, 4]
    idx, _ = p.rerank(base, weight=1.0, k=2)
    assert list(idx) == [1, 2]
    assert 0 not in idx  # liked recipe is left out
    idx, _ = p.rerank(base, weight=1.0, k=6, exclude_liked=False)
    assert idx[0] == 0


def test_rerank_without_likes_is_base_order(matrix):
    p = TasteProfile(matrix)
    base = np.array([0.1, 0.9, 0.5, 0.2, 0.3, 0.0], dtype=np.float32)
    idx, _ = p.rerank(base, weight=0.5, k=3)
    assert list(idx) == [1, 2, 4]


def test_rerank_mask(matrix):
    p = TasteProfile(matrix)
    p.like(5)
    mask = np.array([True, True, False, True, True, True])
    idx, _ = p.rerank(np.ones(6, dtype=np.float32), k=6, mask=mask)
    assert 2 not in idx


def test_diversity_spreads_across_clusters(matrix):
    p = TasteProfile(matrix)
    p.like(5)
    base = np.array([1.0, 0.99, 0.98, 0.9, 0.89, 0.0], dtype=np.float32)
    plain, _ = p.rerank(base, weight=0.0, k=3, diversity=0.0)
    assert list(plain) == [0, 1, 2]
    mixed, _ = p.rerank(base, weight=0.0, k=3, diversity=0.6)
    assert mixed[0] == 0
    assert set(mixed) & {3, 4}  # the second cluster gets a slot
    assert len(set(mixed)) == 3


def test_bad_weights(matrix):
    p = TasteProfile(matrix)
    with pytest.raises(ValueError):
        p.rerank(np.zeros(6), weight=1.5)
