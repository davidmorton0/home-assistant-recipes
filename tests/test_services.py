"""Services, the websocket command and sensor.recipe_book, with Home Assistant running."""

import os

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

import yaml  # noqa: E402
from homeassistant.exceptions import ServiceValidationError  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.recipe_book.const import DOMAIN, RECIPES_DIR  # noqa: E402

PORRIDGE = """\
- uuid: u1
  name: Porridge
  category: Breakfast
  serves: 2
  status: Untested
  ingredients:
    - Oats
  steps:
    - Heat
"""


@pytest.fixture
def folder(hass, tmp_path):
    # Each test gets its own config folder, so recipes written by one test are not
    # seen by the next.
    hass.config.config_dir = str(tmp_path)
    path = hass.config.path(RECIPES_DIR)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "porridge.yaml"), "w") as f:
        f.write(PORRIDGE)
    return path


@pytest.fixture
async def entry(hass, folder):
    entry = MockConfigEntry(domain=DOMAIN, title="Recipe Book", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def recipes(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/recipes"})
    msg = await client.receive_json()
    assert msg["success"]
    return msg["result"]["recipes"]


async def test_sensor_counts_the_recipes(hass, entry):
    assert hass.states.get("sensor.recipe_book").state == "1"


async def test_websocket_returns_recipes_without_file(hass, entry, hass_ws_client):
    result = await recipes(hass, hass_ws_client)
    assert [r["name"] for r in result] == ["Porridge"]
    assert "_file" not in result[0]


async def test_add_recipe_writes_a_file_and_updates_the_sensor(hass, entry, folder):
    await hass.services.async_call(
        DOMAIN,
        "add_recipe",
        {"name": "Tomato soup", "category": "Soup", "serves": 4,
         "ingredients": "- Tomatoes\n- Stock", "steps": "1. Boil\n2. Blend"},
        blocking=True,
    )
    data = yaml.safe_load(open(os.path.join(folder, "tomato_soup.yaml")))[0]
    assert data["ingredients"] == ["Tomatoes", "Stock"]
    assert data["steps"] == ["Boil", "Blend"]
    assert data["status"] == "Untested"
    assert hass.states.get("sensor.recipe_book").state == "2"


async def test_add_recipe_without_steps_is_refused(hass, entry):
    with pytest.raises(ServiceValidationError, match="At least one step is required"):
        await hass.services.async_call(
            DOMAIN, "add_recipe",
            {"name": "Soup", "ingredients": "Tomatoes", "steps": "  \n"},
            blocking=True,
        )


async def test_update_recipe_overwrites_its_file(hass, entry, folder):
    await hass.services.async_call(
        DOMAIN,
        "update_recipe",
        {"uuid": "u1", "name": "Porridge", "category": "Breakfast", "serves": 3,
         "status": "Approved", "ingredients": "Oats\nMilk", "steps": "Heat"},
        blocking=True,
    )
    data = yaml.safe_load(open(os.path.join(folder, "porridge.yaml")))[0]
    assert data["uuid"] == "u1"
    assert data["serves"] == 3
    assert data["ingredients"] == ["Oats", "Milk"]


async def test_update_unknown_uuid_is_refused(hass, entry):
    with pytest.raises(ServiceValidationError, match="No recipe with uuid"):
        await hass.services.async_call(
            DOMAIN, "update_recipe",
            {"uuid": "missing", "name": "X", "ingredients": "a", "steps": "b"},
            blocking=True,
        )


async def test_set_status_changes_only_the_status(hass, entry, folder):
    await hass.services.async_call(
        DOMAIN, "set_status", {"uuid": "u1", "status": "Attempted"}, blocking=True
    )
    data = yaml.safe_load(open(os.path.join(folder, "porridge.yaml")))[0]
    assert data == {
        "uuid": "u1", "name": "Porridge", "category": "Breakfast", "serves": 2,
        "status": "Attempted", "ingredients": ["Oats"], "steps": ["Heat"],
    }


async def test_delete_recipe_removes_its_file(hass, entry, folder):
    await hass.services.async_call(DOMAIN, "delete_recipe", {"uuid": "u1"}, blocking=True)
    assert not os.path.exists(os.path.join(folder, "porridge.yaml"))
    assert hass.states.get("sensor.recipe_book").state == "0"


async def test_reload_reads_files_changed_on_disk(hass, entry, folder):
    with open(os.path.join(folder, "soup.yaml"), "w") as f:
        f.write(PORRIDGE.replace("u1", "u2").replace("Porridge", "Soup"))
    await hass.services.async_call(DOMAIN, "reload_recipes", {}, blocking=True)
    assert hass.states.get("sensor.recipe_book").state == "2"


async def test_unload_removes_the_services(hass, entry):
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "add_recipe")
