"""The recommender the API talks to.

Loads the catalogue once, keeps every lookup in memory and builds rankers on
first use. Learned, embedding and semantic parts are optional at run time: each
is built inside try/except and the service falls back to TF-IDF when one fails.
Brute force is not offered here; it is only an offline evaluation baseline.
"""
from __future__ import annotations

import threading

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from .data import Vocabulary, load_recipes, split_ingredients
from .palette import Palette
from .registry import build_rankers
from .taxonomy import (COURSE_GROUPS, CUISINE_GROUPS, course_group, course_options, cuisine_groups,
                       cuisine_options, resolve_course, resolve_cuisines)

# Boosts are added to a ranker score that is scaled to 0..1, so a cuisine or
# course match is worth 20 or 30 percent of a perfect ingredient match.
CUISINE_BOOST = 0.2
COURSE_BOOST = 0.3
TASTE_BOOST = 0.3

# Models offered, in order. The first is the default. All are built by
# recsys.registry.build_rankers.
MODELS = [
    {"id": "learned", "label": "Learned ranker"},
    {"id": "embedding", "label": "Ingredient embeddings"},
    {"id": "overlap", "label": "Ingredient overlap"},
    {"id": "tfidf", "label": "TF-IDF"},
]
MODEL_IDS = [m["id"] for m in MODELS]
DEFAULT_MODEL = "learned"
FALLBACK_MODEL = "tfidf"


class RecipeNotFound(LookupError):
    pass


def _minutes(value) -> int | None:
    """Whole minutes, or None when the value is missing."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(value) else int(round(value))


def _scale(scores: np.ndarray) -> np.ndarray:
    """Scale to 0..1 with the best score at 1.

    The learned ranker's raw scores can be negative, so those are shifted to
    start at 0 first. Rankers that never go below 0 are only divided by the
    best score, which keeps 0 meaning "no match".
    """
    scores = np.asarray(scores, dtype=np.float64)
    if not scores.size:
        return scores
    low = min(float(scores.min()), 0.0)
    span = float(scores.max()) - low
    return (scores - low) / span if span > 0 else np.zeros_like(scores)


class Recommender:
    def __init__(self, recipes: pd.DataFrame | None = None, path=None):
        self.recipes = load_recipes(path) if recipes is None else recipes.reset_index(drop=True)
        self.vocab = Vocabulary.build(self.recipes)
        df = self.recipes
        self._pos = {int(i): p for p, i in enumerate(df["raw_id"])}
        self._veg = df["veg"].to_numpy(dtype=bool)
        self._palette = Palette(self.vocab, len(df))
        self._card_rows = [{**self._card(row), "palette": self._palette.for_recipe(row.ingredients)}
                           for row in df.itertuples()]
        self._names = [str(n).strip().lower() for n in df["name"]]
        groups = [cuisine_groups(c) for c in df["cuisine"]]
        self._cuisine_mask = {g: np.array([g in s for s in groups]) for g in CUISINE_GROUPS}
        courses = [course_group(c) for c in df["course"]]
        self._course_mask = {g: np.array([c == g for c in courses]) for g in COURSE_GROUPS}
        self._lock = threading.RLock()
        self._rankers: dict = {}
        self._failed: set[str] = set()
        self._text_search = None
        self._semantic = None
        self._semantic_failed = False
        self._combined = None  # (key, matrix) for "more like this" and taste
        self._ready = {"ranker": False, "search": False}
        self._meta = None

    # ----- rows -----

    @staticmethod
    def _card(row) -> dict:
        return {
            "id": int(row.raw_id),
            "title": row.name,
            "total_time": _minutes(row.total_time),
            "image": row.image_url,
            "veg": bool(row.veg),
            "cuisine": row.cuisine,
            "course": row.course,
        }

    def _cards(self, positions, scores) -> list[dict]:
        return [{**self._card_rows[p], "score": round(float(s), 4)} for p, s in zip(positions, scores)]

    def _position(self, recipe_id: int) -> int:
        try:
            return self._pos[int(recipe_id)]
        except (KeyError, TypeError, ValueError):
            raise RecipeNotFound(f"No recipe with id {recipe_id}") from None

    def _pick(self, scores: np.ndarray, allowed: np.ndarray, limit: int, skip=()) -> tuple[list[int], list[float]]:
        """Best positions by score. Drops zeros, repeated titles and ``skip``."""
        ok = allowed & (scores > 0)
        cand = np.flatnonzero(ok)
        order = cand[np.lexsort((cand, -scores[cand]))]
        seen, pos, out = set(skip), [], []
        for p in order:
            name = self._names[p]
            if name in seen:
                continue
            seen.add(name)
            pos.append(int(p))
            out.append(float(scores[p]))
            if len(pos) >= limit:
                break
        return pos, out

    # ----- models -----

    def models(self) -> list[dict]:
        """Models the API can offer right now."""
        return [m for m in MODELS if m["id"] not in self._failed]

    def _ranker(self, name: str):
        with self._lock:
            if name in self._rankers:
                return self._rankers[name]
            if name in self._failed:
                return None
            try:
                self._rankers[name] = build_rankers(self.recipes, self.vocab, only=[name])[name]
            except Exception:
                if name == FALLBACK_MODEL:
                    raise
                self._failed.add(name)
                return None
            return self._rankers[name]

    def resolve_model(self, name: str) -> str:
        """The model that will really run. Falls back to tfidf when the asked one
        cannot be built."""
        if name not in MODEL_IDS:
            raise ValueError(f"Unknown model {name!r}")
        return name if self._ranker(name) is not None else FALLBACK_MODEL

    # ----- warm-up -----

    def warm(self) -> None:
        """Build the default ranker and the semantic index now, not on the first request."""
        try:
            self.resolve_model(DEFAULT_MODEL)
        finally:
            self._ready["ranker"] = True
        try:
            index = self._semantic_index()
            if index is not None:
                index.search("warm up", 1)  # loads the sentence model
            self._vectors()
        finally:
            self._ready["search"] = True

    def ready(self) -> dict:
        """Set by warm(); a request that builds the parts itself does not flip it."""
        with self._lock:
            return {
                "ranker": self._ready["ranker"],
                "search": self._ready["search"],
            }

    # ----- masks and boosts -----

    def _allowed(self, veg: bool) -> np.ndarray:
        return self._veg.copy() if veg else np.ones(len(self._veg), dtype=bool)

    def _group_boost(self, cuisine, course) -> tuple[np.ndarray, np.ndarray]:
        n = len(self._veg)
        cmask = np.zeros(n, dtype=bool)
        for g in resolve_cuisines(cuisine or []):
            cmask |= self._cuisine_mask[g]
        group = resolve_course(course or "")
        kmask = self._course_mask[group] if group else np.zeros(n, dtype=bool)
        return cmask, kmask

    def _taste(self, liked_pos: list[int]) -> np.ndarray:
        """How close each recipe is to what the person liked, 0..1."""
        matrix = self._vectors()
        if matrix is not None:
            try:
                from .similar import TasteProfile

                profile = TasteProfile(matrix)
                for p in liked_pos:
                    profile.like(p)
                return _scale(np.clip(profile.similarity(), 0, None))
            except Exception:
                pass
        # Fallback: mean TF-IDF vector of the liked recipes.
        ranker = self._ranker(FALLBACK_MODEL)
        centroid = np.asarray(ranker.matrix[liked_pos].mean(axis=0))
        sims = np.asarray(ranker.matrix @ centroid.T).ravel()
        return _scale(sims)

    # ----- public API -----

    def recommend(self, ingredients, cuisine=None, course=None, veg=False, model=DEFAULT_MODEL, liked=None,
                  limit=24) -> list[dict]:
        ingredients = [i for i in (ingredients or []) if str(i).strip()]
        liked_pos = [self._pos[int(i)] for i in (liked or []) if int(i) in self._pos]
        cmask, kmask = self._group_boost(cuisine, course)
        if not (ingredients or cmask.any() or kmask.any() or liked_pos):
            return []

        scores = np.zeros(len(self._veg))
        if ingredients:
            used = self.resolve_model(model)
            scores += _scale(self._ranker(used).score(ingredients))
        scores += CUISINE_BOOST * cmask + COURSE_BOOST * kmask
        if liked_pos:
            scores += TASTE_BOOST * self._taste(liked_pos)

        allowed = self._allowed(veg)
        allowed[liked_pos] = False
        pos, vals = self._pick(scores, allowed, limit)
        return self._cards(pos, vals)

    def search(self, text: str, veg: bool = False, limit: int = 24, cuisine=None, course=None) -> list[dict]:
        allowed = self._allowed(veg)
        cmask, kmask = self._group_boost(cuisine, course)
        boosted = cmask.any() or kmask.any()
        # With a boost, look at more candidates so a matching recipe a little
        # further down the text ranking can still come up.
        pool = max(limit * 3, 300) if boosted else limit * 3
        found = self._semantic_search(text, pool, allowed)
        if found is None:
            scores = self._text_scores(text)
        else:
            scores = np.zeros(len(allowed))
            scores[found[0]] = found[1]
        if boosted:
            base = _scale(np.where(allowed, scores, 0.0))
            scores = base + (CUISINE_BOOST * cmask + COURSE_BOOST * kmask) * (base > 0)
        pos, vals = self._pick(scores, allowed, limit)
        return self._cards(pos, vals)

    def recipe(self, recipe_id: int) -> dict:
        row = self.recipes.iloc[self._position(recipe_id)]
        return self._detail(row)

    def similar(self, recipe_id: int, limit: int = 12) -> list[dict]:
        pos = self._position(recipe_id)
        allowed = np.ones(len(self._veg), dtype=bool)
        allowed[pos] = False
        found = self._similar_found(pos, limit * 3, allowed)
        if found is None:
            ranker = self._ranker(FALLBACK_MODEL)
            scores = np.asarray((ranker.matrix @ ranker.matrix[pos].T).todense()).ravel()
        else:
            scores = np.zeros(len(allowed))
            scores[found[0]] = found[1]
        picked, vals = self._pick(scores, allowed, limit, skip=[self._names[pos]])
        return self._cards(picked, vals)

    def meta(self) -> dict:
        if self._meta is None:
            self._meta = {
                "cuisines": cuisine_options(self.recipes),
                "courses": course_options(self.recipes),
                "recipes": len(self.recipes),
            }
        return {**self._meta, "models": self.models()}

    # ----- detail -----

    def _detail(self, row) -> dict:
        card = self._card_rows[self._pos[int(row["raw_id"])]]
        return {
            "id": card["id"],
            "name": row["name"],
            "description": row["description"],
            "veg": card["veg"],
            "image": row["image_url"],
            "prep_time": _minutes(row["prep_time"]),
            "cook_time": _minutes(row["cook_time"]),
            "total_time": card["total_time"],
            "course": row["course"],
            "cuisine": row["cuisine"],
            "cooking_ingredients": str(row["ingredients_name"]) if pd.notna(row["ingredients_name"]) else "",
            "cooking_instruction": row["instructions"],
            "palette": card["palette"],
            # One entry per ingredient in cooking_ingredients, in the same order.
            "ingredient_colors": self._palette.colors(split_ingredients(row["ingredients_name"])),
        }

    # ----- semantic parts -----

    def _semantic_index(self):
        """The SemanticSearch index, built once. None if it cannot be built."""
        with self._lock:
            if self._semantic is None and not self._semantic_failed:
                try:
                    from .semantic import SemanticSearch

                    self._semantic = SemanticSearch(self.recipes)
                except Exception:
                    self._semantic_failed = True
            return self._semantic

    def _semantic_search(self, text: str, k: int, mask: np.ndarray):
        """(positions, scores) from the semantic index, or None to use TF-IDF."""
        index = self._semantic_index()
        if index is None:
            return None
        try:
            idx, sc = index.search(text, k, mask)
            return np.asarray(idx, dtype=int), np.asarray(sc, dtype=float)
        except Exception:
            return None

    def _vectors(self):
        """L2-normalised recipe matrix: ingredient vectors joined with text
        vectors when both exist, else whichever one does. None if neither."""
        ranker = self._ranker("embedding")
        ingredient = getattr(ranker, "recipe_vectors", None)
        index = self._semantic_index()
        text = getattr(index, "matrix", None)
        key = (id(ingredient), id(text))
        with self._lock:
            if self._combined is not None and self._combined[0] == key:
                return self._combined[1]
            try:
                if ingredient is not None and text is not None:
                    from .similar import combine

                    matrix = combine([ingredient, text])
                else:
                    matrix = ingredient if ingredient is not None else text
            except Exception:
                matrix = ingredient
            self._combined = (key, matrix)
            return matrix

    def _similar_found(self, pos: int, k: int, mask: np.ndarray):
        """(positions, scores) from the combined vectors, or None to use TF-IDF."""
        matrix = self._vectors()
        if matrix is None:
            return None
        try:
            from .similar import similar_recipes

            idx, sc = similar_recipes(matrix, pos, k, mask)
            return np.asarray(idx, dtype=int), np.asarray(sc, dtype=float)
        except Exception:
            return None

    def _text_scores(self, text: str) -> np.ndarray:
        """TF-IDF cosine over name and description. The search fallback."""
        with self._lock:
            if self._text_search is None:
                docs = [f"{n} {n} {d}" for n, d in zip(self.recipes["name"], self.recipes["description"])]
                vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
                self._text_search = (vec, vec.fit_transform(docs))
            vec, matrix = self._text_search
        q = vec.transform([text])
        return np.asarray((matrix @ q.T).todense()).ravel()
