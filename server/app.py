"""Flask app for the recipe recommender.

``create_app()`` builds the app and loads the catalogue once. With
``RECSYS_WARM=1`` a background thread builds the default ranker and the
semantic index so the first request is not slow.
"""
# Small matrix products are much slower with many BLAS threads, so pin them
# before numpy is imported.
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import threading  # noqa: E402
import time  # noqa: E402

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from recsys.service import DEFAULT_MODEL, MODEL_IDS, Recommender, RecipeNotFound

MAX_ITEMS = 50
MAX_TEXT = 200
MAX_LIMIT = 100
MAX_SIMILAR = 48


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# ----- request parsing -----

def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object")
    return data


def _str_list(data: dict, key: str) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ApiError(f"'{key}' must be a list of strings")
    if len(value) > MAX_ITEMS:
        raise ApiError(f"'{key}' can hold at most {MAX_ITEMS} items")
    if any(len(v) > MAX_TEXT for v in value):
        raise ApiError(f"Items in '{key}' can be at most {MAX_TEXT} characters")
    return [v.strip() for v in value if v.strip()]


def _text(data: dict, key: str, required: bool = False) -> str:
    value = data.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ApiError(f"'{key}' must be a string")
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise ApiError(f"'{key}' can be at most {MAX_TEXT} characters")
    if required and not value:
        raise ApiError(f"'{key}' is required")
    return value


def _bool(data: dict, key: str) -> bool:
    value = data.get(key, False)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ApiError(f"'{key}' must be true or false")
    return value


def _int(value, key: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(f"'{key}' must be an integer")
    if not low <= value <= high:
        raise ApiError(f"'{key}' must be between {low} and {high}")
    return value


def _limit(data: dict, default: int) -> int:
    value = data.get("limit")
    return default if value is None else _int(value, "limit", 1, MAX_LIMIT)


def _model(data: dict, default: str) -> str:
    value = data.get("model") or default
    if not isinstance(value, str) or value not in MODEL_IDS:
        raise ApiError(f"'model' must be one of: {', '.join(MODEL_IDS)}")
    return value


def _liked(data: dict) -> list[int]:
    value = data.get("liked", [])
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 200:
        raise ApiError("'liked' must be a list of recipe ids (at most 200)")
    return [_int(v, "liked", 0, 10**9) for v in value]


def _warm(rec: Recommender, app: Flask) -> None:
    try:
        rec.warm()
    except Exception:
        app.logger.exception("Warm-up failed")


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _query_limit(default: int, high: int) -> int:
    raw = request.args.get("limit")
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError("'limit' must be an integer") from None
    if not 1 <= value <= high:
        raise ApiError(f"'limit' must be between 1 and {high}")
    return value


def create_app(recommender: Recommender | None = None, warm: bool | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    app.json.sort_keys = False
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    CORS(app, origins=origins)
    rec = recommender or Recommender()
    app.extensions["recommender"] = rec
    if warm is None:
        warm = os.environ.get("RECSYS_WARM", "0") == "1"
    if warm:
        threading.Thread(target=_warm, args=(rec, app), name="warm-up", daemon=True).start()

    @app.post("/api/recommend")
    def recommend():
        data = _body()
        ingredients = _str_list(data, "ingredients")
        cuisine = _str_list(data, "cuisine")
        course = _text(data, "course")
        veg = _bool(data, "veg")
        liked = _liked(data)
        limit = _limit(data, 24)
        model = _model(data, DEFAULT_MODEL)
        if not (ingredients or cuisine or course or liked):
            raise ApiError("Give at least one ingredient, cuisine, course or liked recipe")
        start = time.perf_counter()
        used = rec.resolve_model(model)
        results = rec.recommend(ingredients, cuisine, course, veg, used, liked, limit)
        return jsonify({"recommendations": results, "execution_time": _ms(start), "model": used})

    @app.post("/api/search")
    def search():
        data = _body()
        query = _text(data, "query", required=True)
        cuisine = _str_list(data, "cuisine")
        course = _text(data, "course")
        veg = _bool(data, "veg")
        limit = _limit(data, 24)
        start = time.perf_counter()
        results = rec.search(query, veg=veg, limit=limit, cuisine=cuisine, course=course)
        return jsonify({"recommendations": results, "execution_time": _ms(start), "model": "search"})

    @app.get("/api/recipe/<int:recipe_id>")
    def recipe_by_id(recipe_id: int):
        return jsonify(rec.recipe(recipe_id))

    @app.get("/api/recipe/<int:recipe_id>/similar")
    def similar(recipe_id: int):
        limit = _query_limit(12, MAX_SIMILAR)
        start = time.perf_counter()
        results = rec.similar(recipe_id, limit)
        return jsonify({"recommendations": results, "execution_time": _ms(start)})

    @app.get("/api/meta")
    def meta():
        return jsonify(rec.meta())

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "recipes": rec.meta()["recipes"], "ready": rec.ready()})

    # ----- errors -----

    @app.errorhandler(ApiError)
    def _api_error(err: ApiError):
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(RecipeNotFound)
    def _not_found(err: RecipeNotFound):
        message = "Recipe not found"
        return jsonify({"error": message, "detail": str(err)}), 404

    @app.errorhandler(HTTPException)
    def _http_error(err: HTTPException):
        return jsonify({"error": err.description or err.name}), err.code

    @app.errorhandler(Exception)
    def _server_error(err: Exception):
        app.logger.exception("Unhandled error")
        return jsonify({"error": "Internal server error"}), 500

    return app


def main() -> None:
    os.environ.setdefault("RECSYS_WARM", "1")
    app = create_app()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))


if __name__ == "__main__":
    main()
