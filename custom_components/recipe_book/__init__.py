"""The Recipe Book integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .book import RecipeBook
from .const import DOMAIN, RECIPES_DIR
from .services import async_register_services, async_remove_services
from .websocket import async_register_commands

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CARD_URL = "/recipe_book/recipe-book-card.js"
PANEL_URL = "/recipe_book/recipe-book-panel.js"
PANEL_PATH = "recipe-book"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Recipe Book from a config entry."""
    book = RecipeBook(hass, hass.config.path(RECIPES_DIR))
    await book.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = book

    if not hass.data.get(f"{DOMAIN}_registered"):
        folder = Path(__file__).parent
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(CARD_URL, str(folder / "recipe-book-card.js"), False),
                StaticPathConfig(PANEL_URL, str(folder / "recipe-book-panel.js"), False),
            ]
        )
        # The card, loaded on every page so any dashboard can use it too.
        if "frontend" in hass.config.components:
            add_extra_js_url(hass, CARD_URL)
        async_register_commands(hass)
        hass.data[f"{DOMAIN}_registered"] = True

    async_register_services(hass)

    if "frontend" in hass.config.components:
        try:
            await panel_custom.async_register_panel(
                hass,
                frontend_url_path=PANEL_PATH,
                webcomponent_name="recipe-book-panel",
                sidebar_title="Recipes",
                sidebar_icon="mdi:chef-hat",
                module_url=PANEL_URL,
            )
        except ValueError:
            _LOGGER.warning(
                "The Recipes page was not added, because something else is already at "
                "/%s. Delete that dashboard in Settings > Dashboards and restart",
                PANEL_PATH,
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        async_remove_services(hass)
        async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    return unloaded
