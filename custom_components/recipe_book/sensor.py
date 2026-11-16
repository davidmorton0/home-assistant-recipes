"""sensor.recipe_book: the number of recipes.

The recipes themselves are sent to the card over the websocket command
`recipe_book/recipes`, not held as attributes, so the recorder does not store
every recipe each time one changes.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .book import RecipeBook
from .const import DOMAIN, SIGNAL_RECIPES_UPDATED


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    book: RecipeBook = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RecipeCountSensor(book, entry)])


class RecipeCountSensor(SensorEntity):
    """How many recipes the folder holds. Changes whenever a recipe is saved or deleted."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_name = "Recipe book"
    _attr_icon = "mdi:chef-hat"
    _attr_native_unit_of_measurement = "recipes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, book: RecipeBook, entry: ConfigEntry) -> None:
        self.book = book
        self._attr_unique_id = f"{entry.entry_id}_count"

    # Not stored in the recorder; it only signals the card.
    _unrecorded_attributes = frozenset({"revision"})

    @property
    def native_value(self) -> int:
        return len(self.book.recipes)

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        # Home Assistant moves last_updated only when the state or an attribute
        # changes. A status change or an edit keeps the count, so this attribute,
        # which goes up on every reload, is what moves last_updated for the card.
        return {"revision": self.book.revision}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_RECIPES_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
