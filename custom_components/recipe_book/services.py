"""Services the card calls; they can also be called from scripts and automations."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError

from .book import InvalidRecipe, RecipeBook
from .const import DOMAIN, MAX_CATEGORY_LEN, MAX_NAME_LEN, MAX_SERVES, STATUSES
from .store import RecipeNotFound

SERVICE_RELOAD = "reload_recipes"
SERVICE_ADD = "add_recipe"
SERVICE_UPDATE = "update_recipe"
SERVICE_SET_STATUS = "set_status"
SERVICE_DELETE = "delete_recipe"
SERVICE_GET = "get_recipes"

_LINES = vol.Any(str, [str])

_FIELDS = {
    vol.Required("name"): vol.All(str, vol.Length(max=MAX_NAME_LEN)),
    vol.Optional("category", default=""): vol.All(str, vol.Length(max=MAX_CATEGORY_LEN)),
    vol.Optional("serves"): vol.All(vol.Coerce(int), vol.Range(min=0, max=MAX_SERVES)),
    vol.Optional("status", default=STATUSES[0]): vol.In(STATUSES),
    vol.Required("ingredients"): _LINES,
    vol.Required("steps"): _LINES,
}
ADD_SCHEMA = vol.Schema(_FIELDS)
UPDATE_SCHEMA = vol.Schema({vol.Required("uuid"): str, **_FIELDS})
SET_STATUS_SCHEMA = vol.Schema({vol.Required("uuid"): str, vol.Required("status"): vol.In(STATUSES)})
DELETE_SCHEMA = vol.Schema({vol.Required("uuid"): str})

ALL_SERVICES = (
    SERVICE_RELOAD,
    SERVICE_ADD,
    SERVICE_UPDATE,
    SERVICE_SET_STATUS,
    SERVICE_DELETE,
    SERVICE_GET,
)


def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_ADD):
        return
    hass.services.async_register(DOMAIN, SERVICE_RELOAD, _reload)
    # Returns the new recipe's uuid when called with return_response.
    hass.services.async_register(
        DOMAIN, SERVICE_ADD, _add, schema=ADD_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(DOMAIN, SERVICE_UPDATE, _update, schema=UPDATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_STATUS, _set_status, schema=SET_STATUS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DELETE, _delete, schema=DELETE_SCHEMA)
    # For callers outside the card, such as the REST API, which cannot use the websocket command.
    hass.services.async_register(
        DOMAIN, SERVICE_GET, _get, schema=vol.Schema({}), supports_response=SupportsResponse.ONLY
    )


def async_remove_services(hass: HomeAssistant) -> None:
    for service in ALL_SERVICES:
        hass.services.async_remove(DOMAIN, service)


def _book(call: ServiceCall) -> RecipeBook:
    book = next(iter(call.hass.data.get(DOMAIN, {}).values()), None)
    if book is None:
        raise ServiceValidationError("Recipe Book is not loaded")
    return book


async def _reload(call: ServiceCall) -> None:
    await _book(call).async_reload()


async def _add(call: ServiceCall) -> ServiceResponse:
    try:
        recipe = await _book(call).async_add(dict(call.data))
    except InvalidRecipe as err:
        raise ServiceValidationError(f"Cannot save: {err}") from err
    return {"uuid": recipe["uuid"]} if call.return_response else None


async def _update(call: ServiceCall) -> None:
    data = dict(call.data)
    try:
        await _book(call).async_update(data.pop("uuid"), data)
    except (InvalidRecipe, RecipeNotFound) as err:
        raise ServiceValidationError(f"Cannot save: {err}") from err


async def _set_status(call: ServiceCall) -> None:
    try:
        await _book(call).async_set_status(call.data["uuid"], call.data["status"])
    except (InvalidRecipe, RecipeNotFound) as err:
        raise ServiceValidationError(str(err)) from err


async def _delete(call: ServiceCall) -> None:
    try:
        await _book(call).async_delete(call.data["uuid"])
    except RecipeNotFound as err:
        raise ServiceValidationError(str(err)) from err


async def _get(call: ServiceCall) -> ServiceResponse:
    """All recipes, sorted by name, as the websocket command gives them."""
    return {"recipes": _book(call).public_recipes()}
