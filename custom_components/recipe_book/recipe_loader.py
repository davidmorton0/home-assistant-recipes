import os
import yaml
import logging

_LOGGER = logging.getLogger(__name__)

REQUIRED_FIELDS = ("uuid", "name", "ingredients", "steps")
DEFAULTS = {
    "category": "Uncategorised",
    "status": "Untested",
}


class RecipeLoader:
    def call(self, path):
        recipes = []
        for filepath in self._list_files(path):
            recipes.extend(self._parse_file(filepath))
        return sorted(recipes, key=lambda r: r["name"].lower())

    def _list_files(self, path):
        if not os.path.isdir(path):
            return []
        files = [f for f in os.listdir(path) if f.endswith((".yaml", ".yml"))]
        return sorted(os.path.join(path, f) for f in files)

    def _parse_file(self, path):
        with open(path, "r") as f:
            text = f.read()
        try:
            data = yaml.safe_load(text)
        except Exception as e:
            _LOGGER.error(f"Failed to parse {path}: {e}")
            return []
        recipes = self._normalise(data, path)
        for recipe in recipes:
            recipe["_file"] = path
        return recipes

    def _normalise(self, data, path):
        if not isinstance(data, list):
            _LOGGER.warning(f"Skipping {path}: top-level is not a list")
            return []
        return [self._apply_defaults(e) for e in data if self._is_valid(e, path)]

    def _is_valid(self, entry, path):
        if not isinstance(entry, dict):
            _LOGGER.warning(f"Skipping an entry in {path}: not a dict")
            return False
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            _LOGGER.warning(f"Skipping an entry in {path}: missing field(s) {missing}")
            return False
        return True

    def _apply_defaults(self, recipe):
        for key, default in DEFAULTS.items():
            recipe.setdefault(key, default)
        return recipe
