import re

ALL_CATEGORIES_LABEL = "All"

_BULLET_REGEX = re.compile(r"^\s*(?:[-*•·]|\d+[.)](?!\d))\s+")


def clean_line(line):
    return _BULLET_REGEX.sub("", line.strip())


def safe_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "recipe"


def unique_categories(recipes):
    categories = sorted({recipe["category"] for recipe in recipes}, key=str.lower)
    return [ALL_CATEGORIES_LABEL] + categories


def fetch_recipe(recipes, uuid):
    for recipe in recipes:
        if recipe.get("uuid") == uuid:
            return recipe
    return None


def fetch_recipe_categories(existing_categories, recipe_category):
    categories = [category for category in existing_categories if category != ALL_CATEGORIES_LABEL]
    if recipe_category not in categories:
        categories.append(recipe_category)
    return sorted(categories, key=str.lower)
