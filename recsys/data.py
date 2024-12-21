"""Load and clean the 7k recipe dataset.

The raw CSV has padded cells, bracketed ingredient aliases
("Turmeric powder (Haldi)"), mixed singular and plural spellings, and Hindi
copies of English recipes. Everything downstream works on the cleaned frame
returned by :func:`load_recipes`.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "recipes.csv"

_BRACKET = re.compile(r"\(([^)]*)\)")
_NON_WORD = re.compile(r"[^a-z0-9\s]")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Spelling variants that show up often enough to matter.
_SPELLING = {"chili": "chilli", "chile": "chilli", "chilly": "chilli", "yoghurt": "yogurt", "capsicums": "capsicum"}
_IRREGULAR = {"leaves": "leaf", "chillies": "chilli", "tomatoes": "tomato", "potatoes": "potato",
              "mangoes": "mango", "berries": "berry", "cherries": "cherry", "curries": "curry"}
_KEEP_S = {"asparagus", "hummus", "couscous", "molasses", "citrus", "swiss", "cress", "lemongrass",
           "gas", "watercress", "bass", "octopus", "hibiscus"}

# Bracketed notes that describe the ingredient instead of naming it.
_NOT_ALIASES = {"salted", "unsalted", "optional", "homemade", "bulb", "green", "fresh", "dried", "dry",
                "whole", "powder", "seed", "leaf", "chopped", "boiled", "raw", "ripe", "small", "big"}

VEG_DIETS = {"vegetarian", "high protein vegetarian", "vegan", "no onion no garlic (sattvic)"}
_NON_VEG_WORDS = ("chicken", "mutton", "fish", "prawn", "egg", "lamb", "pork", "beef", "bacon", "crab",
                  "shrimp", "meat", "ham", "salami", "sausage", "anchov", "squid", "tuna", "salmon")
_NOT_MEAT = ("eggplant", "eggless", "egg replacer", "egg free", "jackfruit", "hamburger bun")


def singular(word: str) -> str:
    """Cheap singular form. Good enough for ingredient nouns."""
    word = _SPELLING.get(word, word)
    if word in _IRREGULAR:
        return _IRREGULAR[word]
    if word in _KEEP_S or len(word) <= 3 or word.endswith("ss"):
        return word
    if word.endswith("s"):
        return word[:-1]
    return word


def canonical(text: str) -> str:
    """Key used to decide that two ingredient strings are the same thing."""
    text = _BRACKET.sub(" ", str(text).lower())
    text = _NON_WORD.sub(" ", text)
    return " ".join(singular(w) for w in text.split())


def strip_alias(text: str) -> str:
    """'Turmeric powder (Haldi)' -> 'Turmeric powder'."""
    return " ".join(_BRACKET.sub(" ", str(text)).split())


def aliases(text: str) -> list[str]:
    """'Curd (Dahi / Yogurt)' -> ['dahi', 'yogurt']."""
    out = []
    for group in _BRACKET.findall(str(text)):
        for part in re.split(r"[/&,]", group):
            key = canonical(part)
            if key and key not in _NOT_ALIASES:
                out.append(key)
    return out


def split_ingredients(cell) -> list[str]:
    if not isinstance(cell, str):
        return []
    return [part.strip() for part in cell.split(",") if part.strip()]


def is_vegetarian(diet: str, ingredient_keys: list[str]) -> bool:
    """Diet label says vegetarian and the ingredient list agrees."""
    if diet.strip().lower() not in VEG_DIETS:
        return False
    for key in ingredient_keys:
        if any(skip in key for skip in _NOT_MEAT):
            continue
        if any(word in key for word in _NON_VEG_WORDS):
            return False
    return True


def _minutes(value) -> float:
    try:
        return float(str(value).strip())
    except ValueError:
        return float("nan")


def load_recipes(path: str | Path | None = None, dedupe: bool = True) -> pd.DataFrame:
    """Return one row per recipe with cleaned text and parsed ingredients.

    ``dedupe`` drops rows that reuse another row's photo (Hindi copies of
    English recipes and a few plain repeats) and the remaining Hindi-only
    rows, whose description and steps have no English version.
    """
    if path is None:
        path = DATASET
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    for col in ("name", "description", "cuisine", "course", "diet", "instructions", "image_url"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["raw_id"] = df.index
    df["ingredients_raw"] = df["ingredients_name"].apply(split_ingredients)
    df["ingredients"] = df["ingredients_raw"].apply(
        lambda items: list(dict.fromkeys(k for k in map(canonical, items) if k)))
    df = df[df["ingredients"].str.len() > 0].copy()
    df["is_hindi"] = df["name"].str.contains(_DEVANAGARI)
    df["veg"] = [is_vegetarian(d, k) for d, k in zip(df["diet"], df["ingredients"])]
    df["total_time"] = df["prep_time"].apply(_minutes) + df["cook_time"].apply(_minutes)
    if dedupe:
        # English rows first so the Hindi copy is the one that goes.
        df = df.sort_values(["is_hindi", "raw_id"]).drop_duplicates("image_url")
        df = df[~df["is_hindi"]].sort_values("raw_id")
    return df.reset_index(drop=True)


@dataclass
class Vocabulary:
    """Canonical ingredients, their document frequency and known aliases."""

    counts: Counter = field(default_factory=Counter)
    alias_to_key: dict[str, str] = field(default_factory=dict)
    display: dict[str, str] = field(default_factory=dict)

    @classmethod
    def build(cls, recipes: pd.DataFrame) -> "Vocabulary":
        counts: Counter = Counter()
        alias_votes: dict[str, Counter] = defaultdict(Counter)
        names: dict[str, Counter] = defaultdict(Counter)
        for raw_items in recipes["ingredients_raw"]:
            seen = set()
            for raw in raw_items:
                key = canonical(raw)
                if not key or key in seen:
                    continue
                seen.add(key)
                counts[key] += 1
                names[key][strip_alias(raw)] += 1
                for alias in aliases(raw):
                    alias_votes[alias][key] += 1
        alias_to_key = {a: votes.most_common(1)[0][0] for a, votes in alias_votes.items() if a not in counts}
        display = {k: c.most_common(1)[0][0] for k, c in names.items()}
        return cls(counts=counts, alias_to_key=alias_to_key, display=display)

    def resolve(self, text: str) -> str | None:
        """Map what a person typed to a canonical ingredient, if we know it."""
        key = canonical(text)
        if key in self.counts:
            return key
        if key in self.alias_to_key:
            return self.alias_to_key[key]
        for alias in aliases(text):
            if alias in self.alias_to_key:
                return self.alias_to_key[alias]
        return None

    def resolve_all(self, items: list[str]) -> list[str]:
        out = []
        for item in items:
            key = self.resolve(item)
            if key and key not in out:
                out.append(key)
        return out
