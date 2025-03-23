import numpy as np
import pytest

from api.app import create_app
from recsys.service import Recommender

CARD_KEYS = {"id", "title", "total_time", "image", "veg", "cuisine", "course", "score"}
DETAIL_KEYS = {"id", "name", "description", "veg", "image", "prep_time", "cook_time", "total_time",
               "course", "cuisine", "cooking_ingredients", "cooking_instruction"}


def recommend(client, **body):
    return client.post("/api/recommend", json=body)


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json["status"] == "ok" and res.json["recipes"] > 5000
    assert set(res.json["ready"]) == {"ranker", "search"}
    assert all(isinstance(v, bool) for v in res.json["ready"].values())


def test_meta(client):
    res = client.get("/api/meta").json
    names = {c["name"] for c in res["cuisines"]}
    assert {"Indian", "North Indian", "South Indian", "Italian"} <= names
    assert {c["name"] for c in res["courses"]} >= {"Main Course", "Breakfast", "Dessert"}
    assert all(c["count"] > 0 for c in res["cuisines"] + res["courses"])
    ids = [m["id"] for m in res["models"]]
    assert "brute_force" not in ids
    assert ids == ["overlap", "tfidf"]  # the fixture marks learned and embedding unavailable
    assert res["recipes"] > 5000


@pytest.mark.parametrize("model", ["tfidf", "overlap"])
def test_recommend_shape(client, model):
    res = recommend(client, ingredients=["paneer", "tomato"], model=model, limit=10)
    assert res.status_code == 200
    body = res.json
    assert body["model"] == model
    assert isinstance(body["execution_time"], float) and body["execution_time"] >= 0
    recs = body["recommendations"]
    assert 0 < len(recs) <= 10
    assert all(set(r) == CARD_KEYS for r in recs)
    assert all(r["total_time"] is None or isinstance(r["total_time"], int) for r in recs)
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    assert len({r["id"] for r in recs}) == len(recs)
    assert len({r["title"].lower() for r in recs}) == len(recs)


def test_models_list_order_and_labels():
    from recsys.service import DEFAULT_MODEL, MODELS

    assert [(m["id"], m["label"]) for m in MODELS] == [
        ("learned", "Learned ranker"), ("embedding", "Ingredient embeddings"),
        ("overlap", "Ingredient overlap"), ("tfidf", "TF-IDF")]
    assert DEFAULT_MODEL == "learned"


def test_recommend_defaults_to_learned_and_falls_back(client):
    # The fixture marks learned unavailable, so the default model reports tfidf.
    res = recommend(client, ingredients=["paneer"])
    assert res.status_code == 200 and res.json["model"] == "tfidf"


def test_recommend_defaults_to_24(client):
    assert len(recommend(client, ingredients=["onion"]).json["recommendations"]) == 24


def test_veg_only_returns_veg_recipes(client):
    recs = recommend(client, ingredients=["chicken", "egg"], veg=True, limit=50).json["recommendations"]
    assert recs and all(r["veg"] for r in recs)


def test_cuisine_group_reaches_regional_labels(client):
    recs = recommend(client, cuisine=["Indian"], limit=100).json["recommendations"]
    labels = {r["cuisine"] for r in recs}
    assert len(recs) == 100
    assert labels & {"Kerala Recipes", "Punjabi", "North Indian Recipes"}


def test_course_group_reaches_lunch_and_dinner(client):
    recs = recommend(client, course="Main Course", limit=100).json["recommendations"]
    assert {r["course"] for r in recs} >= {"Lunch", "Dinner"}


def test_cuisine_boost_lifts_matching_recipes(client):
    def italian(**extra):
        recs = recommend(client, ingredients=["rice"], limit=100, **extra).json["recommendations"]
        return sum(r["cuisine"] == "Italian Recipes" for r in recs)

    assert italian(cuisine=["Italian"]) > italian()


def test_liked_recipes_are_excluded_and_steer_results(client):
    first = recommend(client, ingredients=["paneer"], limit=3).json["recommendations"]
    liked = [first[0]["id"]]
    recs = recommend(client, liked=liked, limit=10).json["recommendations"]
    assert recs and first[0]["id"] not in {r["id"] for r in recs}


def test_unavailable_model_falls_back_to_tfidf(client):
    res = recommend(client, ingredients=["paneer"], model="embedding")
    assert res.status_code == 200 and res.json["model"] == "tfidf"


@pytest.mark.parametrize("body", [
    {},
    {"ingredients": []},
    {"ingredients": [1, 2]},
    {"ingredients": ["a"] * 51},
    {"ingredients": ["a"], "cuisine": [3]},
    {"ingredients": ["a"], "course": 5},
    {"ingredients": ["a"], "veg": "yes"},
    {"ingredients": ["a"], "model": "magic"},
    {"ingredients": ["a"], "model": "brute_force"},
    {"ingredients": ["a"], "limit": 0},
    {"ingredients": ["a"], "limit": 101},
    {"ingredients": ["a"], "limit": "5"},
    {"ingredients": ["a"], "limit": True},
    {"ingredients": ["a"], "liked": ["x"]},
    {"ingredients": ["a"], "liked": "1"},
])
def test_recommend_rejects_bad_input(client, body):
    res = recommend(client, **body)
    assert res.status_code == 400
    assert res.is_json and res.json["error"]


def test_recommend_rejects_non_json(client):
    res = client.post("/api/recommend", data="not json", content_type="text/plain")
    assert res.status_code == 400 and res.json["error"]
    res = client.post("/api/recommend", json=["a"])
    assert res.status_code == 400


def test_search(client):
    res = client.post("/api/search", json={"query": "creamy spinach curry", "limit": 5})
    assert res.status_code == 200
    recs = res.json["recommendations"]
    assert 0 < len(recs) <= 5 and all(set(r) == CARD_KEYS for r in recs)
    assert "execution_time" in res.json


def test_search_veg_filter(client):
    recs = client.post("/api/search", json={"query": "chicken curry", "veg": True, "limit": 30}).json["recommendations"]
    assert all(r["veg"] for r in recs)


def test_search_cuisine_and_course_boost(client):
    def count(**extra):
        body = {"query": "creamy rice dish", "limit": 50, **extra}
        recs = client.post("/api/search", json=body).json["recommendations"]
        return sum(r["cuisine"] == "Italian Recipes" for r in recs)

    assert count(cuisine=["Italian"]) > count()
    res = client.post("/api/search", json={"query": "soup", "course": "Main Course", "limit": 10})
    assert res.status_code == 200 and res.json["recommendations"]


@pytest.mark.parametrize("body", [{"query": "ok", "cuisine": [3]}, {"query": "ok", "course": 5}])
def test_search_rejects_bad_cuisine_and_course(client, body):
    assert client.post("/api/search", json=body).status_code == 400


@pytest.mark.parametrize("body", [{}, {"query": ""}, {"query": "  "}, {"query": 5}, {"query": "x" * 300},
                                  {"query": "ok", "veg": 1}, {"query": "ok", "limit": -1}])
def test_search_rejects_bad_input(client, body):
    res = client.post("/api/search", json=body)
    assert res.status_code == 400 and res.json["error"]


def test_recipe_by_id(client):
    rid = recommend(client, ingredients=["paneer"]).json["recommendations"][0]["id"]
    res = client.get(f"/api/recipe/{rid}")
    assert res.status_code == 200
    assert set(res.json) == DETAIL_KEYS
    assert res.json["id"] == rid
    assert isinstance(res.json["cooking_instruction"], str)
    assert "," in res.json["cooking_ingredients"]
    for key in ("prep_time", "cook_time", "total_time"):
        assert res.json[key] is None or isinstance(res.json[key], int)
    assert not {"servings", "serving_size", "difficulty", "cooking_time"} & set(res.json)


def test_recipe_by_id_errors(client):
    assert client.get("/api/recipe/99999999").status_code == 404
    assert client.get("/api/recipe/99999999").json["error"]
    assert client.get("/api/recipe/abc").status_code == 404
    assert client.get("/api/recipe/-1").status_code == 404


def test_similar(client):
    rid = recommend(client, ingredients=["paneer"]).json["recommendations"][0]["id"]
    res = client.get(f"/api/recipe/{rid}/similar")
    assert res.status_code == 200
    recs = res.json["recommendations"]
    assert 0 < len(recs) <= 12
    assert rid not in {r["id"] for r in recs}
    assert all(set(r) == CARD_KEYS for r in recs)


def test_similar_limit(client):
    rid = recommend(client, ingredients=["paneer"]).json["recommendations"][0]["id"]
    assert len(client.get(f"/api/recipe/{rid}/similar?limit=5").json["recommendations"]) == 5
    assert len(client.get(f"/api/recipe/{rid}/similar?limit=48").json["recommendations"]) == 48
    for bad in ("0", "49", "x", "-3"):
        res = client.get(f"/api/recipe/{rid}/similar?limit={bad}")
        assert res.status_code == 400 and res.json["error"]


def test_similar_unknown_id(client):
    assert client.get("/api/recipe/99999999/similar").status_code == 404


@pytest.mark.parametrize("method,path", [("post", "/api/recommend-ai"), ("post", "/api/recommend-brute-force"),
                                         ("post", "/api/recipe")])
def test_legacy_routes_are_gone(client, method, path):
    res = getattr(client, method)(path, json={"ingredients": ["paneer"], "name": "x"})
    assert res.status_code in (404, 405) and res.is_json


def test_cravings_are_not_a_parameter():
    import inspect

    assert "cravings" not in inspect.signature(Recommender.recommend).parameters


def test_json_errors_for_unknown_route_and_wrong_method(client):
    res = client.get("/api/nope")
    assert res.status_code == 404 and res.is_json
    res = client.get("/api/recommend")
    assert res.status_code == 405 and res.is_json


def test_cors_header(client):
    res = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("Access-Control-Allow-Origin") in ("*", "http://localhost:5173")


def test_unexpected_error_becomes_json_500(recommender):
    app = create_app(recommender)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.testing = False

    def boom(*a, **k):
        raise RuntimeError("boom")

    app.extensions["recommender"].meta  # exists
    original = recommender.search
    recommender.search = boom
    try:
        res = app.test_client().post("/api/search", json={"query": "x"})
    finally:
        recommender.search = original
    assert res.status_code == 500 and res.json == {"error": "Internal server error"}


def test_semantic_module_is_used_when_present(recipes):
    """The seam: a SemanticSearch-like object replaces the TF-IDF fallback."""
    rec = Recommender(recipes=recipes)
    rec._failed.update({"embedding", "learned"})

    class Fake:
        def search(self, text, k, mask):
            return np.array([5, 6, 7]), np.array([0.9, 0.8, 0.7])

    rec._semantic = Fake()
    got = rec.search("anything", limit=3)
    assert [r["id"] for r in got] == [int(recipes.loc[i, "raw_id"]) for i in (5, 6, 7)]


def test_failing_semantic_module_falls_back(recipes):
    rec = Recommender(recipes=recipes)
    rec._failed.update({"embedding", "learned"})

    class Broken:
        def search(self, text, k, mask):
            raise RuntimeError("no model")

    rec._semantic = Broken()
    assert rec.search("spinach curry", limit=3)


def _fake_ranker(recipes, dim=8):
    rng = np.random.default_rng(0)
    vecs = rng.normal(size=(len(recipes), dim)).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)

    class Fake:
        recipe_vectors = vecs

    return Fake(), vecs


def test_similar_uses_ingredient_vectors_when_available(recipes):
    rec = Recommender(recipes=recipes)
    rec._failed.add("learned")
    rec._semantic_failed = True
    fake, vecs = _fake_ranker(recipes)
    rec._rankers["embedding"] = fake
    rid = int(recipes.loc[10, "raw_id"])
    got = rec.similar(rid, limit=5)
    sims = vecs @ vecs[10]
    sims[10] = -np.inf
    assert got[0]["id"] == int(recipes.loc[int(np.argmax(sims)), "raw_id"])


def test_similar_combines_ingredient_and_text_vectors(recipes):
    rec = Recommender(recipes=recipes)
    rec._failed.add("learned")
    fake, vecs = _fake_ranker(recipes)
    rec._rankers["embedding"] = fake

    class Text:
        matrix = vecs[::-1].copy()  # a different space with the same rows

    rec._semantic = Text()
    matrix = rec._vectors()
    assert matrix.shape == (len(recipes), vecs.shape[1] * 2)
    assert rec.similar(int(recipes.loc[3, "raw_id"]), limit=4)


def test_liked_uses_taste_profile(recipes):
    rec = Recommender(recipes=recipes)
    rec._failed.add("learned")
    rec._semantic_failed = True
    fake, vecs = _fake_ranker(recipes)
    rec._rankers["embedding"] = fake
    taste = rec._taste([4, 7])
    assert taste.shape == (len(recipes),) and taste.max() == pytest.approx(1.0)
    got = rec.recommend([], liked=[int(recipes.loc[4, "raw_id"])], limit=5)
    assert got and int(recipes.loc[4, "raw_id"]) not in {r["id"] for r in got}


def test_warm_up_sets_ready_flags(recipes):
    rec = Recommender(recipes=recipes)
    rec._failed.update({"embedding", "learned"})
    rec._semantic_failed = True
    assert rec.ready() == {"ranker": False, "search": False}
    rec.warm()
    assert rec.ready() == {"ranker": True, "search": True}
