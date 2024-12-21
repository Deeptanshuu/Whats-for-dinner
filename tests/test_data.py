import pandas as pd
import pytest

from recsys.data import Vocabulary, aliases, canonical, is_vegetarian, load_recipes, singular, strip_alias

COLUMNS = ["name", "description", "cuisine", "course", "diet", "ingredients_name", "ingredients_quantity",
           "prep_time", "cook_time", "instructions", "image_url"]


def write_csv(tmp_path, rows):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "recipes.csv"
    frame.to_csv(path, index=False)
    return path


def row(name, ingredients, image, diet="Vegetarian", **extra):
    base = {"name": name, "description": "d", "cuisine": "Indian", "course": "Lunch", "diet": diet,
            "ingredients_name": ingredients, "ingredients_quantity": "", "prep_time": " 10 ", "cook_time": " 20 ",
            "instructions": "Cook.", "image_url": image}
    base.update(extra)
    return base


def test_singular_and_plurals():
    assert singular("tomatoes") == "tomato"
    assert singular("leaves") == "leaf"
    assert singular("onions") == "onion"
    assert singular("hummus") == "hummus"
    assert singular("chili") == "chilli"


def test_canonical_merges_spellings_and_drops_brackets():
    assert canonical("Turmeric powder (Haldi)") == "turmeric powder"
    assert canonical("Green Chillies") == canonical("green chilli")
    assert canonical("Tomatoes") == canonical("tomato")


def test_strip_alias_and_aliases():
    assert strip_alias("Turmeric powder (Haldi)") == "Turmeric powder"
    assert aliases("Curd (Dahi / Yogurt)") == ["dahi", "yogurt"]
    assert aliases("Butter (Salted)") == []


def test_vegetarian_label_with_chicken_is_not_veg():
    assert not is_vegetarian("Vegetarian", ["onion", "chicken breast"])
    assert not is_vegetarian("Vegetarian", ["egg", "flour"])


def test_vegetarian_keeps_eggplant_and_vegan_diets():
    assert is_vegetarian("Vegetarian", ["eggplant", "onion"])
    assert is_vegetarian("Vegan", ["tofu"])
    assert is_vegetarian("High Protein Vegetarian", ["lentil"])
    assert not is_vegetarian("Non Vegeterian", ["onion"])


def test_load_recipes_cleans_and_flags_veg(tmp_path):
    path = write_csv(tmp_path, [
        row("Dal", "Toor dal, Turmeric powder (Haldi), Tomatoes", "a.jpg"),
        row("Liar Curry", "Chicken, Onion", "b.jpg", diet="Vegetarian"),
        row("Vegan Bowl", "Tofu, Rice", "c.jpg", diet="Vegan"),
        row("Empty", "", "d.jpg"),
    ])
    df = load_recipes(path)
    assert list(df["name"]) == ["Dal", "Liar Curry", "Vegan Bowl"]
    assert list(df["raw_id"]) == [0, 1, 2]
    assert df.loc[0, "ingredients"] == ["toor dal", "turmeric powder", "tomato"]
    assert list(df["veg"]) == [True, False, True]
    assert df.loc[0, "total_time"] == 30


def test_dedupe_drops_hindi_copy_and_keeps_english(tmp_path):
    path = write_csv(tmp_path, [
        row("दाल रेसिपी", "Toor dal", "same.jpg"),
        row("Dal Recipe", "Toor dal", "same.jpg"),
        row("Other", "Rice", "other.jpg"),
    ])
    df = load_recipes(path)
    assert list(df["name"]) == ["Dal Recipe", "Other"]
    assert len(load_recipes(path, dedupe=False)) == 3


def test_vocabulary_resolves_aliases_and_plurals(tmp_path):
    path = write_csv(tmp_path, [
        row("A", "Turmeric powder (Haldi), Tomato", "1.jpg"),
        row("B", "Turmeric powder (Haldi), Onion", "2.jpg"),
    ])
    vocab = Vocabulary.build(load_recipes(path))
    assert vocab.resolve("haldi") == "turmeric powder"
    assert vocab.resolve("Tomatoes") == "tomato"
    assert vocab.resolve("unicorn") is None
    assert vocab.resolve_all(["haldi", "turmeric powder", "tomatoes"]) == ["turmeric powder", "tomato"]


def test_real_catalogue_has_no_duplicate_photos(recipes):
    assert not recipes["image_url"].duplicated().any()
    assert recipes["raw_id"].is_unique
    assert recipes["veg"].dtype == bool
