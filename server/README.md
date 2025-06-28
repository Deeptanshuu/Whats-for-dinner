# Recipe API

Flask API over the cleaned 7k recipe catalogue (`recsys/`). The catalogue and
rankers load once at start-up and stay in memory.

## Run

```
pip install -r requirements.txt
python -m server.app
```

| Variable | Default | Meaning |
|---|---|---|
| `HOST` | `127.0.0.1` | Interface to bind |
| `PORT` | `5000` | Port |
| `CORS_ORIGINS` | `*` | Comma separated allowed origins |
| `RECSYS_WARM` | `1` with `python -m server.app`, else `0` | Build the default ranker and the semantic index in a background thread at start-up |

`server/app.py` sets `OPENBLAS_NUM_THREADS` and `OMP_NUM_THREADS` to `1` (unless
already set) before numpy loads; small matrix products are much slower with
many BLAS threads.

Recipe ids are the row number in `data/recipes.csv`. Errors are JSON:
`{"error": "..."}` with status 400, 404, 405 or 500.

## Endpoints

| Method and path | Body or result |
|---|---|
| `POST /api/recommend` | `{ingredients, cuisine, course, veg, model, liked, limit}` returns `{recommendations, execution_time, model}`. At least one of ingredients, cuisine, course or liked is required. `limit` is 1 to 100, default 24. `model` defaults to `learned`. |
| `POST /api/search` | `{query, cuisine, course, veg, limit}` returns the same shape. `cuisine` and `course` boost matches, as in `/api/recommend`. |
| `GET /api/recipe/<id>` | Full recipe |
| `GET /api/recipe/<id>/similar?limit=` | `{recommendations, execution_time}`. `limit` is 1 to 48, default 12. |
| `GET /api/meta` | `{cuisines, courses, models, recipes}`; cuisines and courses are `{name, count}` groups, models are `{id, label}` |
| `GET /api/health` | `{status, recipes, ready: {ranker, search}}` |

Models, in order: `learned` (Learned ranker, the default), `embedding`
(Ingredient embeddings), `overlap` (Ingredient overlap), `tfidf` (TF-IDF).
Brute force is an offline evaluation baseline only and is not offered.

`execution_time` is measured in milliseconds. `model` in a response is the
model that really ran: if the asked model cannot be built it falls back to
`tfidf`.

`ready` shows whether the default ranker and the semantic index are built.
Before that, the first request that needs them pays the load time.

A recommendation card holds `id, title, total_time, image, veg, cuisine,
course, score, palette`. `total_time` is whole minutes or `null`. The full
recipe holds `id, name, description, veg, image, prep_time, cook_time,
total_time, course, cuisine, cooking_ingredients, cooking_instruction, palette,
ingredient_colors`; the three times are whole minutes or `null`. Cuisine and course names in a request are the group names
from `/api/meta` (for example `Indian` covers every regional label); `veg`
uses the cleaned veg flag, which drops "Vegetarian" rows that list meat or
eggs.

"More like this" and `liked` use the ingredient embedding vectors joined with
the text embeddings when both are available. If they are not, results fall
back to TF-IDF.

## Ingredient palette

The app shows no photos. Each recipe carries a `palette` instead: the colours
of its main ingredients, which the web app turns into a drawn cover: an
abstract plate seen from above (`web/src/cover/plate.js`). The first item is
the dish itself, the others are pieces on it sized by weight, and the item
names pick their shapes. The cover also reads the card's `title`, `course` and
`cuisine` to choose the vessel. The palette is built in `recsys/palette.py`.

```
"palette": [
  {"name": "Spinach Leaves", "color": "#47734a", "weight": 30},
  {"name": "Paneer", "color": "#e9dcb6", "weight": 21},
  {"name": "Tomato", "color": "#c65a41", "weight": 16}
]
```

- Up to 6 items, most characteristic first. `name` is the display name,
  `color` a hex colour, `weight` a whole percent; the weights add up to 100.
  About 300 bytes per card.
- An ingredient's weight is its family's role (1 for what the dish is made of,
  less for herbs, spices and fats) times its IDF over the catalogue, times a
  mild bonus for being listed early.
- Salt, water, oils, white sugar, vinegar and raising agents never appear.
- Colours come from a curated map of about 420 canonical ingredient names.
  Names not in the map fall back to a family colour by keyword (leafy greens,
  red chillies, pulses, grains and flours, dairy, meats, seafood, nuts, fruits
  and so on). Two ingredients with the same colour become one item.
- When fewer than 3 ingredients have a colour and the rest are unknown, one
  neutral item named `Other ingredients` (`#cdc6b8`) is added. The list is
  empty only when every ingredient is a staple.

The full recipe also has `ingredient_colors`: one entry for each ingredient in
`cooking_ingredients` (split on commas), in the same order, a hex colour or
`null` for staples and unknown ingredients.

Coverage of the catalogue (6,521 recipes, 75,216 ingredient uses): 79.1% of
uses hit a named colour, 2.7% a family fallback, 0.7% are unknown and 17.5%
are staples. Leaving staples out, that is 95.9% named, 3.2% family and 0.9%
unknown. 97.5% of recipes have at least 3 coloured ingredients.

## Tests

```
python -m pytest
```
