import json
import re

import pytest

from recsys.data import split_ingredients
from recsys.palette import (FAMILIES, MAX_ITEMS, NEUTRAL, SPECIFIC, STAPLES, Palette, classify, coverage)

HEX = re.compile(r"^#[0-9a-f]{6}$")


@pytest.fixture(scope="module")
def palette(recipes, vocab):
    return Palette(vocab, len(recipes))


def test_colours_are_valid_and_families_known():
    assert HEX.match(NEUTRAL)
    assert all(HEX.match(colour) and 0 < role <= 1 for colour, role in FAMILIES.values())
    assert all(family in FAMILIES and HEX.match(colour) for family, colour in SPECIFIC.values())
    assert not STAPLES & set(SPECIFIC)


def test_curated_names_exist_in_the_catalogue(vocab):
    # A typo in the map would silently never match.
    assert [name for name in SPECIFIC if name not in vocab.counts] == []


@pytest.mark.parametrize("key, kind, family", [
    ("turmeric powder", "specific", "yellow spices"),
    ("spinach leaf", "specific", "leafy greens"),
    ("tomato", "specific", "tomatoes"),
    ("paneer", "specific", "dairy"),
    ("arhar dal", "specific", "pulses"),
    ("red amaranth leaf", "family", "leafy greens"),
    ("pomfret fish", "family", "seafood"),
    ("coconut sugar", "family", "sugars"),
    ("gouda cheese", "family", "dairy"),
    ("salt", "staple", None),
    ("extra virgin olive oil", "staple", None),
    ("lukewarm water", "staple", None),
    ("sugar", "staple", None),
    ("no such thing", "neutral", None),
])
def test_classify(key, kind, family):
    got_kind, got_family, colour = classify(key)
    assert (got_kind, got_family) == (kind, family)
    assert (colour is None) == (kind == "staple")


def test_coverage_of_the_real_catalogue(recipes, palette):
    stats = coverage(recipes, palette)
    assert stats["recipes_with_3_coloured"] > 0.95
    assert stats["specific_of_shown"] > 0.9
    assert stats["neutral_of_shown"] < 0.03
    assert abs(stats["specific"] + stats["family"] + stats["neutral"] + stats["staple"] - 1) < 1e-9


def test_every_recipe_gets_a_well_formed_palette(recipes, palette):
    empty = 0
    for keys in recipes["ingredients"]:
        items = palette.for_recipe(keys)
        empty += not items
        assert len(items) <= MAX_ITEMS
        if items:
            assert sum(i["weight"] for i in items) == 100
            assert all(set(i) == {"name", "color", "weight"} for i in items)
            assert all(i["name"] and HEX.match(i["color"]) and i["weight"] > 0 for i in items)
            colours = [i["color"] for i in items]
            assert len(set(colours)) == len(colours)
    assert empty / len(recipes) < 0.01


def test_staples_never_show(recipes, palette, vocab):
    names = {vocab.display[k] for k in ("salt", "oil", "water", "sugar")}
    for keys in recipes["ingredients"].head(1500):
        assert not names & {i["name"] for i in palette.for_recipe(keys)}
    assert palette.for_recipe(["salt", "water", "oil"]) == []


def test_deterministic_and_most_characteristic_first(recipes, vocab, palette):
    other = Palette(vocab, len(recipes))
    for keys in recipes["ingredients"].head(300):
        assert palette.for_recipe(keys) == other.for_recipe(keys) == palette.for_recipe(list(keys))
    keys = ["salt", "turmeric powder", "spinach leaf", "paneer", "onion", "tomato", "water"]
    items = palette.for_recipe(keys)
    assert [i["name"] for i in items][:2] == ["Spinach Leaves", "Paneer"]
    weights = [i["weight"] for i in items]
    assert weights == sorted(weights, reverse=True)


def test_similar_dishes_share_colours_and_different_ones_do_not(palette):
    def colours(keys):
        return {i["color"] for i in palette.for_recipe(keys)}

    palak = colours(["spinach leaf", "paneer", "tomato", "onion", "turmeric powder", "salt"])
    methi = colours(["methi leaf", "paneer", "tomato", "onion", "turmeric powder", "oil"])
    cake = colours(["all purpose flour", "cocoa powder", "whole egg", "butter", "sugar", "milk"])
    assert len(palak & methi) >= 3
    assert not palak & cake


def test_few_known_colours_degrade_to_a_neutral_band(palette):
    items = palette.for_recipe(["no such thing", "another unknown", "tomato"])
    assert [i["color"] for i in items] == ["#c65a41", NEUTRAL]
    assert items[-1]["name"] == "Other ingredients"


def test_same_colour_merges_into_one_band(palette):
    items = palette.for_recipe(["spinach leaf", "spinach", "tomato"])
    assert [i["color"] for i in items].count("#47734a") == 1


def test_card_payload(client):
    recs = client.post("/api/recommend", json={"ingredients": ["paneer", "spinach"], "limit": 60}).json["recommendations"]
    assert recs
    for card in recs:
        assert isinstance(card["palette"], list) and len(card["palette"]) <= MAX_ITEMS
        assert all(set(i) == {"name", "color", "weight"} for i in card["palette"])
    sizes = [len(json.dumps(c["palette"], separators=(",", ":"))) for c in recs]
    assert max(sizes) < 600 and sum(sizes) / len(sizes) < 400


def test_detail_payload(client, recommender):
    rid = client.post("/api/recommend", json={"ingredients": ["paneer", "spinach"], "limit": 1}).json["recommendations"][0]["id"]
    detail = client.get(f"/api/recipe/{rid}").json
    lines = split_ingredients(detail["cooking_ingredients"])
    assert len(detail["ingredient_colors"]) == len(lines)
    assert all(c is None or HEX.match(c) for c in detail["ingredient_colors"])
    assert detail["palette"] == recommender._card_rows[recommender._pos[rid]]["palette"]
    by_line = dict(zip(lines, detail["ingredient_colors"]))
    assert by_line.get("Salt", None) is None
