from custom_components.recipe_book.recipe_writer import RecipeWriter

import pytest
import yaml


@pytest.fixture
def writer():
    return RecipeWriter()


@pytest.fixture
def recipe():
    return {
        "uuid": "abc-123",
        "name": "Porridge",
        "category": "Breakfast",
        "serves": 2,
        "status": "Approved",
        "ingredients": ["Oats", "Milk"],
        "steps": ["Combine and heat"],
    }


class TestCall:
    def test_writes_file_to_disk(self, writer, recipe, tmp_path):
        path = tmp_path / "porridge.yaml"
        writer.call(str(path), recipe)
        assert path.exists()

    def test_written_file_parses_back_correctly(self, writer, recipe, tmp_path):
        path = tmp_path / "porridge.yaml"
        writer.call(str(path), recipe)
        loaded = yaml.safe_load(path.read_text())
        assert loaded[0]["uuid"] == "abc-123"
        assert loaded[0]["name"] == "Porridge"
        assert loaded[0]["ingredients"] == ["Oats", "Milk"]
        assert loaded[0]["steps"] == ["Combine and heat"]

    def test_excludes_private_file_field(self, writer, recipe, tmp_path):
        recipe["_file"] = "/config/recipes/porridge.yaml"
        path = tmp_path / "porridge.yaml"
        writer.call(str(path), recipe)
        content = path.read_text()
        assert "_file" not in content

    def test_quotes_values_with_special_characters(self, writer, recipe, tmp_path):
        recipe["name"] = "Mac & Cheese"
        path = tmp_path / "mac.yaml"
        writer.call(str(path), recipe)
        loaded = yaml.safe_load(path.read_text())
        assert loaded[0]["name"] == "Mac & Cheese"
