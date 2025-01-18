"""Cuisine and course groups for the filters.

The dataset has about 80 cuisine labels and 14 course labels. The old API
matched what the user clicked as a substring of the label, so "Indian" missed
"Kerala Recipes" and "Main Course" missed "Lunch". Here every label is mapped
by hand to the small set of groups the UI offers.

A cuisine label can sit in more than one group: "Kerala Recipes" is both
"South Indian" and "Indian". A course label sits in exactly one.
"""
from __future__ import annotations

import pandas as pd

OTHER = "Other"

INDIAN = "Indian"
NORTH = "North Indian"
SOUTH = "South Indian"
EAST = "East & North-East Indian"
WEST = "West Indian"
ITALIAN = "Italian"
EUROPEAN = "Continental & European"
AMERICAN = "American & Caribbean"
MEXICAN = "Mexican"
EAST_ASIAN = "Chinese & East Asian"
SE_ASIAN = "Thai & South-East Asian"
MIDDLE_EASTERN = "Middle Eastern"
AFRICAN = "African"
SOUTH_ASIAN = "Other South Asian"
FUSION = "Fusion"

# Order shown in the UI.
CUISINE_GROUPS = [INDIAN, NORTH, SOUTH, EAST, WEST, ITALIAN, EUROPEAN, AMERICAN, MEXICAN,
                  EAST_ASIAN, SE_ASIAN, MIDDLE_EASTERN, AFRICAN, SOUTH_ASIAN, FUSION, OTHER]

# Raw label -> the group it belongs to besides the parent "Indian".
_REGION = {
    NORTH: ["North Indian Recipes", "Punjabi", "Kashmiri", "Awadhi", "Mughlai", "Lucknowi", "Himachal",
            "Uttar Pradesh", "Uttarakhand-North Kumaon", "Haryana"],
    SOUTH: ["South Indian Recipes", "Kerala Recipes", "Tamil Nadu", "Karnataka", "Andhra", "Chettinad",
            "Mangalorean", "Coorg", "Udupi", "North Karnataka", "Coastal Karnataka", "South Karnataka",
            "Malabar", "Kongunadu", "Hyderabadi"],
    EAST: ["Bengali Recipes", "Oriya Recipes", "Assamese", "Bihari", "North East India Recipes", "Nagaland",
           "Jharkhand"],
    WEST: ["Maharashtrian Recipes", "Gujarati Recipes", "Goan Recipes", "Rajasthani", "Parsi Recipes",
           "Konkan", "Malvani", "Sindhi"],
}

# Raw label -> the full set of groups.
CUISINE_MAP: dict[str, frozenset[str]] = {"Indian": frozenset({INDIAN})}
for _group, _labels in _REGION.items():
    for _label in _labels:
        CUISINE_MAP[_label] = frozenset({INDIAN, _group})

for _group, _labels in {
    ITALIAN: ["Italian Recipes"],
    EUROPEAN: ["Continental", "French", "European", "British", "Swedish", "Greek", "Mediterranean"],
    AMERICAN: ["American", "Caribbean"],
    MEXICAN: ["Mexican"],
    EAST_ASIAN: ["Chinese", "Sichuan", "Cantonese", "Hunan", "Shandong", "Japanese", "Korean"],
    SE_ASIAN: ["Thai", "Vietnamese", "Indonesian", "Malaysian", "Burmese", "Singapore"],
    MIDDLE_EASTERN: ["Middle Eastern", "Arab", "Afghan", "Jewish"],
    AFRICAN: ["African"],
    SOUTH_ASIAN: ["Pakistani", "Nepalese", "Sri Lankan", "Bangladeshi"],
    FUSION: ["Fusion"],
}.items():
    for _label in _labels:
        CUISINE_MAP[_label] = frozenset({_group})

# Labels that belong to two worlds.
CUISINE_MAP["Indo Chinese"] = frozenset({INDIAN, EAST_ASIAN})
CUISINE_MAP["Asian"] = frozenset({EAST_ASIAN, SE_ASIAN})
CUISINE_MAP[""] = frozenset({OTHER})

MAIN = "Main Course"
BREAKFAST = "Breakfast"
SNACK = "Snack & Appetizer"
SIDE = "Side Dish"
DESSERT = "Dessert"

COURSE_GROUPS = [MAIN, BREAKFAST, SNACK, SIDE, DESSERT, OTHER]

COURSE_MAP: dict[str, str] = {
    "Lunch": MAIN, "Dinner": MAIN, "Main Course": MAIN, "One Pot Dish": MAIN,
    "World Breakfast": BREAKFAST, "South Indian Breakfast": BREAKFAST, "North Indian Breakfast": BREAKFAST,
    "Indian Breakfast": BREAKFAST, "Brunch": BREAKFAST,
    "Snack": SNACK, "Appetizer": SNACK,
    "Side Dish": SIDE,
    "Dessert": DESSERT,
    "": OTHER,
}

# Names the old UI sent that are not group names. Anything not listed here or
# in the group names is ignored, so Russian, Irish or Vegan add no boost.
_CUISINE_ALIASES = {
    "japanese": [EAST_ASIAN], "chinese": [EAST_ASIAN], "korean": [EAST_ASIAN], "asian": [EAST_ASIAN, SE_ASIAN],
    "thai": [SE_ASIAN], "vietnamese": [SE_ASIAN], "south-east asian": [SE_ASIAN],
    "american": [AMERICAN], "french": [EUROPEAN], "greek": [EUROPEAN], "british": [EUROPEAN],
    "mediterranean": [EUROPEAN], "continental": [EUROPEAN], "european": [EUROPEAN],
    "east indian": [EAST], "north-east indian": [EAST], "eastern indian": [EAST],
}
_COURSE_ALIASES = {
    "lunch": MAIN, "dinner": MAIN, "one pot dish": MAIN, "brunch": BREAKFAST,
    "snack": SNACK, "appetizer": SNACK, "starter": SNACK, "snacks": SNACK, "appetizers": SNACK,
    "side": SIDE, "sides": SIDE, "desserts": DESSERT, "sweet": DESSERT,
}


def cuisine_groups(label: str) -> set[str]:
    """Groups a raw cuisine label belongs to. Unknown labels fall in "Other"."""
    return set(CUISINE_MAP.get(str(label).strip(), {OTHER}))


def course_group(label: str) -> str:
    """Group a raw course label belongs to. Unknown labels fall in "Other"."""
    return COURSE_MAP.get(str(label).strip(), OTHER)


def is_mapped(cuisine: str | None = None, course: str | None = None) -> bool:
    """True when the label is listed explicitly, not caught by the fallback."""
    if cuisine is not None and str(cuisine).strip() not in CUISINE_MAP:
        return False
    if course is not None and str(course).strip() not in COURSE_MAP:
        return False
    return True


def resolve_cuisines(names: list[str]) -> set[str]:
    """Turn what the UI sent into group names. Raw dataset labels work too."""
    out: set[str] = set()
    by_lower = {g.lower(): g for g in CUISINE_GROUPS}
    for name in names:
        key = str(name).strip().lower()
        if key in by_lower:
            out.add(by_lower[key])
        elif key in _CUISINE_ALIASES:
            out.update(_CUISINE_ALIASES[key])
        else:
            labels = {k.lower(): k for k in CUISINE_MAP}
            if key in labels and key:
                out.update(CUISINE_MAP[labels[key]])
    return out


def resolve_course(name: str) -> str | None:
    """Group name for what the UI sent, or None when it means nothing here."""
    key = str(name or "").strip().lower()
    if not key:
        return None
    for group in COURSE_GROUPS:
        if key == group.lower():
            return group
    if key in _COURSE_ALIASES:
        return _COURSE_ALIASES[key]
    return None


def cuisine_options(recipes: pd.DataFrame) -> list[dict]:
    """Groups with the number of recipes in each, in UI order. Empty ones are left out."""
    counts = dict.fromkeys(CUISINE_GROUPS, 0)
    for label, n in recipes["cuisine"].value_counts().items():
        for group in cuisine_groups(label):
            counts[group] += int(n)
    return [{"name": g, "count": c} for g, c in counts.items() if c > 0]


def course_options(recipes: pd.DataFrame) -> list[dict]:
    counts = dict.fromkeys(COURSE_GROUPS, 0)
    for label, n in recipes["course"].value_counts().items():
        counts[course_group(label)] += int(n)
    return [{"name": g, "count": c} for g, c in counts.items() if c > 0]
