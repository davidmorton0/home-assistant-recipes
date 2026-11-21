"""The skill's script, against a stub of Home Assistant's REST API."""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

# The Home Assistant test plugin blocks sockets; these tests talk to a local stub server.
pytestmark = pytest.mark.enable_socket

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skill" / "recipe-to-home-assistant" / "scripts" / "recipes_to_ha.py"
)
TOKEN = "test-token"
PORRIDGE = {
    "uuid": "u1", "name": "Porridge", "category": "Breakfast", "serves": 2,
    "status": "Untested", "ingredients": ["Oats"], "steps": ["Heat"],
}


@pytest.fixture
def script():
    spec = importlib.util.spec_from_file_location("recipes_to_ha", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ha(script, tmp_path):
    """A stub server; `calls` holds (path, body) for each request."""
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append((self.path, body))
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                return self._reply(401, {"message": "Unauthorized"})
            if self.path == "/api/services/recipe_book/get_recipes?return_response":
                return self._reply(200, {"changed_states": [], "service_response": {"recipes": [PORRIDGE]}})
            if self.path == "/api/services/recipe_book/add_recipe?return_response":
                return self._reply(200, {"changed_states": [], "service_response": {"uuid": "new-uuid"}})
            return self._reply(200, [])

        def _reply(self, code, data):
            payload = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"base_url": f"http://127.0.0.1:{server.server_port}/", "token": TOKEN}))
    script.CONFIG = config
    yield calls
    server.shutdown()
    server.server_close()


def recipe_file(tmp_path, **fields):
    data = {"name": "Tomato soup", "category": "Soup", "serves": 4,
            "ingredients": ["Tomatoes"], "steps": ["Boil"], **fields}
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_add_sends_the_recipe_and_prints_the_uuid(script, ha, tmp_path, capsys):
    assert script.main(["add", recipe_file(tmp_path)]) == 0
    assert ha == [("/api/services/recipe_book/add_recipe?return_response", {
        "name": "Tomato soup", "category": "Soup", "serves": 4, "status": "Untested",
        "ingredients": ["Tomatoes"], "steps": ["Boil"],
    })]
    assert capsys.readouterr().out == "added 'Tomato soup' new-uuid\n"


def test_add_dry_run_sends_nothing(script, ha, tmp_path):
    assert script.main(["add", recipe_file(tmp_path), "--dry-run"]) == 0
    assert ha == []


def test_add_refuses_a_recipe_without_steps(script, ha, tmp_path, capsys):
    assert script.main(["add", recipe_file(tmp_path, steps=[" "])]) == 1
    assert ha == []
    assert "steps is empty" in capsys.readouterr().err


def test_list_prints_one_line_per_recipe(script, ha, capsys):
    assert script.main(["list", "--search", "oats"]) == 0
    assert capsys.readouterr().out == "Breakfast | Porridge | serves 2 | Untested | u1\n1 recipes\n"


def test_update_sends_the_uuid_and_every_field(script, ha, tmp_path):
    assert script.main(["update", "u1", recipe_file(tmp_path, name="Porridge")]) == 0
    assert ha[-1] == ("/api/services/recipe_book/update_recipe", {
        "uuid": "u1", "name": "Porridge", "category": "Soup", "serves": 4,
        "status": "Untested", "ingredients": ["Tomatoes"], "steps": ["Boil"],
    })


def test_status_and_delete_refuse_an_unknown_uuid(script, ha, capsys):
    assert script.main(["status", "nope", "Approved"]) == 1
    assert script.main(["delete", "nope"]) == 1
    assert [path for path, _ in ha] == ["/api/services/recipe_book/get_recipes?return_response"] * 2


def test_delete_sends_the_uuid(script, ha):
    assert script.main(["delete", "u1"]) == 0
    assert ha[-1] == ("/api/services/recipe_book/delete_recipe", {"uuid": "u1"})


def test_wrong_token_reports_401(script, ha, capsys):
    script.CONFIG.write_text(json.dumps({"base_url": json.loads(script.CONFIG.read_text())["base_url"], "token": "bad"}))
    assert script.main(["list"]) == 1
    assert "replied 401" in capsys.readouterr().err
