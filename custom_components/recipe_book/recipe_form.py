"""Turn what the card or a service call sends into a recipe dict."""

from __future__ import annotations

from typing import Any

from .const import DEFAULT_SERVES, DEFAULT_STATUS, UNCATEGORISED
from .utils import clean_line


def lines(value: Any) -> list[str]:
    """One entry per non-blank line; a list is taken line by line too.

    Bullets and numbering at the start of a line are removed, so a pasted list
    reads the same as a typed one.
    """
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.splitlines()
    else:
        raw = [line for item in value for line in str(item).splitlines()]
    return [clean_line(line) for line in raw if line.strip()]


def build_recipe(data: dict[str, Any], uuid: str) -> dict[str, Any]:
    """A recipe dict in the shape RecipeWriter writes."""
    serves = data.get("serves")
    try:
        serves = int(float(serves)) if serves is not None else DEFAULT_SERVES
    except (TypeError, ValueError):
        serves = DEFAULT_SERVES

    return {
        "uuid": uuid,
        "name": (data.get("name") or "").strip(),
        "category": (data.get("category") or "").strip() or UNCATEGORISED,
        "serves": serves,
        "status": (data.get("status") or "").strip() or DEFAULT_STATUS,
        "ingredients": lines(data.get("ingredients")),
        "steps": lines(data.get("steps")),
    }
