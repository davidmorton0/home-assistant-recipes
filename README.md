# Recipe Book

A Home Assistant custom integration for browsing, adding, editing and deleting
recipes. Recipes are stored as YAML files, one recipe per file, in
`config/recipe_book/`.

## What it does

- Adds a **Recipes** page to the sidebar: category and recipe pickers, the
  selected recipe, buttons to mark it Attempted or Approved, edit it or delete it,
  and a form to add a new one.
- Provides the same view as a card (`custom:recipe-book-card`), for use on any
  dashboard, for example one cast to a Nest Hub.
- Adds `sensor.recipe_book`, which holds the number of recipes.
- Adds services to add, update, delete and reload recipes and to set a recipe's status.

## Installing

1. In HACS, add this repository as a custom repository with the category
   **Integration**, install **Recipe Book**, and restart Home Assistant.
2. Go to **Settings → Devices & services → Add integration → Recipe Book**.
3. Put any existing recipe files in `config/recipe_book/` and call
   `recipe_book.reload_recipes`, or restart.

The **Recipes** page is part of the integration and cannot be edited in the UI.

## Casting to a display

`cast.show_lovelace_view` shows a Lovelace dashboard view, so cast a view that
holds the card:

```yaml
# Dashboard "recipes-cast", view path "cook"
views:
  - title: Cook
    path: cook
    panel: true
    cards:
      - type: custom:recipe-book-card
```

```yaml
action: cast.show_lovelace_view
data:
  entity_id: media_player.kitchen_display
  dashboard_path: recipes-cast
  view_path: cook
```

## Recipe files

Each file holds a YAML list of recipes. Files saved by the integration hold one.

```yaml
- uuid: 5bb305da-7ca5-40b8-8d2b-c799cb9918e4
  name: Asparagus
  category: Vegetable
  serves: 2
  status: Approved
  ingredients:
    - Asparagus
  steps:
    - Chop ends 1 inch
    - Steam for 3 minutes
```

| Field | Rule |
|---|---|
| `uuid` | Required. Identifies the recipe when it is edited, has its status set, or is deleted. |
| `name` | Required. |
| `category` | Optional, default `Uncategorised`. |
| `serves` | Optional whole number. |
| `status` | Optional: `Untested` (default), `Attempted` or `Approved`. |
| `ingredients` | Required list of strings. |
| `steps` | Required list of strings. |

An entry missing a required field, or a file that is not a list, is skipped and
logged. A new recipe's file is named after the recipe (`Mac & Cheese` →
`mac_cheese.yaml`, then `mac_cheese_2.yaml` if that exists). Editing a recipe
overwrites its file and keeps the file name.

## Services

| Service | Fields | What it does |
|---|---|---|
| `recipe_book.add_recipe` | `name`, `ingredients`, `steps`, optional `category`, `serves`, `status` | Saves a new recipe to its own file. |
| `recipe_book.update_recipe` | `uuid` plus the fields above | Overwrites that recipe's file. |
| `recipe_book.set_status` | `uuid`, `status` | Changes only the status. |
| `recipe_book.delete_recipe` | `uuid` | Deletes that recipe's file. |
| `recipe_book.reload_recipes` | none | Reads the files again, after changing them outside Home Assistant. |

`ingredients` and `steps` take a list, or text with one entry per line. Bullets
(`-`, `*`, `•`) and numbering (`1.`, `2)`) at the start of a line are removed. A
recipe with no name, no ingredients or no steps is refused with an error.

## Development

```sh
mise install
poetry install
poetry run pytest tests -q
```
