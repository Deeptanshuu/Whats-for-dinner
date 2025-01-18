import pytest

from recsys import taxonomy as tx


def test_every_label_in_the_data_is_mapped(recipes):
    missing_cuisine = {c for c in recipes["cuisine"].unique() if not tx.is_mapped(cuisine=c)}
    missing_course = {c for c in recipes["course"].unique() if not tx.is_mapped(course=c)}
    assert not missing_cuisine, missing_cuisine
    assert not missing_course, missing_course


def test_every_mapped_group_is_a_known_group():
    for label, groups in tx.CUISINE_MAP.items():
        assert groups <= set(tx.CUISINE_GROUPS), label
    assert set(tx.COURSE_MAP.values()) <= set(tx.COURSE_GROUPS)


def test_regional_labels_belong_to_indian_parent():
    assert tx.cuisine_groups("Kerala Recipes") == {"Indian", "South Indian"}
    assert tx.cuisine_groups("Punjabi") == {"Indian", "North Indian"}
    assert tx.cuisine_groups("Bengali Recipes") == {"Indian", "East & North-East Indian"}
    assert tx.cuisine_groups("Gujarati Recipes") == {"Indian", "West Indian"}
    assert tx.cuisine_groups("Indian") == {"Indian"}


def test_non_indian_labels():
    assert tx.cuisine_groups("Italian Recipes") == {"Italian"}
    assert tx.cuisine_groups("Indo Chinese") == {"Indian", "Chinese & East Asian"}
    assert tx.cuisine_groups("Asian") == {"Chinese & East Asian", "Thai & South-East Asian"}
    assert tx.cuisine_groups("") == {"Other"}
    assert tx.cuisine_groups("Martian") == {"Other"}


def test_course_groups():
    for label in ("Lunch", "Dinner", "Main Course", "One Pot Dish"):
        assert tx.course_group(label) == "Main Course"
    for label in ("World Breakfast", "South Indian Breakfast", "North Indian Breakfast", "Indian Breakfast", "Brunch"):
        assert tx.course_group(label) == "Breakfast"
    assert tx.course_group("Snack") == tx.course_group("Appetizer") == "Snack & Appetizer"
    assert tx.course_group("") == "Other"


def test_indian_parent_reaches_every_regional_recipe(recipes):
    counts = {o["name"]: o["count"] for o in tx.cuisine_options(recipes)}
    regional = counts["North Indian"] + counts["South Indian"] + counts["West Indian"] + \
        counts["East & North-East Indian"]
    assert counts["Indian"] >= regional
    assert counts["Indian"] > 4000  # the old substring match reached about 2,500


def test_course_counts_add_up_to_the_catalogue(recipes):
    assert sum(o["count"] for o in tx.course_options(recipes)) == len(recipes)


def test_resolve_ui_names():
    assert tx.resolve_cuisines(["Indian", "Italian"]) == {"Indian", "Italian"}
    assert tx.resolve_cuisines(["Japanese", "Thai"]) == {"Chinese & East Asian", "Thai & South-East Asian"}
    assert tx.resolve_cuisines(["Kerala Recipes"]) == {"Indian", "South Indian"}
    assert tx.resolve_cuisines(["Russian", "Vegan", ""]) == set()
    assert tx.resolve_course("Main Course") == "Main Course"
    assert tx.resolve_course("Breakfast") == "Breakfast"
    assert tx.resolve_course("Lunch") == "Main Course"
    assert tx.resolve_course("Soup") is None
    assert tx.resolve_course("") is None
