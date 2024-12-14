# RecipeSense: plan for an ML recommender

A plan for replacing the keyword ranker with a learned recommender, plus what
an audit of the current code found. Nothing here is built yet.

## Goal

A recommender that is measured, not just demoed: clean ingredient data, a
learned ranker on top of it, free-text search, and recommendations that follow
what a person opens or likes.

## What stays

| Thing | Note |
|---|---|
| The app's look: food-doodle background, serif type, bordered cards | |
| Flask and Python as the backend | |
| The timing readout | It has to show a real measurement |

## What goes

| Thing | Why |
|---|---|
| Brute force mode | A substring counter with a `time.sleep(0.08)` in it, so the "faster than brute force" readout is not real. Keep it only as an offline baseline |
| Servings and difficulty on the cards | Both are made up from cooking time |
| `Server/`, `testing/`, `Visual/`, `stuff/`, the root `yes-chef/` | Old copies, committed `node_modules` and build output, five copies of the dataset |

## What to build

| Piece | What it is | How |
|---|---|---|
| Clean ingredients | One canonical name per ingredient | Strip bracketed aliases, fold singular and plural, keep the aliases as a lookup |
| Evaluation | A number for every ranker | Known-item search, below |
| Ingredient embeddings | A vector per ingredient, trained on which ingredients appear together | Skip-gram (gensim `Word2Vec`) with each recipe's ingredient list as a sentence |
| Learned ranker | One model that combines overlap, TF-IDF and embedding similarity | LightGBM `lambdarank`, trained on known-item queries. Replaces the hand-set 0.2 and 0.3 weights |
| Free-text search | "something creamy and spicy with spinach" | Sentence embeddings (`all-MiniLM-L6-v2`) of title and description, cosine in NumPy |
| More like this | Recommendations from a recipe that was opened or liked | Nearest neighbours in embedding space; a taste vector from liked recipes re-ranks later results |

Order: cleaning and evaluation first, then embeddings, the ranker, free-text
search, and the API and UI last.

## How to measure it

There are no ratings or click logs, so use known-item search: build a query
from a held-out recipe's own ingredients, rank every recipe, record where the
source recipe lands. Split recipes in half by id; tune on one half, report on
the other.

| Query style | How it is built |
|---|---|
| typed | Four ingredients; half the time use the bracketed alias (`haldi` for `Turmeric powder (Haldi)`), otherwise flip singular and plural |
| exact | Four ingredients as the dataset spells them, bracketed alias removed |
| pantry | Three quarters of the recipe's ingredients plus ten other common ones |

Report the share of source recipes ranked in the top 6, the app's first page.

## Bugs found in the current code

| Bug | Where | Effect |
|---|---|---|
| Fake delay in the brute-force path | `time.sleep(0.08)` in `brute_force_recommend` | The speed comparison is not a real measurement |
| Veg mode keeps only `diet == "vegetarian"` | `recommend_recipes` | Drops Vegan, High Protein Vegetarian and Sattvic recipes, and keeps "Vegetarian" rows that list eggs, fish or meat |
| Cuisine matched as a substring | `calculate_weighted_similarity` | "Indian" misses Kerala, Punjabi, Bengali and the other regional labels |
| Course matched as a substring | same | "Main Course" misses Lunch and Dinner; "Soup" and "Salad" match nothing because they are not course labels |
| Hindi copies of English recipes | the dataset | Several hundred rows repeat an English recipe with the same photo, so one dish can appear twice in a result list |
| UI cuisines with no data | `Home.jsx` | Russian, Irish, Italian-American and Vegan return nothing |
| `/api/recipe` re-reads the CSV on every request | `recipe()` | Slow, and looks recipes up by name |
| `requirements.txt` | UTF-16, lists torch, transformers, faiss, ollama | None are imported by the API |
