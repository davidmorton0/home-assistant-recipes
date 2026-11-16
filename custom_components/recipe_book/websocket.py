"""The websocket command the card reads the recipes with."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_recipes)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/recipes"})
@callback
def ws_recipes(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """All recipes, sorted by name."""
    book = next(iter(hass.data.get(DOMAIN, {}).values()), None)
    recipes = book.public_recipes() if book is not None else []
    connection.send_result(msg["id"], {"recipes": recipes})
