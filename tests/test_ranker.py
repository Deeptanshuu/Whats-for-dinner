import subprocess
import sys

import numpy as np
import pytest

from recsys.data import Vocabulary
from recsys.embeddings import EmbeddingRanker, train_vectors
from recsys.evaluate import build_queries
from recsys.ranker import (FEATURES, META_PATH, MODEL_PATH, FeatureBuilder, LearnedRanker, TreeEnsemble,
                           load_ranker, save_ranker, train_ranker)


@pytest.fixture(scope="module")
def setup(recipes):
    part = recipes.head(800).reset_index(drop=True)
    vocab = Vocabulary.build(part)
    embedding = EmbeddingRanker(part, vocab, train_vectors(part, vector_size=16, epochs=5))
    features = FeatureBuilder(part, vocab, embedding, n_candidates=20)
    queries = build_queries(part, vocab, "tune")
    train = [q for qs in queries.values() for q in qs[:60]]
    booster, info = train_ranker(features, train, params={"num_threads": 1}, rounds=50)
    return part, vocab, features, booster, info, queries


def test_features_match_the_names(setup):
    _, _, features, *_ = setup
    cands, X, overlap = features.build(["onion", "tomato", "ginger", "salt"])
    assert X.shape == (len(cands), len(FEATURES))
    assert np.isfinite(X).all()
    assert len(np.unique(cands)) == len(cands)
    assert overlap.shape == (features.index.incidence.shape[0],)


def test_training_reports_held_out_scores(setup):
    *_, info, _ = setup
    assert info["train_queries"] > 0 and info["valid_queries"] > 0
    assert 0 < info["candidate_recall"] <= 1
    assert "ndcg@1" in info["valid"]


def test_scores_cover_every_row_and_candidates_come_first(setup):
    part, _, features, booster, _, queries = setup
    ranker = LearnedRanker(features, booster, len(part))
    query = queries["exact"][0].items
    scores = ranker.score(query)
    assert scores.shape == (len(part),)
    assert scores.dtype == np.float32
    cands, _, _ = features.build(query)
    outside = np.setdiff1d(np.arange(len(part)), cands)
    assert scores[cands].min() > scores[outside].max()


def test_ranker_puts_source_near_top(setup):
    part, _, features, booster, _, queries = setup
    ranker = LearnedRanker(features, booster, len(part))
    held = queries["exact"][-40:]
    hits = [(ranker.score(q.items) > ranker.score(q.items)[q.source]).sum() < 6 for q in held]
    assert np.mean(hits) > 0.6


def test_empty_query_does_not_crash(setup):
    part, _, features, booster, *_ = setup
    scores = LearnedRanker(features, booster, len(part)).score([])
    assert scores.shape == (len(part),)


def test_save_and_load_round_trip(tmp_path, setup):
    _, _, features, booster, info, _ = setup
    model, meta = tmp_path / "ranker.txt", tmp_path / "ranker.json"
    save_ranker(booster, info, features.n_candidates, model, meta)
    loaded, loaded_meta = load_ranker(model, meta)
    assert loaded_meta["n_candidates"] == features.n_candidates
    _, X, _ = features.build(["rice", "onion", "peas"])
    np.testing.assert_allclose(loaded.predict(X), booster.predict(X, num_iteration=booster.best_iteration),
                               rtol=1e-6)
    assert isinstance(loaded, TreeEnsemble)


def test_numpy_trees_match_lightgbm(setup):
    pytest.importorskip("lightgbm")
    part, _, features, booster, _, queries = setup
    trees = TreeEnsemble.from_text(booster.model_to_string(num_iteration=booster.best_iteration))
    for q in [q for qs in queries.values() for q in qs[:25]]:
        _, X, _ = features.build(q.items)
        want = booster.predict(X, num_iteration=booster.best_iteration)
        got = trees.predict(X)
        np.testing.assert_allclose(got, want, atol=1e-9)
        assert (np.argsort(-got, kind="stable") == np.argsort(-want, kind="stable")).all()


def test_saved_model_matches_lightgbm():
    lgb = pytest.importorskip("lightgbm")
    if not MODEL_PATH.exists():
        pytest.skip("no trained model in models/")
    booster = lgb.Booster(model_file=str(MODEL_PATH))
    trees = TreeEnsemble.from_file(MODEL_PATH)
    X = np.random.default_rng(0).random((300, len(FEATURES))).astype(np.float32)
    np.testing.assert_allclose(trees.predict(X), booster.predict(X), atol=1e-9)


def test_trees_predict_without_lightgbm():
    if not (MODEL_PATH.exists() and META_PATH.exists()):
        pytest.skip("no trained model in models/")
    code = (
        "import sys; sys.modules['lightgbm'] = None\n"
        "import numpy as np\n"
        "from recsys.ranker import FEATURES, load_ranker\n"
        "trees, meta = load_ranker()\n"
        "out = trees.predict(np.zeros((5, len(FEATURES)), dtype=np.float32))\n"
        "assert out.shape == (5,) and np.isfinite(out).all()\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_nan_features_are_rejected():
    trees = TreeEnsemble.from_file(MODEL_PATH) if MODEL_PATH.exists() else pytest.skip("no model")
    X = np.zeros((1, len(FEATURES)), dtype=np.float32)
    X[0, 0] = np.nan
    with pytest.raises(ValueError):
        trees.predict(X)
