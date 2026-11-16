"""The loaded recipes, and the changes made to them."""

from __future__ import annotations

import asyncio
import logging
import uuid as uuid_lib
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_RECIPES_UPDATED
from .recipe_form import build_recipe
from .recipe_validator import RecipeValidator
from .store import RecipeNotFound, RecipeStore
from .utils import fetch_recipe

_LOGGER = logging.getLogger(__name__)


class InvalidRecipe(Exception):
    """The recipe failed validation; the message lists every problem."""


class RecipeBook:
    """Holds the recipes read from the folder; every change goes through here."""

    def __init__(self, hass: HomeAssistant, directory: str) -> None:
        self.hass = hass
        self.store = RecipeStore(directory)
        self.recipes: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._validator = RecipeValidator()

    def public_recipes(self) -> list[dict[str, Any]]:
        """The recipes without the private `_file` field."""
        return [{k: v for k, v in r.items() if not k.startswith("_")} for r in self.recipes]

    async def async_setup(self) -> None:
        await self.hass.async_add_executor_job(self.store.ensure_directory)
        await self.async_reload()

    async def async_reload(self) -> None:
        self.recipes = await self.hass.async_add_executor_job(self.store.load)
        async_dispatcher_send(self.hass, SIGNAL_RECIPES_UPDATED)

    async def async_add(self, data: dict[str, Any]) -> dict[str, Any]:
        recipe = self._checked(build_recipe(data, str(uuid_lib.uuid4())))
        async with self._lock:
            path = await self.hass.async_add_executor_job(self.store.add, recipe)
            _LOGGER.info("Saved new recipe '%s' to %s", recipe["name"], path)
            await self.async_reload()
        return recipe

    async def async_update(self, uuid: str, data: dict[str, Any]) -> dict[str, Any]:
        recipe = self._checked(build_recipe(data, uuid))
        async with self._lock:
            path = await self.hass.async_add_executor_job(
                self.store.replace, self.recipes, recipe
            )
            _LOGGER.info("Saved edited recipe '%s' to %s", recipe["name"], path)
            await self.async_reload()
        return recipe

    async def async_set_status(self, uuid: str, status: str) -> dict[str, Any]:
        existing = fetch_recipe(self.recipes, uuid)
        if existing is None:
            raise RecipeNotFound(f"No recipe with uuid {uuid}")
        return await self.async_update(uuid, {**existing, "status": status})

    async def async_delete(self, uuid: str) -> None:
        async with self._lock:
            path = await self.hass.async_add_executor_job(
                self.store.delete, self.recipes, uuid
            )
            _LOGGER.info("Deleted recipe %s (%s)", uuid, path)
            await self.async_reload()

    def _checked(self, recipe: dict[str, Any]) -> dict[str, Any]:
        errors = self._validator.validate(recipe)
        if errors:
            raise InvalidRecipe(" ".join(errors))
        return recipe
