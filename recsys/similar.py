"""More-like-this and a taste profile.

Every function takes an L2-normalised recipe matrix whose rows line up with the
catalogue. It can be text embeddings, ingredient vectors, or the blend from
:func:`combine`. With unit rows, a dot product is cosine similarity.
"""
from __future__ import annotations

import numpy as np


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norm == 0, 1.0, norm)


def _top(scores: np.ndarray, k: int):
    k = min(k, int(np.isfinite(scores).sum()))
    if k <= 0:
        return np.empty(0, dtype=int), np.empty(0, dtype=np.float32)
    top = np.argpartition(-scores, k - 1)[:k]
    top = top[np.argsort(-scores[top], kind="stable")]
    return top, scores[top]


def similar_recipes(matrix: np.ndarray, idx: int, k: int = 12, mask: np.ndarray | None = None):
    """Nearest neighbours of row ``idx``, not including ``idx``. Returns (indices, scores)."""
    scores = (matrix @ matrix[idx]).astype(np.float32)
    scores[idx] = -np.inf
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
    return _top(scores, k)


def combine(matrices, weights=None) -> np.ndarray:
    """Blend several matrices into one, e.g. ingredient + text.

    Each block is scaled by sqrt(weight) and the blocks are joined side by side,
    so the dot product of two rows is the weighted mean of the per-block cosines.
    Blocks must be L2-normalised and have the same rows. Dense output.
    """
    matrices = [m.toarray() if hasattr(m, "toarray") else np.asarray(m) for m in matrices]
    if weights is None:
        weights = [1.0] * len(matrices)
    if len(weights) != len(matrices):
        raise ValueError("one weight per matrix")
    if len({m.shape[0] for m in matrices}) != 1:
        raise ValueError("matrices must have the same number of rows")
    w = np.asarray(weights, dtype=np.float64)
    if (w < 0).any() or w.sum() == 0:
        raise ValueError("weights must be non-negative and not all zero")
    w = w / w.sum()
    blocks = [m.astype(np.float32) * np.float32(np.sqrt(wi)) for m, wi in zip(matrices, w) if wi > 0]
    return np.hstack(blocks)


def _scale(x: np.ndarray) -> np.ndarray:
    """Min-max to 0..1 over the finite values, so scores from different sources can be blended."""
    out = np.zeros_like(x, dtype=np.float32)
    ok = np.isfinite(x)
    if not ok.any():
        return out
    lo, hi = x[ok].min(), x[ok].max()
    out[ok] = (x[ok] - lo) / (hi - lo) if hi > lo else 0.0
    return out


class TasteProfile:
    """Running mean of the vectors of recipes a person liked."""

    def __init__(self, matrix: np.ndarray):
        self.matrix = matrix
        self._sum = np.zeros(matrix.shape[1], dtype=np.float64)
        self.liked: list[int] = []

    def like(self, idx: int) -> None:
        if idx in self.liked:
            return
        self.liked.append(idx)
        self._sum += self.matrix[idx]

    def unlike(self, idx: int) -> None:
        if idx in self.liked:
            self.liked.remove(idx)
            self._sum -= self.matrix[idx]

    def __len__(self) -> int:
        return len(self.liked)

    @property
    def vector(self) -> np.ndarray | None:
        """Unit-length mean of the liked vectors, or None before the first like."""
        if not self.liked:
            return None
        v = self._sum / len(self.liked)
        n = np.linalg.norm(v)
        return (v / n).astype(np.float32) if n > 0 else None

    def similarity(self) -> np.ndarray:
        """Cosine of every recipe to the taste vector (zeros if nothing is liked)."""
        v = self.vector
        if v is None:
            return np.zeros(len(self.matrix), dtype=np.float32)
        return (self.matrix @ v).astype(np.float32)

    def rerank(self, scores: np.ndarray, weight: float = 0.3, k: int = 12, diversity: float = 0.0,
               mask: np.ndarray | None = None, exclude_liked: bool = True):
        """Blend base scores with taste similarity and return the top k.

        Both parts are scaled to 0..1, then ``(1 - weight) * base + weight * taste``.
        ``diversity`` in 0..1 switches on MMR: each pick is penalised by its
        similarity to the picks so far, so the list is not ten versions of one
        dish. 0 is a plain sort. Returns (indices, blended scores).
        """
        if not 0 <= weight <= 1 or not 0 <= diversity <= 1:
            raise ValueError("weight and diversity must be between 0 and 1")
        scores = np.asarray(scores, dtype=np.float32)
        blended = (1 - weight) * _scale(scores) + weight * _scale(self.similarity())
        if mask is not None:
            blended = np.where(mask, blended, -np.inf)
        if exclude_liked and self.liked:
            blended[self.liked] = -np.inf
        if diversity == 0:
            return _top(blended, k)
        return self._mmr(blended, k, diversity)

    def _mmr(self, blended: np.ndarray, k: int, diversity: float):
        # Only the best few hundred can win a slot, so skip the rest.
        pool, _ = _top(blended, max(5 * k, 50))
        chosen: list[int] = []
        got: list[float] = []
        closest = np.full(len(pool), -1.0, dtype=np.float32)  # max sim to anything chosen
        left = np.ones(len(pool), dtype=bool)
        for _ in range(min(k, len(pool))):
            value = (1 - diversity) * blended[pool] - diversity * np.maximum(closest, 0)
            value[~left] = -np.inf
            best = int(np.argmax(value))
            chosen.append(int(pool[best]))
            got.append(float(blended[pool[best]]))
            left[best] = False
            sims = self.matrix[pool] @ self.matrix[pool[best]]
            closest = np.maximum(closest, sims)
        return np.array(chosen), np.array(got, dtype=np.float32)
