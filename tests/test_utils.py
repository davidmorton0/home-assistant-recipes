from custom_components.recipe_book.utils import unique_categories, fetch_recipe, fetch_recipe_categories, clean_line, safe_slug

import pytest


@pytest.fixture
def recipes():
    return [
        {"uuid": "abc-1", "name": "Porridge", "category": "Breakfast"},
        {"uuid": "abc-2", "name": "Spaghetti", "category": "Pasta"},
        {"uuid": "abc-3", "name": "Avocado Toast", "category": "Breakfast"},
    ]


class TestUniqueCategories:
    def test_returns_sorted_categories_with_all_prefix(self, recipes):
        assert unique_categories(recipes) == ["All", "Breakfast", "Pasta"]

    def test_deduplicates_categories(self, recipes):
        assert unique_categories(recipes).count("Breakfast") == 1

    def test_empty_recipes_returns_only_all(self):
        assert unique_categories([]) == ["All"]


class TestFetchRecipe:
    def test_returns_matching_recipe(self, recipes):
        assert fetch_recipe(recipes, "abc-2")["name"] == "Spaghetti"

    def test_returns_none_when_not_found(self, recipes):
        assert fetch_recipe(recipes, "no-such-uuid") is None


class TestCleanLine:
    def test_strips_dash_bullet(self):
        assert clean_line("- Oats") == "Oats"

    def test_strips_numbered_bullet(self):
        assert clean_line("1. Combine and heat") == "Combine and heat"

    def test_strips_leading_whitespace(self):
        assert clean_line("  Oats") == "Oats"

    def test_leaves_plain_text_unchanged(self):
        assert clean_line("Oats") == "Oats"


class TestSafeSlug:
    def test_lowercases_name(self):
        assert safe_slug("Porridge") == "porridge"

    def test_replaces_spaces_with_underscores(self):
        assert safe_slug("Mac and Cheese") == "mac_and_cheese"

    def test_removes_special_characters(self):
        assert safe_slug("Mum's Soup!") == "mum_s_soup"

    def test_empty_name_returns_recipe(self):
        assert safe_slug("") == "recipe"


class TestFetchRecipeCategories:
    def test_returns_existing_categories_without_all(self):
        assert fetch_recipe_categories(["All", "Breakfast", "Pasta"], "Breakfast") == ["Breakfast", "Pasta"]

    def test_appends_missing_category(self):
        assert fetch_recipe_categories(["All", "Breakfast"], "Dessert") == ["Breakfast", "Dessert"]

    def test_returns_sorted(self):
        assert fetch_recipe_categories(["All", "Pasta", "Breakfast"], "Dessert") == ["Breakfast", "Dessert", "Pasta"]
