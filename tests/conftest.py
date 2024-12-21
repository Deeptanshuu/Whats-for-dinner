import pytest

from recsys.data import Vocabulary, load_recipes


@pytest.fixture(scope="session")
def recipes():
    """The real catalogue, loaded once."""
    return load_recipes()


@pytest.fixture(scope="session")
def vocab(recipes):
    return Vocabulary.build(recipes)
