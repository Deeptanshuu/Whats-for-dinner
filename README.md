# What's for Dinner (RecipeSense)

Tell it what is in your kitchen, or describe what you feel like eating, and it
ranks 6,521 recipes for you.

It started as a college mini project with a TF-IDF keyword ranker. This
version cleans the ingredient data properly, learns a ranker on top of it, adds
free-text search with sentence embeddings, and measures all of it.

## What it does

| Feature | How |
|---|---|
| Search by ingredients | Typed ingredients are resolved to canonical names ("haldi", "turmeric powders" and "Turmeric powder (Haldi)" are one thing), cheap rankers pick candidates, a LightGBM `lambdarank` model re-orders them |
| Describe what you want | "something creamy and spicy with spinach" is embedded with `all-MiniLM-L6-v2` and matched against recipe text |
| More like this | Nearest recipes in a joint space of ingredient embeddings (skip-gram over recipes) and text embeddings |
| Likes | Liked recipes build a taste vector that re-ranks later results. Stored in the browser, no account |
| Filters | Vegetarian, cuisine and course, using grouped labels so "Indian" also covers Kerala, Punjabi, Bengali and the other regional labels |

## Results

There are no ratings or click logs, so the evaluation is known-item search: a
query is built from a held-out recipe's own ingredients, and a ranker scores
well if that recipe comes back near the top. Recipes are split by id, half for
tuning and training, half for reporting. 3,120 test queries per style.

Share of queries where the source recipe is in the top 6 (the app's first page):

| Ranker | typed | exact | pantry |
|---|---|---|---|
| Brute force (substring count) | 52.4% | 88.9% | 67.5% |
| TF-IDF (the original app) | 71.9% | 86.6% | 83.8% |
| Ingredient overlap on cleaned names | 93.1% | 97.5% | 95.7% |
| Ingredient embeddings alone | 77.0% | 83.5% | 37.5% |
| Learned ranker | **95.3%** | **97.4%** | **99.0%** |

Top-1 for the learned ranker is 80.5% / 85.5% / 95.3%, against 45.1% / 61.9% /
66.8% for TF-IDF.

- **typed**: four ingredients the way people type them, using the Hindi alias
  half the time and flipping singular and plural
- **exact**: four ingredients spelled as the dataset spells them
- **pantry**: three quarters of the recipe plus ten unrelated common ingredients

Free-text search, same split, 3,000+ queries per style:

| Searcher | title, top 6 | ingredient sentence, top 6 |
|---|---|---|
| TF-IDF over recipe text | 91.6% | 81.5% |
| MiniLM | 95.3% | 31.0% |

### What the numbers say

- Most of the gain is data cleaning. Resolving aliases and plurals takes typed
  queries from 72% to 93% before any model is trained.
- The learned ranker adds the rest, mostly on pantry queries (95.7% to 99.0%),
  where it learns to ignore ingredients the recipe does not use.
- Ingredient embeddings do not help ranking. Removing their features leaves the
  learned ranker's scores unchanged, and on their own they collapse on pantry
  queries because averaging in ten extra ingredients drags the query vector
  towards generic recipes. They are kept for "more like this" and
  similar-ingredient lookups, which is what co-occurrence vectors are good at.
- MiniLM is better at finding a dish from its name and worse than TF-IDF when
  the query is a list of ingredients. So ingredient search goes to the ranker
  and free text goes to MiniLM.
- Known-item search is a proxy. It measures whether the right recipe can be
  found, not whether people like the list. There are no human queries or
  judgements behind these numbers.

Reproduce:

```
python -m recsys.train          # embeddings and ranker, about 30 s
python -m recsys.evaluate       # ingredient rankers
python -m recsys.eval_semantic  # free-text search
```

## How it is built

```
data/recipes.csv
      |
recsys/data.py        clean, canonical ingredients, veg flag, drop duplicates
      |
      +-- baselines.py    brute force and TF-IDF, kept for comparison
      +-- embeddings.py   skip-gram ingredient vectors, overlap and embedding rankers
      +-- ranker.py       LightGBM lambdarank over 18 features
      +-- semantic.py     MiniLM text index
      +-- similar.py      nearest neighbours, taste profile, MMR diversity
      +-- taxonomy.py     cuisine and course groups
      +-- service.py      one Recommender object the API talks to
      |
api/app.py            Flask routes
      |
web/                  React + Vite + Tailwind
```

A request: typed ingredients are resolved to canonical names (with a character
n-gram fallback for misspellings), the overlap, TF-IDF and embedding rankers
each nominate 50 recipes, the learned ranker scores the union, then cuisine,
course, vegetarian and likes are applied. About 3 ms per query on a laptop CPU.

Training is offline. `models/` holds the artefacts the API loads: ingredient
vectors (180 KB), the ranker (350 KB) and the text embeddings (5 MB).

## Run it

```
pip install -r requirements.txt
python -m api.app                 # http://localhost:5000

cd web
npm install
npm run dev                       # http://localhost:5173
```

Set `VITE_API_URL` in `web/.env` if the API is somewhere else. Endpoints are
listed in [api/README.md](api/README.md).

Tests: `python -m pytest` (123 tests), and `npm run lint && npm run build` in
`web/`.

## Data

7,540 recipes with name, description, cuisine, course, diet, ingredients,
times, steps and a photo URL. After removing Hindi copies of English recipes,
plain repeats and Hindi-only rows, 6,521 remain. Known problems that the
cleaning handles: "Vegetarian" rows that list meat or eggs, 78 cuisine labels
for what a person would call a dozen cuisines, and the same ingredient spelled
many ways.

## Copyright

Registered with the Copyright Office, Government of India, as "Recipesense":
certificate SW-2025020495, application 38904/2024-CO/SW, filed 11 December
2024, registered 13 May 2025. Authors: Dr. Smita Bharne, Nauman Pathan,
Deeptanshu Lal, Sara Pathan, Soham Pardhi.
