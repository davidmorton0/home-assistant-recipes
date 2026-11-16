"""Constants for the Recipe Book integration."""

DOMAIN = "recipe_book"

# Recipe files live in <config>/recipe_book/, one YAML file per recipe.
RECIPES_DIR = "recipe_book"

UNCATEGORISED = "Uncategorised"
DEFAULT_STATUS = "Untested"
STATUSES = ["Untested", "Attempted", "Approved"]
DEFAULT_SERVES = 2
MAX_SERVES = 100
MAX_NAME_LEN = 100
MAX_CATEGORY_LEN = 100

SIGNAL_RECIPES_UPDATED = f"{DOMAIN}_recipes_updated"
