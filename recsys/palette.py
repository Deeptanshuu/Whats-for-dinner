"""A colour for each ingredient, and a small palette for each recipe.

The app cannot show recipe photos, so every recipe gets an abstract mark made
from the colours of its main ingredients. This module holds the data behind
it: a curated map from canonical ingredient names (see recsys.data.canonical)
to muted pigment colours, family fallbacks for names the map does not list,
and the rule that picks which ingredients stand for a recipe.

Nothing here needs more than the standard library.
"""
from __future__ import annotations

import math
from collections import Counter

from .data import Vocabulary, canonical

NEUTRAL = "#cdc6b8"
NEUTRAL_NAME = "Other ingredients"
MAX_ITEMS = 6

# family -> (fallback colour, role). The role says how much of the look of a
# dish an ingredient of that family carries: 1 for what the dish is made of,
# less for what only seasons it.
FAMILIES: dict[str, tuple[str, float]] = {
    "leafy greens": ("#4d7650", 1.0),
    "herbs": ("#7a9c5c", 0.6),
    "green chillies": ("#8fae52", 0.5),
    "green vegetables": ("#93ad6e", 1.0),
    "tomatoes": ("#c65a41", 1.0),
    "red chillies": ("#b0412f", 0.6),
    "yellow spices": ("#d6a028", 0.6),
    "brown spices": ("#8f6a45", 0.35),
    "aromatics": ("#d8c39a", 0.5),
    "vegetables": ("#c9b98a", 1.0),
    "root vegetables": ("#d6b77a", 1.0),
    "dairy": ("#eadfc3", 0.8),
    "fats": ("#e8cc74", 0.3),
    "coconut": ("#e6e1d3", 0.8),
    "pulses": ("#cfa24a", 1.0),
    "grains and flours": ("#dccaa2", 0.9),
    "meats": ("#c9937c", 1.0),
    "eggs": ("#ecc662", 1.0),
    "seafood": ("#9db1b6", 1.0),
    "nuts and seeds": ("#c3a070", 0.7),
    "fruits": ("#dc9a4e", 1.0),
    "souring": ("#6f4a30", 0.5),
    "sugars": ("#bd8238", 0.5),
    "chocolate": ("#513629", 1.0),
    "condiments": ("#a37c56", 0.5),
}

# family -> {canonical name: colour}. An empty colour means the family colour.
_CURATED: dict[str, dict[str, str]] = {
    "leafy greens": {
        "spinach leaf": "#47734a", "spinach": "#47734a", "baby spinach": "#47734a", "methi leaf": "#527a45",
        "green amaranth leaf": "#4f7d55", "drumstick leaf": "#557c48", "mooli ke patte": "#5c8550",
        "iceberg lettuce": "#b4cc96", "lettuce leaf": "#a5c285", "bok choy": "#8fb07a", "kale": "#3f6a4a",
        "colocasia leaf": "#4a7048", "mustard green": "#4f7a42", "dill leaf": "#6c9460",
    },
    "herbs": {
        "coriander leaf": "#6f9a56", "mint leaf": "#5f9468", "mint": "#5f9468", "curry leaf": "#58783f",
        "basil leaf": "#5d8a4d", "thai basil leaf": "#5d8a4d", "parsley leaf": "#6a9450", "kasuri methi": "#8a9562",
        "dried oregano": "#8f9869", "mixed herb": "#8f9869", "dry mix herb": "#8f9869", "italian seasoning": "#8f9869",
        "rosemary": "#6f8a68", "dried thyme leaf": "#8b9670", "fresh thyme leaf": "#78966a",
        "dried basil leaf": "#85946a", "fresh herb": "#6f9a56", "chive": "#6f9a56", "lemongrass": "#b3bf7c",
        "lemon grass": "#b3bf7c", "kaffir lime leaf": "#5c8748", "green chutney": "#6d9450",
        "homemade basil pesto": "#74914a", "spring onion": "#9dbb79", "spring onion green": "#84ab64",
        "leek": "#a9c489", "celery": "#a8c488",
    },
    "green chillies": {
        "green chilli": "#8fae52", "green chilli paste": "#8fae52", "green chilli sauce": "#8fae52",
        "pickled jalapeno": "#8a9e52",
    },
    "green vegetables": {
        "green bell pepper": "#6f9a58", "green pea": "#93b56b", "green bean": "#7da262", "cucumber": "#abc88e",
        "english cucumber": "#abc88e", "mangalorean cucumber": "#b9cc8e", "broccoli": "#5c8a52",
        "green zucchini": "#8aa866", "cabbage": "#c3d5a2", "bhindi": "#7e9d58", "okra": "#7e9d58",
        "bottle gourd": "#bcd0a0", "ridge gourd": "#9fb97c", "karela": "#6e8f4c", "tindora": "#8fae6a",
        "pointed gourd": "#94b072", "gawar phali": "#84a565", "avarekalu lilva bean": "#9ab873",
        "drumstick": "#8ea468", "avocado": "#a5b56a", "raw banana": "#a9b878", "raw papaya": "#bccb96",
        "jackfruit raw": "#b9b77a", "banana stem": "#d3d6b4", "vellai poosanikai": "#d3dcbc",
        "green grape": "#b5c574", "kiwi": "#96ad5a", "amla": "#b3c070", "asparagus": "#7da262",
    },
    "tomatoes": {
        "tomato": "#c65a41", "cherry tomato": "#c9523f", "homemade tomato puree": "#bf4f3a", "tomato puree": "#bf4f3a",
        "tomato ketchup": "#b5412f", "sun dried tomato": "#9c3f30", "roasted tomato pasta sauce": "#b9523a",
        "tomato basil pasta sauce": "#b9523a", "homemade pizza and pasta sauce": "#b9523a", "tomato salsa": "#c4563f",
        "red bell pepper": "#c24b3b", "red yellow and green bell pepper": "#cf7a3e",
        "red yellow or green bell pepper": "#cf7a3e", "yellow bell pepper": "#e2b53e", "orange bell pepper": "#de8f3c",
    },
    "red chillies": {
        "red chilli powder": "#b0412f", "dry red chilli": "#9a3829", "dried red chilli": "#9a3829",
        "kashmiri red chilli powder": "#b63a2c", "kashmiri dry red chilli": "#a3352a", "byadagi dried chilli": "#9e3628",
        "red chilli flake": "#ad4a35", "fresh red chilli": "#bd4233", "thai red chilli": "#bd4233",
        "paprika powder": "#b9502f", "cayenne pepper": "#b3452e", "red chilli sauce": "#b8432e",
        "sweet and spicy red chilli sauce": "#bf5236", "sriracha sauce": "#bd4a31", "schezwan sauce": "#a8402c",
        "tabasco original hot sauce": "#b4452f", "thai red curry paste": "#ad4a32",
    },
    "yellow spices": {
        "turmeric powder": "#d6a028", "saffron strand": "#df8a26", "curry powder": "#c99a34",
        "sambar powder": "#b8792f", "rasam powder": "#a9682f", "asafoetida": "#cdb37a", "ssp asafoetida": "#cdb37a",
        "amchur": "#c7ab72", "amchur powder": "#c7ab72", "dried mango powder": "#c7ab72", "dry ginger powder": "#cbb07c", "methi seed": "#b58f3e",
        "fenugreek seed": "#b58f3e", "methi powder": "#b58f3e", "yellow mustard seed": "#cfae4e",
        "english mustard sauce": "#cda63c", "dijon mustard": "#c9a54a", "custard powder": "#ecd27a",
    },
    "brown spices": {
        "cumin seed": "#96714a", "cumin": "#96714a", "cumin powder": "#96714a", "kala jeera": "#5e4a3a",
        "coriander powder": "#a98a5b", "coriander seed": "#b39a66", "garam masala powder": "#7a5236",
        "mustard seed": "#5a4638", "cinnamon stick": "#8c5a37", "cinnamon powder": "#9a6840", "cinnamon": "#8c5a37",
        "clove": "#5c3c2c", "whole black peppercorn": "#4b413b", "black pepper powder": "#5a4f47",
        "whole black pepper corn": "#4b413b", "whole black pepper": "#4b413b", "black pepper corn": "#4b413b",
        "white pepper powder": "#d6cbb2", "sichuan peppercorn": "#8a4a3c", "bay leaf": "#7e8762",
        "cardamom pod seed": "#9aa878", "cardamom powder": "#a9a67c", "cardamom": "#9aa878",
        "black cardamom": "#4f4038", "brown cardamom": "#4f4038", "fennel seed": "#a6ab6e", "fennel powder": "#a6ab6e",
        "ajwain": "#9c8a5c", "carom seed": "#9c8a5c", "star anise": "#6e4630", "nutmeg powder": "#8e6844",
        "nutmeg": "#8e6844", "mace": "#c0703c", "kalonji": "#3c3836", "chaat masala powder": "#9a7450",
        "pav bhaji masala": "#9c5a38", "panch phoran masala": "#8a7248", "maharashtrian goda masala": "#6a4a34",
        "tandoori masala": "#b0503a", "all spice powder": "#7a5238", "chinese 5 spice powder": "#7a5238",
        "stone flower": "#6a6258", "anardana powder": "#7c4038", "garlic powder": "#dccfae", "onion powder": "#d8c8a4",
        "vanilla extract": "#6a4a36",
    },
    "aromatics": {
        "onion": "#c79aa0", "red onion": "#b07a92", "pearl onion": "#c99aa3", "shallot": "#bd8f9c",
        "garlic": "#e4d9bd", "ginger": "#d1b47a", "ginger garlic paste": "#d6c090",
    },
    "vegetables": {
        "brinjal": "#62466b", "small brinjal": "#62466b", "eggplant": "#62466b", "purple cabbage": "#7d5578",
        "red cabbage": "#7d5578", "cauliflower": "#e9e2cb", "button mushroom": "#b9a690", "sweet corn": "#e9c552",
        "baby corn": "#e8d68a", "del monte whole corn kernel": "#e9c552", "kaddu": "#df9a40",
        "pumpkin puree": "#df9a40", "yellow zucchini": "#e3c65a", "mixed vegetable": "#a9b06a",
        "black olive": "#3f3a3c", "vegetable stock": "#c9b282",
    },
    "root vegetables": {
        "potato": "#d8bd84", "baby potato": "#d8bd84", "carrot": "#df8a3c", "beetroot": "#8c3050",
        "sweet potato": "#d68a55", "mooli mullangi": "#ebe7da", "elephant yam": "#b99a78", "colocasia root": "#b9a082",
    },
    "dairy": {
        "milk": "#efe8d6", "curd": "#ece6d6", "hung curd": "#ece6d6", "yogurt": "#ece6d6", "buttermilk": "#eee9da",
        "fresh cream": "#efe2c2", "cream": "#efe2c2", "heavy whipping cream": "#efe2c2", "double cream": "#efe2c2",
        "sour cream": "#ece4cf", "paneer": "#e9dcb6", "chenna": "#e9dcb6", "khoya": "#e3cfa2",
        "condensed milk": "#ecd9a8", "milk powder": "#ede2c4", "cheese": "#e6bd5e", "cheddar cheese": "#e3ad4c",
        "britannia cheese block": "#e6bd5e", "cheese spread": "#e8c672", "mozzarella cheese": "#ecdfb8",
        "parmesan cheese": "#e6d298", "feta cheese": "#ece7d6", "ricotta cheese": "#ece5d0",
        "britannia cream cheese": "#ece4cc", "mascarpone cheese": "#ece2c6", "goat cheese": "#ebe6d6",
        "classic mayonnaise": "#ece2c0", "tofu": "#e6dcc0",
    },
    "fats": {
        "ghee": "#e4c260", "butter": "#ead489", "nutralite classic spread": "#ead489",
        "nutralite garlic oregano spread": "#e2cf8c",
    },
    "coconut": {
        "fresh coconut": "#e6e1d3", "coconut": "#e6e1d3", "dessicated coconut": "#e8e3d4", "dry coconut": "#d9cbb0",
        "coconut milk": "#ebe5d6",
    },
    "pulses": {
        "white urad dal": "#e2d7bc", "black urad dal": "#4a4440", "chana dal": "#d3a440", "arhar dal": "#d8ad4c",
        "pigeon pea dal": "#d8ad4c", "yellow moong dal": "#dcba58", "green moong dal": "#84935a",
        "green moong sprout": "#a9b47c", "bean sprout": "#d9d6b8", "masoor dal": "#d88560", "pink masoor dal": "#d88560",
        "kabuli chana": "#d9c08a", "kala chana": "#6c4c38", "rajma": "#7e3c38", "black eyed bean": "#d9cba6",
        "black bean": "#3e3838", "horse gram dal": "#8a5a40", "roasted gram dal": "#d6bd7e", "gram flour": "#dbb65c",
        "besan": "#dbb65c", "soy chunk": "#c0a070", "soy granule": "#c0a070", "soybean": "#d6c48c", "badi": "#c9a868",
        "papad": "#dcc98c", "sev": "#e0b24a", "boondi": "#e0b24a",
    },
    "grains and flours": {
        "rice": "#ece6d5", "basmati rice": "#ece6d5", "cooked rice": "#ece6d5", "idli rice": "#ece6d5",
        "idli dosa batter": "#ebe5d2", "rice flour": "#ebe5d4", "poha": "#e8e1cc", "puffed rice": "#ebe5d2",
        "brown rice": "#b89a6c", "red matta rice": "#a8684e", "black rice": "#3c343a", "whole wheat flour": "#d2b888",
        "all purpose flour": "#eae2cc", "vivatta maida": "#eae2cc", "corn flour": "#ece3c2", "sooji": "#e6d5a6",
        "instant oat": "#d9c8a2", "rolled oat": "#d9c8a2", "rolled oat or instant oat": "#d9c8a2",
        "oat flour": "#d9c8a2", "muesli": "#cfb686", "ragi flour": "#7d5048", "ragi seed": "#7d5048",
        "bajra flour": "#a89a80", "jowar flour": "#d9cdb0", "makki ka atta": "#e6c868", "buckwheat flour": "#9a8672",
        "rajgira flour": "#dccb9e", "whole wheat brown bread": "#b98e5c", "whole wheat bread crumb": "#cfa66c",
        "baguette": "#d6b078", "burger bun": "#d2a468", "pav bun": "#d9b47a", "tortilla": "#e2cf9e",
        "whole wheat flour tortilla": "#cfb080", "corn flour tortilla": "#e3c878", "hard taco shell": "#e0b85a",
        "hakka noodle": "#e6d39a", "rice noodle": "#ebe5d2", "durum wheat spaghetti pasta": "#e3c888",
        "durum wheat penne pasta": "#e3c888", "semiya": "#dfc890", "quinoa": "#d9c9a0", "couscous": "#e2cf9a",
        "broken wheat": "#c9a874", "barley": "#d6c198", "foxtail millet": "#ddc680", "barnyard millet": "#e2d8bc",
        "sabudana": "#ebe7dc", "phool makhana": "#ebe6d8", "marie biscuit": "#d6b07a", "puff pastry sheet": "#e3cc94",
        "all purpose pie crust": "#e3cc94",
    },
    "meats": {
        "chicken": "#cf9c84", "chicken breast": "#d6a892", "boneless chicken": "#cf9c84", "chicken thigh": "#c98f78",
        "chicken stock": "#d6b680", "mutton": "#8f4a46",
    },
    "eggs": {"whole egg": "#ecc662", "egg white": "#efeadc", "egg yolk": "#e6b040"},
    "seafood": {
        "prawn": "#e29a84", "shrimp": "#e29a84", "fish": "#9db1b6", "fish fillet": "#9db1b6", "basa fish": "#b9c4c2",
        "fish sauce": "#8a5a3a",
    },
    "nuts and seeds": {
        "cashew nut": "#ddc8a0", "cashew": "#ddc8a0", "whole almond": "#b5875c", "almond": "#b5875c",
        "slivered almond": "#dccba8", "almond meal": "#d9c49c", "almond milk": "#ebe3d0", "roasted peanut": "#c4955e",
        "raw peanut": "#cfa67a", "peanut": "#c4955e", "peanut butter": "#bf8c50", "walnut": "#8a684a",
        "pistachio": "#a8b46c", "mixed nut": "#b99468", "dry fruit": "#a87c50", "pine nut": "#dccaa0",
        "sesame seed": "#dccfa8", "black sesame seed": "#3a3634", "tahini": "#cfb88a", "poppy seed": "#d6cdb6",
        "chia seed": "#56504c", "flax seed": "#8a6040", "flax seed powder": "#8a6040", "sunflower seed": "#b9ad94",
        "pumpkin seed": "#7c9060", "melon seed": "#e2dac4", "chironji": "#cfb690",
    },
    "fruits": {
        "mango": "#e8a63c", "mango pulp": "#e8a63c", "ripe banana": "#ecd380", "lemon": "#e2cd55",
        "lemon juice": "#e6d877", "lemon zest": "#e2cd55", "lemon wedge": "#e2cd55", "orange": "#e48e3c",
        "fresh orange juice": "#e8a04a", "orange zest": "#e48e3c", "apple": "#b84f44", "pineapple": "#e6c653",
        "strawberrie": "#c6485a", "cranberrie": "#9c3044", "fresh cherry": "#96283c", "blueberrie": "#4c4f7a",
        "fresh pomegranate fruit kernel": "#a8324c", "watermelon": "#d9606a", "papaya": "#e5924a",
        "apricot": "#e3a052", "plum": "#7a3a58", "fresh fig": "#7a4a62", "dried fig": "#8a6248", "date": "#6a4234",
        "prune": "#4a3038", "sultana raisin": "#8a5e30", "mixed fruit": "#dc9a4e", "fresh fruit": "#dc9a4e",
        "rose petal": "#c97a8c", "dried rose petal": "#b06a7c",
    },
    "souring": {
        "tamarind": "#6f4a30", "tamarind water": "#8a6240", "tamarind paste": "#6f4a30", "kokum": "#5a2c3c",
        "soy sauce": "#44302a", "dark soy sauce": "#3a2a26", "light soy sauce": "#6a4a36",
        "balsamic vinegar": "#4a3230",
    },
    "sugars": {
        "jaggery": "#b87830", "brown sugar": "#b98a5c", "palm sugar": "#b9824a", "honey": "#dba032",
        "maple syrup": "#b87a3a", "date syrup": "#6a4030",
    },
    "chocolate": {
        "cocoa powder": "#5a3a2c", "dark chocolate": "#46302a", "dark chocolate chip": "#46302a",
        "chocolate chip": "#513629", "chocolate bar": "#513629", "chocolate sauce": "#513629",
        "chocolate ganache": "#46302a", "nutella spread": "#5c3c2a", "instant coffee powder": "#5a3e2e",
        "white chocolate": "#ede2c4",
    },
    "condiments": {
        "red wine vinaigrette": "#9a4a48", "achari mayo": "#d9a85c", "del monte cheesy garlic mayo": "#ece2c0",
        "nutralite cheesy garlic mayo": "#ece2c0", "del monte mint mayo": "#b9cc9c", "sweet chutney": "#7a4a30",
    },
}

# A few ingredients carry less of a dish than their family suggests: dals used
# a spoonful at a time for tempering, juices, stock.
_ROLE = {"white urad dal": 0.4, "chana dal": 0.5, "roasted gram dal": 0.6, "lemon juice": 0.5, "lemon zest": 0.4,
         "lemon wedge": 0.4, "orange zest": 0.4, "vegetable stock": 0.4, "chicken stock": 0.4, "corn flour": 0.4,
         "rice flour": 0.6, "sultana raisin": 0.6, "milk powder": 0.5, "garlic powder": 0.3, "onion powder": 0.3}

SPECIFIC: dict[str, tuple[str, str]] = {
    name: (family, colour or FAMILIES[family][0])
    for family, names in _CURATED.items() for name, colour in names.items()
}

# Things that are in nearly every dish or that have no look of their own.
STAPLES = frozenset({
    "sugar", "caster sugar", "icing sugar", "decorative sugar", "baking powder", "baking soda", "cooking soda",
    "active dry yeast", "eno fruit salt", "ice cube", "ice", "crushed ice", "gelatin", "coal", "banana leaf", "vinegar", "white vinegar",
    "white wine vinegar", "apple cider vinegar", "rice vinegar", "chilli vinegar", "salt and pepper", "rose water",
    "rose essence", "kewra essence", "food color",
})
_STAPLE_WORDS = frozenset({"salt", "water", "oil", "yeast", "toothpick", "skewer", "foil"})

# Fallbacks for names the curated map does not list: the first rule with a
# word in the name wins, so the order matters ("coconut milk" before "milk").
_RULES: tuple[tuple[str, frozenset[str]], ...] = tuple((family, frozenset(words.split())) for family, words in (
    ("chocolate", "chocolate cocoa coffee nutella brownie"),
    ("green chillies", "jalapeno"),
    ("tomatoes", "tomato salsa marinara"),
    ("sugars", "sugar syrup jaggery honey caramel jam molasses gur gulkand"),
    ("coconut", "coconut"),
    ("leafy greens", "spinach palak methi amaranth lettuce kale greens arugula rocket saag chard"),
    ("nuts and seeds", "nut almond cashew peanut walnut pistachio pecan hazelnut sesame makhana groundnut"),
    ("seafood", "fish prawn shrimp crab squid tuna salmon anchovy anchovie seafood sardine mackerel pomfret"),
    ("meats", "chicken mutton lamb pork beef bacon meat ham sausage salami turkey keema"),
    ("eggs", "egg"),
    ("pulses", "dal bean lentil chana gram rajma sprout soy chickpea pea lobia moong matki"),
    ("grains and flours", "flour rice bread pasta noodle oat millet wheat atta bun tortilla poha vermicelli biscuit "
                          "cracker quinoa rava crumb pastry roti pita spaghetti macaroni penne dough batter cornmeal "
                          "polenta cereal cornflake maida paratha flake meal bran jowar bajra ragi idli semolina "
                          "loaf bagel lasagna pizza puri granola"),
    ("dairy", "cheese milk cream curd yogurt paneer mayo mayonnaise custard"),
    ("fats", "butter ghee margarine"),
    ("fruits", "mango banana lemon lime orange apple pineapple berry grape melon peach pear fig cherry fruit "
               "raisin apricot pomegranate guava litchi jackfruit zest peache raspberrie blackberrie "
               "raspberry strawberry plum chikoo"),
    ("herbs", "leaf herb basil parsley thyme oregano sage tarragon pesto chutney"),
    ("yellow spices", "turmeric saffron mustard"),
    ("red chillies", "chilli paprika cayenne harissa"),
    ("root vegetables", "potato carrot beet radish yam turnip root"),
    ("green vegetables", "gourd zucchini cucumber capsicum broccoli cabbage okra asparagus"),
    ("vegetables", "pumpkin squash mushroom corn brinjal cauliflower vegetable olive artichoke"),
    ("aromatics", "onion garlic ginger shallot"),
    ("souring", "tamarind vinegar"),
    ("condiments", "sauce ketchup dressing vinaigrette pickle"),
    ("brown spices", "masala powder spice seasoning seed pepper peppercorn"),
))


def classify(key: str) -> tuple[str, str | None, str | None]:
    """(kind, family, colour) for a canonical ingredient name.

    kind is "specific" (listed by name), "family" (matched by a fallback
    rule), "neutral" (unknown) or "staple" (left out of every palette).
    """
    if key in STAPLES:
        return "staple", None, None
    if key in SPECIFIC:
        family, colour = SPECIFIC[key]
        return "specific", family, colour
    words = set(key.split())
    if words & _STAPLE_WORDS:
        return "staple", None, None
    for family, hits in _RULES:
        if words & hits:
            return "family", family, FAMILIES[family][0]
    return "neutral", None, NEUTRAL


class Palette:
    """Picks the ingredients that stand for a recipe and gives each a colour.

    An ingredient's weight is role x IDF x a mild bonus for coming early in
    the list (recipes name their main ingredients first). The best few are
    kept, most characteristic first; two that share a colour become one band.
    """

    def __init__(self, vocab: Vocabulary, n_recipes: int):
        self.vocab = vocab
        self._idf = {k: math.log((n_recipes + 1) / (c + 1)) + 1.0 for k, c in vocab.counts.items()}
        self._idf_unknown = math.log(n_recipes + 1) + 1.0
        self._class: dict[str, tuple[str, str | None, str | None]] = {}

    def classify(self, key: str) -> tuple[str, str | None, str | None]:
        if key not in self._class:
            self._class[key] = classify(key)
        return self._class[key]

    def color(self, text: str) -> str | None:
        """Colour of one ingredient as written in a recipe; None for staples
        and for ingredients with no known colour."""
        kind, _, colour = self.classify(canonical(text))
        return colour if kind in ("specific", "family") else None

    def colors(self, raw_items: list[str]) -> list[str | None]:
        return [self.color(item) for item in raw_items]

    def for_recipe(self, keys: list[str], limit: int = MAX_ITEMS) -> list[dict]:
        """Up to ``limit`` items ``{name, color, weight}``. Weights are whole
        percents that add up to 100. Empty when every ingredient is a staple."""
        n = len(keys)
        scored, unknown = [], 0.0
        for pos, key in enumerate(keys):
            kind, family, colour = self.classify(key)
            if kind == "staple":
                continue
            early = 1.0 - 0.3 * (pos / (n - 1) if n > 1 else 0.0)
            idf = self._idf.get(key, self._idf_unknown)
            if kind == "neutral":
                unknown += 0.5 * idf * early
                continue
            role = _ROLE.get(key, FAMILIES[family][1])
            scored.append((role * idf * early, pos, key, colour))

        # Same colour, same band: keep the stronger name and add the weights.
        bands: dict[str, list] = {}
        for weight, pos, key, colour in sorted(scored, key=lambda s: (-s[0], s[1])):
            if colour in bands:
                bands[colour][0] += weight
            else:
                bands[colour] = [weight, pos, self.vocab.display.get(key, key), colour]
        items = sorted(bands.values(), key=lambda b: (-b[0], b[1]))[:limit]

        # Too few known colours: say so with one neutral band, not a guess.
        if len(items) < 3 and unknown > 0:
            items.append([unknown, n, NEUTRAL_NAME, NEUTRAL])
        if not items:
            return []
        shares = _percents([b[0] for b in items])
        return [{"name": b[2], "color": b[3], "weight": s} for b, s in zip(items, shares)]


def _percents(weights: list[float]) -> list[int]:
    """Whole percents that add up to exactly 100 (largest remainder)."""
    total = sum(weights)
    exact = [100.0 * w / total for w in weights]
    out = [int(x) for x in exact]
    order = sorted(range(len(exact)), key=lambda i: (out[i] - exact[i], i))
    for i in order[:100 - sum(out)]:
        out[i] += 1
    return out


def coverage(recipes, palette: Palette) -> dict:
    """How much of the catalogue the map covers. Used by the tests and docs."""
    kinds: Counter = Counter()
    coloured = []
    for keys in recipes["ingredients"]:
        found = [palette.classify(k)[0] for k in keys]
        kinds.update(found)
        coloured.append(sum(k in ("specific", "family") for k in found))
    total = sum(kinds.values())
    shown = total - kinds["staple"]
    return {
        "occurrences": total,
        "specific": kinds["specific"] / total,
        "family": kinds["family"] / total,
        "neutral": kinds["neutral"] / total,
        "staple": kinds["staple"] / total,
        "specific_of_shown": kinds["specific"] / shown,
        "family_of_shown": kinds["family"] / shown,
        "neutral_of_shown": kinds["neutral"] / shown,
        "recipes_with_3_coloured": sum(c >= 3 for c in coloured) / len(coloured),
    }
