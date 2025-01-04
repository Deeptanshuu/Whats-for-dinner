"""Known-item evaluation.

There are no ratings or click logs, so each test recipe becomes a query built
from its own ingredients. A ranker is good if it puts that recipe near the top.

Three query styles:

- ``typed``   four ingredients the way a person might type them: the bracketed
              alias half the time ("haldi"), otherwise singular/plural flipped
- ``exact``   four ingredients as the dataset spells them, alias removed
- ``pantry``  three quarters of the recipe plus ten other common ingredients

Recipes are split by id: even ids are for tuning, odd ids for reporting.
"""
from __future__ import annotations

import argparse
import json
import re
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Vocabulary, aliases, canonical, load_recipes, strip_alias

STYLES = ("typed", "exact", "pantry")
TOP_K = 6  # the app's first page
MIN_INGREDIENTS = 5
N_COMMON = 150


@dataclass
class Query:
    source: int  # row position in the catalogue
    style: str
    items: list[str]


def _rng(recipe_id: int, style: str) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(f"{style}:{recipe_id}".encode()))


def _flip_number(text: str) -> str:
    words = text.split()
    last = words[-1]
    low = last.lower()
    if low.endswith("ies"):
        last = last[:-3] + "y"
    elif low.endswith("ves"):
        last = last[:-3] + "f"
    elif low.endswith(("oes", "shes", "ches")):
        last = last[:-2]
    elif low.endswith("s") and not low.endswith("ss"):
        last = last[:-1]
    elif low.endswith("y") and low[-2:-1] not in "aeiou":
        last = last[:-1] + "ies"
    elif low.endswith("f"):
        last = last[:-1] + "ves"
    elif low.endswith(("o", "sh", "ch", "ss")):
        last = last + "es"
    else:
        last = last + "s"
    return " ".join(words[:-1] + [last])


def _raw_alias(raw: str, rng: np.random.Generator) -> str | None:
    """A bracketed name for the ingredient, skipping notes like '(Salted)'."""
    options = aliases(raw)
    return str(rng.choice(options)) if options else None


def build_queries(recipes: pd.DataFrame, vocab: Vocabulary, split: str = "test") -> dict[str, list[Query]]:
    """Queries for every recipe in the split, per style. Deterministic."""
    n = len(recipes)
    idf = {k: np.log(n / c) for k, c in vocab.counts.items()}
    common = [k for k, _ in vocab.counts.most_common(N_COMMON)]
    parity = 1 if split == "test" else 0
    out: dict[str, list[Query]] = {s: [] for s in STYLES}
    for pos, row in enumerate(recipes.itertuples()):
        if row.raw_id % 2 != parity:
            continue
        raws = list(dict.fromkeys(row.ingredients_raw))
        keys = [canonical(r) for r in raws]
        if len(set(keys)) < MIN_INGREDIENTS:
            continue
        # People name the distinctive things first, so sample by rarity.
        weights = np.array([idf.get(k, 0.0) + 1e-3 for k in keys])
        weights /= weights.sum()

        rng = _rng(row.raw_id, "pick")
        picked = [raws[i] for i in rng.choice(len(raws), size=4, replace=False, p=weights)]

        out["exact"].append(Query(pos, "exact", [strip_alias(r) for r in picked]))

        rng = _rng(row.raw_id, "typed")
        typed = []
        for raw in picked:
            alias = _raw_alias(raw, rng)
            if alias and rng.random() < 0.5:
                typed.append(alias.lower())
            elif rng.random() < 0.5:
                typed.append(_flip_number(strip_alias(raw)).lower())
            else:
                typed.append(strip_alias(raw).lower())
        out["typed"].append(Query(pos, "typed", typed))

        rng = _rng(row.raw_id, "pantry")
        keep = max(3, round(0.75 * len(raws)))
        have = [strip_alias(raws[i]) for i in rng.choice(len(raws), size=keep, replace=False)]
        extras = [k for k in common if k not in set(keys)]
        extra = [vocab.display[k] for k in rng.choice(extras, size=10, replace=False)]
        items = have + extra
        rng.shuffle(items)
        out["pantry"].append(Query(pos, "pantry", items))
    return out


def rank_of(scores: np.ndarray, source: int) -> float:
    """Rank of the source recipe. Ties share the middle of their block, which
    is the expected rank under a random tie-break."""
    s = scores[source]
    better = int((scores > s).sum())
    tied = int((scores == s).sum()) - 1
    return 1 + better + tied / 2


def evaluate(ranker, queries: list[Query]) -> dict[str, float]:
    ranks = np.array([rank_of(ranker.score(q.items), q.source) for q in queries])
    return {
        "hit@1": float((ranks <= 1).mean()),
        f"hit@{TOP_K}": float((ranks <= TOP_K).mean()),
        "hit@24": float((ranks <= 24).mean()),
        "mrr": float((1 / ranks).mean()),
        "n": int(len(ranks)),
    }


def run(rankers: dict, queries: dict[str, list[Query]]) -> pd.DataFrame:
    rows = []
    for name, ranker in rankers.items():
        for style in STYLES:
            rows.append({"ranker": name, "query": style, **evaluate(ranker, queries[style])})
    return pd.DataFrame(rows)


def to_markdown(results: pd.DataFrame, metric: str = f"hit@{TOP_K}") -> str:
    table = results.pivot(index="ranker", columns="query", values=metric)[list(STYLES)]
    table = table.loc[list(dict.fromkeys(results["ranker"]))]
    lines = ["| Ranker | " + " | ".join(STYLES) + " |", "|---|" + "---|" * len(STYLES)]
    for name, row in table.iterrows():
        lines.append(f"| {name} | " + " | ".join(f"{v:.1%}" for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    from .registry import build_rankers

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--split", default="test", choices=("test", "tune"))
    parser.add_argument("--rankers", nargs="*", help="subset of rankers to run")
    parser.add_argument("--out", help="write results as JSON")
    args = parser.parse_args()

    recipes = load_recipes()
    vocab = Vocabulary.build(recipes)
    queries = build_queries(recipes, vocab, args.split)
    rankers = build_rankers(recipes, vocab, only=args.rankers)
    results = run(rankers, queries)
    print(f"{len(recipes)} recipes, {results['n'].iloc[0]} {args.split} queries per style\n")
    for metric in ("hit@1", f"hit@{TOP_K}", "mrr"):
        print(metric)
        print(to_markdown(results, metric), "\n")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(results.to_dict("records"), fh, indent=2)


if __name__ == "__main__":
    main()
