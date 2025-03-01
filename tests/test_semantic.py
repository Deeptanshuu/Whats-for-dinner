import numpy as np
import pandas as pd
import pytest

from recsys import semantic
from recsys.semantic import TfidfSearch, _digest, _top_k, clean_description, clean_title, recipe_texts


def frame():
    rows = [
        ("Palak Paneer Recipe", "Creamy spinach curry with paneer cubes.", "North Indian Recipes", "Lunch", ["Spinach", "Paneer"]),
        ("Chocolate Brownie Recipe", "Fudgy chocolate dessert baked in squares.", "Continental", "Dessert", ["Cocoa", "Sugar"]),
        ("तुरई चना सब्ज़ी - Ridge Gourd With Dal (Recipe In Hindi)", "तुरई चना सब्ज़ी एक बहुत ही सरल सब्ज़ी है", "North Indian Recipes", "Lunch", ["Ridge Gourd"]),
        ("Masala Chai Recipe", "Spiced milk tea with ginger and cardamom.", "Indian", "Beverages", ["Tea", "Milk"]),
    ]
    return pd.DataFrame({"name": [r[0] for r in rows], "description": [r[1] for r in rows],
                         "cuisine": [r[2] for r in rows], "course": [r[3] for r in rows],
                         "ingredients_raw": [r[4] for r in rows]})


def test_clean_title_handles_hindi_and_recipe_word():
    assert clean_title("Palak Paneer Recipe") == "Palak Paneer"
    assert clean_title("तुरई चना सब्ज़ी - Ridge Gourd With Dal (Recipe In Hindi)") == "Ridge Gourd With Dal"


def test_clean_description_drops_hindi():
    assert clean_description("तुरई चना सब्ज़ी एक बहुत ही सरल सब्ज़ी है") == ""
    assert clean_description("  Plain   English text ") == "Plain English text"


def test_recipe_texts_fields():
    df = frame()
    full = recipe_texts(df, ("title", "description", "cuisine", "course", "ingredients"))
    assert "Palak Paneer" in full[0] and "Lunch" in full[0] and "Ingredients: Spinach, Paneer" in full[0]
    no_title = recipe_texts(df, ("description",))
    assert "Palak" not in no_title[0]
    assert "ुर" not in recipe_texts(df)[2]  # no Devanagari reaches the model


def test_digest_changes_with_input():
    assert _digest(["a", "b"], "m") == _digest(["a", "b"], "m")
    assert _digest(["a", "b"], "m") != _digest(["a", "c"], "m")
    assert _digest(["a", "b"], "m") != _digest(["a", "b"], "n")


def test_top_k_and_mask():
    s = np.array([0.1, 0.9, 0.5, 0.7], dtype=np.float32)
    idx, sc = _top_k(s, 2, None)
    assert list(idx) == [1, 3] and sc[0] == pytest.approx(0.9)
    idx, _ = _top_k(s, 10, np.array([True, False, True, True]))
    assert list(idx) == [3, 2, 0]
    idx, _ = _top_k(s, 3, np.zeros(4, dtype=bool))
    assert len(idx) == 0


def test_tfidf_finds_the_right_recipe():
    s = TfidfSearch(frame(), min_df=1)
    idx, _ = s.search("creamy spinach with paneer", k=2)
    assert idx[0] == 0
    idx, _ = s.search("spiced tea", k=1)
    assert idx[0] == 3
    assert s.score("chocolate").shape == (4,)


def test_semantic_cache_roundtrip(tmp_path, monkeypatch):
    """Cache is written once and reused; a stale hash forces a rebuild. Uses a fake encoder."""
    monkeypatch.setattr(semantic, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(semantic, "EMB_PATH", tmp_path / "text_embeddings.npy")
    monkeypatch.setattr(semantic, "META_PATH", tmp_path / "text_embeddings.json")
    calls = []

    def fake_encode(self, texts, batch_size=64):
        calls.append(len(texts))
        rng = np.random.default_rng(len(texts))
        m = rng.normal(size=(len(texts), 8)).astype(np.float32)
        return m / np.linalg.norm(m, axis=1, keepdims=True)

    monkeypatch.setattr(semantic.SemanticSearch, "encode", fake_encode)
    df = frame()
    a = semantic.SemanticSearch(df)
    b = semantic.SemanticSearch(df)
    assert calls == [4]  # second build read the cache
    assert (tmp_path / "text_embeddings.npy").stat().st_size > 0
    assert np.allclose(a.matrix, b.matrix, atol=1e-2)
    df2 = df.copy()
    df2.loc[0, "description"] = "changed"
    semantic.SemanticSearch(df2)
    assert calls == [4, 4]  # stale, rebuilt


@pytest.mark.model
def test_real_model_ranks_sensibly():
    pytest.importorskip("sentence_transformers")
    s = semantic.SemanticSearch(frame(), cache=False)
    idx, scores = s.search("creamy spinach curry", k=4)
    assert idx[0] == 0
    assert np.all(np.diff(scores) <= 1e-6)
    assert np.allclose(np.linalg.norm(s.matrix, axis=1), 1, atol=1e-4)
