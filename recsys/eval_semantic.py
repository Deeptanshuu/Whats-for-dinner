"""Known-item evaluation of free-text search.

There are no human queries, so each test recipe makes its own query and a
searcher is good if it puts that recipe near the top. Two query styles:

- ``title``       the recipe title with the word "Recipe" removed, searched
                  against an index built WITHOUT the title (description plus
                  cuisine and course). Measures whether the description text
                  matches the dish name. Limits: descriptions usually repeat
                  the dish name, so word overlap makes this easy for TF-IDF;
                  titles are short and unlike real typed queries.
- ``paraphrase``  one natural sentence from cuisine, course and three or four
                  ingredient names ("A North Indian lunch with paneer, ..."),
                  sampled by rarity. Measures whether a loose description
                  finds the dish. Limits: when the index text holds cuisine,
                  course or ingredients, the query reuses the index's own
                  words, so scores are friendlier than real use.

Neither covers mood words ("creamy", "light"); those need human judgement.
Metrics: hit@1, hit@6 (the app's first page) and MRR. Even raw ids tune, odd
ids report, as in ``evaluate.py``.

    python -m recsys.eval_semantic            # test split, final index text
    python -m recsys.eval_semantic --select   # compare index texts on the tune split
"""
from __future__ import annotations

import argparse
import json
import re
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Vocabulary, canonical, load_recipes, strip_alias
from .evaluate import TOP_K, rank_of
from .semantic import DEFAULT_FIELDS, SemanticSearch, TfidfSearch, clean_description, clean_title

STYLES = ("title", "paraphrase")
MIN_INGREDIENTS = 5

# Index texts compared by --select. The title is dropped for the title queries.
VARIANTS = {
    "title+desc": ("title", "description"),
    "title+desc+cuisine+course": ("title", "description", "cuisine", "course"),
    "title+desc+ingredients": ("title", "description", "ingredients"),
    "title+desc+cuisine+course+ingredients": ("title", "description", "cuisine", "course", "ingredients"),
}


@dataclass
class Query:
    source: int
    style: str
    text: str


def _rng(recipe_id: int, tag: str) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(f"{tag}:{recipe_id}".encode()))


def _natural(cuisine: str, course: str, items: list[str]) -> str:
    cuisine = re.sub(r"\brecipes?\b", "", cuisine, flags=re.I).strip()
    base = " ".join(p for p in (cuisine, course.lower()) if p) or "A"
    lead = "An" if base[0].lower() in "aeiou" else "A"
    tail = ", ".join(items[:-1]) + " and " + items[-1]
    return f"{lead} {base} dish made with {tail}"


def build_queries(recipes: pd.DataFrame, vocab: Vocabulary, split: str = "test") -> dict[str, list[Query]]:
    n = len(recipes)
    idf = {k: np.log(n / c) for k, c in vocab.counts.items()}
    parity = 1 if split == "test" else 0
    out: dict[str, list[Query]] = {s: [] for s in STYLES}
    for pos, row in enumerate(recipes.itertuples()):
        if row.raw_id % 2 != parity:
            continue
        title = clean_title(row.name)
        if title and clean_description(row.description):
            out["title"].append(Query(pos, "title", title))
        raws = list(dict.fromkeys(strip_alias(r) for r in row.ingredients_raw))
        keys = [canonical(r) for r in raws]
        if len(set(keys)) >= MIN_INGREDIENTS and row.cuisine and row.course:
            w = np.array([idf.get(k, 0.0) + 1e-3 for k in keys])
            rng = _rng(row.raw_id, "para")
            size = int(rng.integers(3, 5))
            pick = rng.choice(len(raws), size=size, replace=False, p=w / w.sum())
            out["paraphrase"].append(Query(pos, "paraphrase", _natural(row.cuisine, row.course, [raws[i].lower() for i in pick])))
    return out


def evaluate(searcher, queries: list[Query]) -> dict[str, float]:
    ranks = np.array([rank_of(searcher.score(q.text), q.source) for q in queries])
    return {"hit@1": float((ranks <= 1).mean()), f"hit@{TOP_K}": float((ranks <= TOP_K).mean()),
            "mrr": float((1 / ranks).mean()), "n": int(len(ranks))}


def _fields_for(style: str, fields) -> tuple:
    """The title queries must not see the title in the index."""
    return tuple(f for f in fields if f != "title") if style == "title" else tuple(fields)


def run(recipes: pd.DataFrame, queries: dict[str, list[Query]], fields) -> pd.DataFrame:
    rows = []
    for style in STYLES:
        use = _fields_for(style, fields)
        searchers = {"minilm": SemanticSearch(recipes, use, cache=tuple(use) == tuple(DEFAULT_FIELDS)), "tfidf_text": TfidfSearch(recipes, use)}
        for name, s in searchers.items():
            rows.append({"searcher": name, "query": style, **evaluate(s, queries[style])})
    return pd.DataFrame(rows)


def to_markdown(results: pd.DataFrame, metric: str) -> str:
    table = results.pivot(index="searcher", columns="query", values=metric)[list(STYLES)]
    table = table.loc[list(dict.fromkeys(results["searcher"]))]
    lines = ["| Searcher | " + " | ".join(STYLES) + " |", "|---|" + "---|" * len(STYLES)]
    fmt = (lambda v: f"{v:.3f}") if metric == "mrr" else (lambda v: f"{v:.1%}")
    for name, row in table.iterrows():
        lines.append(f"| {name} | " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--split", default="test", choices=("test", "tune"))
    parser.add_argument("--select", action="store_true", help="compare index texts (use the tune split)")
    parser.add_argument("--out", help="write results as JSON")
    args = parser.parse_args()

    recipes = load_recipes()
    vocab = Vocabulary.build(recipes)
    if args.select:
        args.split = "tune"
    queries = build_queries(recipes, vocab, args.split)
    print(f"{len(recipes)} recipes; {args.split} queries: " + ", ".join(f"{s}={len(queries[s])}" for s in STYLES) + "\n")

    if args.select:
        all_rows = []
        for label, fields in VARIANTS.items():
            res = run(recipes, queries, fields)
            res.insert(0, "variant", label)
            all_rows.append(res)
        res = pd.concat(all_rows)
        print("| Index text | Searcher | title hit@1 | title hit@6 | title MRR | paraphrase hit@1 | paraphrase hit@6 | paraphrase MRR |")
        print("|---|---|---|---|---|---|---|---|")
        for (label, name), g in res.groupby(["variant", "searcher"], sort=False):
            t, p = g[g["query"] == "title"].iloc[0], g[g["query"] == "paraphrase"].iloc[0]
            print(f"| {label} | {name} | {t['hit@1']:.1%} | {t[f'hit@{TOP_K}']:.1%} | {t['mrr']:.3f} | "
                  f"{p['hit@1']:.1%} | {p[f'hit@{TOP_K}']:.1%} | {p['mrr']:.3f} |")
    else:
        res = run(recipes, queries, DEFAULT_FIELDS)
        print("Index text: " + "+".join(DEFAULT_FIELDS) + " (title removed for title queries)\n")
        for metric in ("hit@1", f"hit@{TOP_K}", "mrr"):
            print(metric)
            print(to_markdown(res, metric), "\n")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res.to_dict("records"), fh, indent=2)


if __name__ == "__main__":
    main()
