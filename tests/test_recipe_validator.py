from custom_components.recipe_book.recipe_validator import RecipeValidator

import pytest


@pytest.fixture
def valid_recipe():
    return {
        "name": "Porridge",
        "ingredients": ["Oats", "Milk"],
        "steps": ["Combine and heat"],
    }


@pytest.fixture
def validator():
    return RecipeValidator()


class TestValidate:
    def test_valid_recipe_returns_no_errors(self, validator, valid_recipe):
        assert validator.validate(valid_recipe) == []

    def test_empty_name_returns_error(self, validator, valid_recipe):
        valid_recipe["name"] = ""
        errors = validator.validate(valid_recipe)
        assert any("Name" in e for e in errors)

    def test_empty_ingredients_returns_error(self, validator, valid_recipe):
        valid_recipe["ingredients"] = []
        errors = validator.validate(valid_recipe)
        assert any("ingredient" in e for e in errors)

    def test_empty_steps_returns_error(self, validator, valid_recipe):
        valid_recipe["steps"] = []
        errors = validator.validate(valid_recipe)
        assert any("step" in e for e in errors)

    def test_multiple_errors_returned_together(self, validator, valid_recipe):
        valid_recipe["name"] = ""
        valid_recipe["ingredients"] = []
        valid_recipe["steps"] = []
        assert len(validator.validate(valid_recipe)) == 3
