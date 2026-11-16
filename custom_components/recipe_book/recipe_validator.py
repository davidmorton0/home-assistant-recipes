class RecipeValidator:
    def validate(self, recipe):
        errors = []
        if not recipe["name"]:
            errors.append("Name is required.")
        if not recipe["ingredients"]:
            errors.append("At least one ingredient is required.")
        if not recipe["steps"]:
            errors.append("At least one step is required.")
        return errors
