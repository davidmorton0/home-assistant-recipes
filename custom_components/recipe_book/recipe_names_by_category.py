ALL_CATEGORIES_LABEL = "All"

class RecipeNamesByCategory:
    def call(self, recipes, category):
        recipe_names = []

        for recipe in recipes:
            if self._matches(recipe, category):
                recipe_names.append(recipe["name"])

        return sorted(recipe_names)
    
    def _matches(self, recipe, category):
        if category == ALL_CATEGORIES_LABEL:
            return True
        if recipe.get("category") == category:
            return True
        return False
