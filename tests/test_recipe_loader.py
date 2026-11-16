from custom_components.recipe_book.recipe_loader import RecipeLoader

import pytest


@pytest.fixture
def service():
    return RecipeLoader()


@pytest.fixture
def avocado_toast_yaml():
    return """\
- uuid: abc-123
  name: Avocado Toast
  category: Breakfast
  serves: 1
  status: Attempted
  ingredients:
    - 1 avocado
    - 2 slices sourdough
  steps:
    - Toast the bread.
    - Mash the avocado and spread on toast.
"""


class TestRecipeLoader:
    def test_returns_recipe_from_yaml_files(self, service, avocado_toast_yaml, tmp_path):
        (tmp_path / "avocado_toast.yaml").write_text(avocado_toast_yaml)
        recipes = service.call(str(tmp_path))
        assert len(recipes) == 1
        assert recipes[0]["name"] == "Avocado Toast"
        assert recipes[0]["category"] == "Breakfast"

    def test_recipe_missing_required_field_is_skipped(self, service, tmp_path):
        (tmp_path / "bad.yaml").write_text("- name: No UUID\n  ingredients: []\n  steps: []\n")
        recipes = service.call(str(tmp_path))
        assert recipes == []

    def test_invalid_yaml_file_is_skipped(self, service, tmp_path):
        (tmp_path / "bad.yaml").write_text("this: is: not: valid: yaml: [\n")
        recipes = service.call(str(tmp_path))
        assert recipes == []

    def test_defaults_applied_when_fields_absent(self, service, tmp_path):
        (tmp_path / "r.yaml").write_text(
            "- uuid: abc-123\n  name: Mystery Dish\n  ingredients: []\n  steps: []\n"
        )
        recipes = service.call(str(tmp_path))
        assert recipes[0]["category"] == "Uncategorised"
        assert recipes[0]["status"] == "Untested"

    def test_file_with_top_level_dict_is_skipped(self, service, tmp_path):
        (tmp_path / "bad.yaml").write_text("name: Not A List\n")
        recipes = service.call(str(tmp_path))
        assert recipes == []

    def test_recipes_returned_sorted_by_name(self, service, tmp_path):
        (tmp_path / "recipes.yaml").write_text(
            "- uuid: 1\n  name: Porridge\n  ingredients: []\n  steps: []\n"
            "- uuid: 2\n  name: Avocado Toast\n  ingredients: []\n  steps: []\n"
        )
        recipes = service.call(str(tmp_path))
        assert [r["name"] for r in recipes] == ["Avocado Toast", "Porridge"]
