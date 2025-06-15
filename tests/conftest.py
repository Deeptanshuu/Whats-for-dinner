import os

import pytest

os.environ["RECSYS_WARM"] = "0"  # no background warm-up under tests

from server.app import create_app
from recsys.data import Vocabulary, load_recipes
from recsys.service import Recommender


@pytest.fixture(scope="session")
def recipes():
    """The real catalogue, loaded once."""
    return load_recipes()


@pytest.fixture(scope="session")
def vocab(recipes):
    return Vocabulary.build(recipes)


@pytest.fixture(scope="session")
def recommender(recipes):
    rec = Recommender(recipes=recipes)
    # Keep API tests fast and independent of the models: use the TF-IDF fallbacks.
    rec._semantic_failed = True
    rec._failed.update({"embedding", "learned"})
    return rec


@pytest.fixture(scope="session")
def client(recommender):
    return create_app(recommender).test_client()
