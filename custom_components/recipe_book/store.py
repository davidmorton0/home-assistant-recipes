"""Reading and writing the recipe folder. Blocking I/O: run in the executor."""

from __future__ import annotations

import os
from typing import Any

from .recipe_loader import RecipeLoader
from .recipe_writer import RecipeWriter
from .utils import fetch_recipe, safe_slug


class RecipeNotFound(Exception):
    """No loaded recipe has that uuid."""


class RecipeStore:
    """The recipe files in one folder."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self._loader = RecipeLoader()
        self._writer = RecipeWriter()

    def ensure_directory(self) -> None:
        os.makedirs(self.directory, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        """All valid recipes, sorted by name. Each holds its file in `_file`."""
        return self._loader.call(self.directory)

    def add(self, recipe: dict[str, Any]) -> str:
        """Write a new single-recipe file named after the recipe. Returns its path."""
        path = self._free_path(safe_slug(recipe["name"]))
        self._writer.call(path, recipe)
        return path

    def replace(self, recipes: list[dict[str, Any]], recipe: dict[str, Any]) -> str:
        """Overwrite the file that holds the recipe with that uuid."""
        path = self._path_of(recipes, recipe["uuid"])
        self._writer.call(path, recipe)
        return path

    def delete(self, recipes: list[dict[str, Any]], uuid: str) -> str:
        """Remove the file that holds the recipe with that uuid."""
        path = self._path_of(recipes, uuid)
        os.remove(path)
        return path

    def _path_of(self, recipes: list[dict[str, Any]], uuid: str) -> str:
        recipe = fetch_recipe(recipes, uuid)
        if recipe is None or not recipe.get("_file"):
            raise RecipeNotFound(f"No recipe with uuid {uuid}")
        return recipe["_file"]

    def _free_path(self, slug: str) -> str:
        path = os.path.join(self.directory, f"{slug}.yaml")
        n = 2
        while os.path.exists(path):
            path = os.path.join(self.directory, f"{slug}_{n}.yaml")
            n += 1
        return path
