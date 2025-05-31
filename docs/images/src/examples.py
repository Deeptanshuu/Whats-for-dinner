"""Collect the real example data drawn in the README images.

Run from the repo root:  python docs/images/src/examples.py
It loads the real Recommender, resolves the typed ingredients the same way the
rankers do, runs the learned ranker, free-text search and "more like this",
and writes docs/images/src/examples.json. Millisecond timings are added by
hand from the API (see build.mjs header), because they are measured there.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from recsys.data import canonical  # noqa: E402
from recsys.service import Recommender  # noqa: E402

TYPED = ["haldi", "paneer", "palak", "green chilly", "tomatoe"]
TEXT = "something creamy and spicy with spinach"

rec = Recommender()
learned = rec._ranker("learned")
idx = learned.features.index
vocab = idx.vocab


def how(item):
    key = canonical(item)
    if key in vocab.counts:
        return key, "exact name" if key == item.strip().lower() else "spelling and plural folding"
    if key in vocab.alias_to_key or vocab.resolve(item):
        return vocab.resolve(item), "alias"
    hit = idx.fuzzy.nearest(item)
    if hit and hit[1] >= idx.fuzzy.threshold:
        return hit[0], f"n-gram fuzzy ({hit[1]:.2f})"
    return None, "unresolved"


resolved = []
for item in TYPED:
    key, path = how(item)
    resolved.append({"typed": item, "canonical": key, "display": vocab.display.get(key, key), "via": path,
                     "recipes_with_it": int(vocab.counts.get(key, 0))})

cands, X, _ = learned.features.build(TYPED)
picks = rec.recommend(TYPED, limit=6)
for p in picks:
    pos = rec._pos[p["id"]]
    have = set(rec.recipes.iloc[pos]["ingredients"])
    p["matched"] = [r["canonical"] for r in resolved if r["canonical"] in have]
    p["n_ingredients"] = len(have)

search = rec.search(TEXT, limit=6)
similar = rec.similar(picks[0]["id"], limit=3)

out = {
    "catalogue": {"recipes": len(rec.recipes), "ingredients": len(vocab.counts),
                  "aliases": len(vocab.alias_to_key)},
    "ingredients_example": {"typed": TYPED, "resolved": resolved, "candidates": int(len(cands)),
                            "n_features": int(X.shape[1]), "top": picks},
    "search_example": {"query": TEXT, "top": search},
    "similar_example": {"source": picks[0]["title"], "source_id": picks[0]["id"], "top": similar},
    "shapes": {"ingredient_vectors": list(learned.features.embedding.table.shape),
               "recipe_ingredient_vectors": list(learned.features.embedding.recipe_vectors.shape),
               "text_matrix": list(rec._semantic_index().matrix.shape),
               "combined": list(rec._vectors().shape)},
}
path = Path(__file__).with_name("examples.json")
if path.exists():  # keep the hand-recorded API timings across re-runs
    old = json.loads(path.read_text())
    for key in ("api_timings", "search_eval"):
        if key in old:
            out[key] = old[key]
path.write_text(json.dumps(out, indent=2, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)))
print(json.dumps(out, indent=2, default=str))
