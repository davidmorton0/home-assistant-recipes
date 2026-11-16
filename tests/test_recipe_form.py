from custom_components.recipe_book.recipe_form import build_recipe, lines


class TestLines:
    def test_text_is_split_on_lines_and_blank_lines_dropped(self):
        assert lines("Oats\n\n  Milk  \n") == ["Oats", "Milk"]

    def test_bullets_and_numbers_are_removed(self):
        assert lines("- Oats\n2. Milk\n• Salt") == ["Oats", "Milk", "Salt"]

    def test_a_list_is_taken_as_it_is(self):
        assert lines(["Oats", "Milk"]) == ["Oats", "Milk"]

    def test_none_gives_an_empty_list(self):
        assert lines(None) == []


class TestBuildRecipe:
    def test_defaults(self):
        recipe = build_recipe({"name": " Porridge ", "ingredients": "Oats", "steps": "Heat"}, "u1")
        assert recipe == {
            "uuid": "u1",
            "name": "Porridge",
            "category": "Uncategorised",
            "serves": 2,
            "status": "Untested",
            "ingredients": ["Oats"],
            "steps": ["Heat"],
        }

    def test_given_values_are_kept(self):
        recipe = build_recipe(
            {"name": "Soup", "category": "Lunch", "serves": "4", "status": "Approved",
             "ingredients": ["Tomato"], "steps": ["Boil"]},
            "u2",
        )
        assert recipe["category"] == "Lunch"
        assert recipe["serves"] == 4
        assert recipe["status"] == "Approved"

    def test_unreadable_serves_falls_back_to_default(self):
        recipe = build_recipe({"name": "Soup", "serves": "lots", "ingredients": "a", "steps": "b"}, "u3")
        assert recipe["serves"] == 2
