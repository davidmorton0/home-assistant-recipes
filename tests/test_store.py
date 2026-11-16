import os

import pytest
import yaml

from custom_components.recipe_book.store import RecipeNotFound, RecipeStore


def recipe(uuid="u1", name="Porridge", **extra):
    return {
        "uuid": uuid,
        "name": name,
        "category": "Breakfast",
        "serves": 2,
        "status": "Untested",
        "ingredients": ["Oats"],
        "steps": ["Heat"],
        **extra,
    }


@pytest.fixture
def store(tmp_path):
    return RecipeStore(str(tmp_path / "recipe_book"))


def test_ensure_directory_creates_the_folder(store):
    store.ensure_directory()
    assert os.path.isdir(store.directory)


def test_add_writes_a_file_named_after_the_recipe(store):
    store.ensure_directory()
    path = store.add(recipe(name="Mac & Cheese"))
    assert os.path.basename(path) == "mac_cheese.yaml"
    assert yaml.safe_load(open(path))[0]["name"] == "Mac & Cheese"


def test_add_does_not_overwrite_a_file_with_the_same_name(store):
    store.ensure_directory()
    first = store.add(recipe(uuid="u1"))
    second = store.add(recipe(uuid="u2"))
    assert os.path.basename(first) == "porridge.yaml"
    assert os.path.basename(second) == "porridge_2.yaml"


def test_load_returns_the_recipes_with_their_file(store):
    store.ensure_directory()
    path = store.add(recipe())
    loaded = store.load()
    assert [r["uuid"] for r in loaded] == ["u1"]
    assert loaded[0]["_file"] == path


def test_replace_overwrites_the_file_holding_that_uuid(store):
    store.ensure_directory()
    path = store.add(recipe())
    store.replace(store.load(), recipe(name="Better porridge", status="Approved"))
    data = yaml.safe_load(open(path))[0]
    assert data["name"] == "Better porridge"
    assert data["status"] == "Approved"
    assert len(os.listdir(store.directory)) == 1


def test_replace_unknown_uuid_raises(store):
    store.ensure_directory()
    with pytest.raises(RecipeNotFound):
        store.replace([], recipe(uuid="missing"))


def test_delete_removes_the_file(store):
    store.ensure_directory()
    path = store.add(recipe())
    store.delete(store.load(), "u1")
    assert not os.path.exists(path)


def test_delete_unknown_uuid_raises(store):
    store.ensure_directory()
    with pytest.raises(RecipeNotFound):
        store.delete([], "missing")
