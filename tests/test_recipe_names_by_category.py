from custom_components.recipe_book.recipe_names_by_category import RecipeNamesByCategory

import pytest


@pytest.fixture
def spaghetti_aglio_e_olio():
    return {"name": "Spaghetti Aglio e Olio", "category": "Pasta"}


@pytest.fixture
def porridge():
    return {"name": "Porridge", "category": "Breakfast"}


@pytest.fixture
def avocado_toast():
    return {"name": "Avocado Toast", "category": "Breakfast"}


@pytest.fixture
def eton_mess():
    return {"name": "Eton Mess", "category": "Dessert"}


@pytest.fixture
def sample_recipes(spaghetti_aglio_e_olio, porridge, avocado_toast, eton_mess):
    return [spaghetti_aglio_e_olio, porridge, avocado_toast, eton_mess]


@pytest.fixture
def service():
    return RecipeNamesByCategory()


class TestRecipeNamesByCategory:
    def test_empty_recipes_returns_empty(self, service):
        assert service.call([], "Pasta") == []

    def test_returns_only_matching_recipes(self, service, spaghetti_aglio_e_olio, porridge):
        assert service.call([spaghetti_aglio_e_olio, porridge], "Pasta") == ["Spaghetti Aglio e Olio"]

    def test_all_label_returns_every_name(self, service, spaghetti_aglio_e_olio, porridge, eton_mess):
        recipes = [spaghetti_aglio_e_olio, porridge, eton_mess]
        assert service.call(recipes, "All") == [
            "Eton Mess", "Porridge", "Spaghetti Aglio e Olio",
        ]

    def test_names_are_sorted_alphabetically(self, service, eton_mess, avocado_toast):
        assert service.call([eton_mess, avocado_toast], "All") == ["Avocado Toast", "Eton Mess"]

    def test_recipe_without_category_does_not_match(self, service):
        recipes = [{"name": "Mystery"}]
        assert service.call(recipes, "Pasta") == []

    def test_recipe_without_category_still_returned_for_all(self, service):
        recipes = [{"name": "Mystery"}]
        assert service.call(recipes, "All") == ["Mystery"]
