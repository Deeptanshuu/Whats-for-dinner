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
course, score`. `total_time` is whole minutes or `null`. The full recipe holds
`id, name, description, veg, image, prep_time, cook_time, total_time, course,
cuisine, cooking_ingredients, cooking_instruction`; the three times are whole
minutes or `null`. Cuisine and course names in a request are the group names
from `/api/meta` (for example `Indian` covers every regional label); `veg`
uses the cleaned veg flag, which drops "Vegetarian" rows that list meat or
eggs.

"More like this" and `liked` use the ingredient embedding vectors joined with
the text embeddings when both are available. If they are not, results fall
back to TF-IDF.

## Tests

```
python -m pytest
```
