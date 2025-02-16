"""Train the ingredient embeddings and the learned ranker, write them to models/.

Only tune-split queries are used. The test split stays for
``python -m recsys.evaluate``.
"""
from __future__ import annotations

import argparse
import time

from .data import Vocabulary, load_recipes
from .embeddings import VECTORS_PATH, EmbeddingRanker, IngredientIndex, save_vectors, train_vectors
from .evaluate import build_queries
from .ranker import META_PATH, MODEL_PATH, N_CANDIDATES, FeatureBuilder, save_ranker, train_ranker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--candidates", type=int, default=N_CANDIDATES, help="top N per cheap ranker")
    args = parser.parse_args()

    recipes = load_recipes()
    vocab = Vocabulary.build(recipes)

    start = time.time()
    vectors = train_vectors(recipes)
    save_vectors(vectors)
    print(f"embeddings: {len(vectors)} ingredients, {vectors.params}, {time.time() - start:.1f}s")

    start = time.time()
    embedding = EmbeddingRanker(recipes, vocab, vectors, IngredientIndex(recipes, vocab))
    features = FeatureBuilder(recipes, vocab, embedding, n_candidates=args.candidates)
    queries = build_queries(recipes, vocab, "tune")
    booster, info = train_ranker(features, [q for qs in queries.values() for q in qs])
    save_ranker(booster, info, args.candidates)
    print(f"ranker: {info['best_iteration']} trees, {info['train_queries']} train / {info['valid_queries']} "
          f"held-out tune queries, candidate recall {info['candidate_recall']:.3f}, "
          f"held-out {info['valid']}, {time.time() - start:.1f}s")

    for path in (VECTORS_PATH, MODEL_PATH, META_PATH):
        print(f"{path.relative_to(path.parent.parent)}: {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
