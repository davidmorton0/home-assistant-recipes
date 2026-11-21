#!/usr/bin/env python3
"""Add, list, read, correct and delete recipes in the Recipe Book integration.

It calls the integration's services through Home Assistant's REST API,
POST /api/services/recipe_book/<service>, with a long-lived access token.

Usage:
  python recipes_to_ha.py add recipe.json [--dry-run]   add a new recipe, prints its uuid
  python recipes_to_ha.py list [--category TEXT] [--search TEXT]
                                                        one line per recipe, ending in its uuid
  python recipes_to_ha.py get UUID                      one recipe, as a recipe file
  python recipes_to_ha.py update UUID recipe.json [--dry-run]
                                                        replace every field of one recipe
  python recipes_to_ha.py status UUID STATUS            set Untested, Attempted or Approved
  python recipes_to_ha.py delete UUID                   delete one recipe

recipe.json, for add and update:
{
  "name": "Tomato soup",                  # required, up to 100 characters
  "category": "Soup",                     # optional, up to 100; default Uncategorised
  "serves": 4,                            # optional whole number 0-100; default 2
  "status": "Untested",                   # optional: Untested (default), Attempted, Approved
  "ingredients": ["400 g tomatoes", "..."],  # required list, one entry per ingredient
  "steps": ["Chop the onion", "..."]         # required list, one entry per step
}
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config.json"
DOMAIN = "recipe_book"
STATUSES = ["Untested", "Attempted", "Approved"]
LIMITS = {"name": 100, "category": 100}
MAX_SERVES = 100
FIELDS = ["name", "category", "serves", "status", "ingredients", "steps"]
TIMEOUT = 30


class Failed(Exception):
    """A problem to print and exit on."""


def load_config():
    try:
        config = json.loads(CONFIG.read_text())
    except FileNotFoundError:
        raise Failed(f"config.json is missing: copy config.example.json to {CONFIG} and fill it in")
    base_url = str(config.get("base_url", "")).rstrip("/")
    token = str(config.get("token", ""))
    if not base_url or "YOUR" in base_url or not token or "YOUR" in token:
        raise Failed("config.json still holds placeholders: set base_url and token")
    return base_url, token


def check_recipe(recipe):
    """The recipe as the service takes it, checking the same rules the integration does."""
    problems = []
    unknown = sorted(set(recipe) - set(FIELDS))
    if unknown:
        problems.append(f"unknown fields: {', '.join(unknown)}")

    name = str(recipe.get("name", "")).strip()
    if not name:
        problems.append("name is empty")
    elif len(name) > LIMITS["name"]:
        problems.append(f"name longer than {LIMITS['name']} characters")

    category = str(recipe.get("category", "") or "").strip()
    if len(category) > LIMITS["category"]:
        problems.append(f"category longer than {LIMITS['category']} characters")

    serves = recipe.get("serves")
    if serves is not None and (
        not isinstance(serves, int) or isinstance(serves, bool) or not 0 <= serves <= MAX_SERVES
    ):
        problems.append(f"serves must be a whole number from 0 to {MAX_SERVES}")

    status = recipe.get("status") or STATUSES[0]
    if status not in STATUSES:
        problems.append(f"status must be one of {', '.join(STATUSES)}")

    lists = {}
    for field in ("ingredients", "steps"):
        value = recipe.get(field)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            problems.append(f"{field} must be a list of strings")
            continue
        lists[field] = [v.strip() for v in value if v.strip()]
        if not lists[field]:
            problems.append(f"{field} is empty")

    if problems:
        raise Failed("recipe refused, nothing sent:\n  " + "\n  ".join(problems))

    data = {"name": name, "status": status, **lists}
    if category:
        data["category"] = category
    if serves is not None:
        data["serves"] = serves
    return data


def call(service, data, want_response=False):
    """Call recipe_book.<service>; returns its service_response, or None."""
    base_url, token = load_config()
    url = f"{base_url}/api/services/{DOMAIN}/{service}"
    if want_response:
        url += "?return_response"
    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
            body = json.loads(reply.read() or b"null")
    except urllib.error.HTTPError as err:
        # Claude's sandbox proxy refuses domains not on its allow list with this header.
        deny = err.headers.get("x-deny-reason")
        if deny:
            raise Failed(f"BLOCKED BY SANDBOX NETWORK: {deny}")
        detail = err.read().decode(errors="replace").strip()
        raise Failed(f"Home Assistant replied {err.code}: {detail or err.reason}")
    except (urllib.error.URLError, TimeoutError) as err:
        reason = getattr(err, "reason", err)
        if isinstance(reason, TimeoutError) or "timed out" in str(reason):
            raise Failed(f"Home Assistant did not reply in time ({reason})")
        raise Failed(f"could not connect to {base_url} ({reason}); nothing was changed")
    if want_response:
        return (body or {}).get("service_response")
    return None


def all_recipes():
    return call("get_recipes", {}, want_response=True)["recipes"]


def find(uuid):
    for recipe in all_recipes():
        if recipe["uuid"] == uuid:
            return recipe
    raise Failed(f"no recipe with uuid {uuid}")


def read_file(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as err:
        raise Failed(f"cannot read {path}: {err}")


def cmd_add(args):
    data = check_recipe(read_file(args.file))
    if args.dry_run:
        print("dry run, would add:\n" + json.dumps(data, indent=2, ensure_ascii=False))
        return
    response = call("add_recipe", data, want_response=True)
    print(f"added '{data['name']}' {response['uuid']}")


def cmd_list(args):
    recipes = all_recipes()
    if args.category:
        recipes = [r for r in recipes if args.category.lower() in r["category"].lower()]
    if args.search:
        text = args.search.lower()
        recipes = [
            r for r in recipes
            if text in r["name"].lower()
            or any(text in line.lower() for line in r["ingredients"])
        ]
    for r in recipes:
        print(f"{r['category']} | {r['name']} | serves {r.get('serves', '')} | {r['status']} | {r['uuid']}")
    print(f"{len(recipes)} recipes")


def cmd_get(args):
    recipe = find(args.uuid)
    print(json.dumps({k: recipe[k] for k in FIELDS if k in recipe}, indent=2, ensure_ascii=False))


def cmd_update(args):
    data = check_recipe(read_file(args.file))
    find(args.uuid)
    if args.dry_run:
        print(f"dry run, would replace {args.uuid} with:\n" + json.dumps(data, indent=2, ensure_ascii=False))
        return
    call("update_recipe", {"uuid": args.uuid, **data})
    print(f"updated '{data['name']}' {args.uuid}")


def cmd_status(args):
    if args.status not in STATUSES:
        raise Failed(f"status must be one of {', '.join(STATUSES)}")
    recipe = find(args.uuid)
    call("set_status", {"uuid": args.uuid, "status": args.status})
    print(f"'{recipe['name']}' is now {args.status}")


def cmd_delete(args):
    recipe = find(args.uuid)
    call("delete_recipe", {"uuid": args.uuid})
    print(f"deleted '{recipe['name']}' {args.uuid}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add")
    p.add_argument("file")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("--category")
    p.add_argument("--search", help="text in the name or an ingredient")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get")
    p.add_argument("uuid")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("update")
    p.add_argument("uuid")
    p.add_argument("file")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("status")
    p.add_argument("uuid")
    p.add_argument("status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("delete")
    p.add_argument("uuid")
    p.set_defaults(func=cmd_delete)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Failed as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
