"""Exercise the Hermes entry points against a cache shared with the real CLI."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "ground-news" / "scripts"


def load(name, path, package=False):
    kwargs = {"submodule_search_locations": [str(path.parent)]} if package else {}
    spec = importlib.util.spec_from_file_location(name, path, **kwargs)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plugin = load("_grounded_hermes_test_agent", ROOT / "__init__.py", package=True)
api = load("_grounded_hermes_test_dashboard", ROOT / "dashboard" / "plugin_api.py")
cache_client = load("_grounded_hermes_test_cache", SCRIPTS / "ground_news_client.py")


class Context:
    def __init__(self):
        self.tools = {}
        self.skills = {}

    def register_tool(self, *, name, handler, schema, toolset):
        self.tools[name] = (handler, schema, toolset)

    def register_skill(self, name, path):
        self.skills[name] = path


class PluginTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"GROUND_NEWS_CACHE_DIR": self.temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.cache = cache_client.Cache(Path(self.temp.name))
        self.context = Context()
        plugin.register(self.context)
        app = FastAPI()
        app.include_router(api.router, prefix="/api/plugins/grounded-hermes")
        self.http = self.enterContext(TestClient(app))
        self.story = {
            "id": "story_01",
            "title": "Budget talks resume",
            "slug": "budget-talks-resume",
            "sourceCount": 14,
            "biasSourceCount": 7,
            "blindspotData": {"leftPercent": 0, "centerPercent": 29, "rightPercent": 71},
            "sources": [{
                "url": "https://publisher.example/budget",
                "sourceInfo": {"name": "Publisher", "bias": "center"},
            }],
        }

    def seed(self, kind, label, url, data, body=None):
        request_body = json.dumps(body, sort_keys=True).encode() if body is not None else b""
        digest = hashlib.sha256(url.encode() + b"\x00" + request_body).hexdigest()
        key = f"{kind}:{digest[:24]}"
        self.cache.put(key, kind, label, data)
        return key

    def seed_story(self):
        return self.seed(
            "story", self.story["id"],
            cache_client.API_BASE + f"/public/event/{self.story['id']}/summary",
            {"summary": self.story},
        )

    def tool(self, operation, **args):
        handler = self.context.tools[f"ground_news_{operation}"][0]
        return json.loads(handler(args))

    def read(self, operation, **args):
        response = self.http.post(f"/api/plugins/grounded-hermes/read/{operation}", json=args)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_manifest_tool_and_skill_registration(self):
        manifest = (ROOT / "plugin.yaml").read_text()
        declared = {line.strip()[2:] for line in manifest.splitlines() if line.startswith("  - ")}
        self.assertEqual(set(self.context.tools), declared)
        for name, (_, schema, toolset) in self.context.tools.items():
            self.assertEqual(schema["name"], name)
            self.assertEqual(toolset, "grounded-hermes")
        self.assertTrue(self.context.skills["ground-news"].is_file())

    def test_reuse_cli_story_and_read_snapshot_with_exact_metadata(self):
        key = self.seed_story()
        cli = subprocess.check_output([
            sys.executable, "-B", str(SCRIPTS / "ground_news.py"),
            "story", "--cache-only", self.story["id"],
        ], text=True)
        expected = json.loads(cli)
        self.assertEqual(self.tool("story", story_id=self.story["id"], policy="cache_only"), expected)
        self.assertEqual(self.read("story", story_id=self.story["id"], policy="cache_only"), expected)

        saved = self.read("cache", query="budget talks")["data"]["entries"]
        self.assertEqual([item["cache"]["key"] for item in saved], [key])
        self.assertEqual(saved[0]["sourceCount"], 14)
        self.assertEqual(saved[0]["biasSourceCount"], 7)
        snapshot = self.read("snapshot", key=key)
        self.assertEqual(snapshot["data"], expected["data"])
        self.assertEqual(self.tool("cache", key=key), snapshot)
        self.assertEqual(snapshot["reads"][0]["origin"], "cache")

    def test_search_tool_and_desktop_use_same_request(self):
        query = "--budget"
        self.seed("search-story", query, cache_client.API_BASE + "/public/search?limit=5",
                  {"searchResults": [{"id": self.story["id"], "title": self.story["title"]}]},
                  {"type": "event", "searchText": query})
        result = self.read("search", query=query, kind="story", policy="cache_only")
        self.assertEqual(result, self.tool("search", query=query, kind="story", policy="cache_only"))
        self.assertEqual(result["reads"][0]["origin"], "cache")
        self.assertEqual(result["data"]["searchResults"][0]["id"], self.story["id"])

    def test_cache_misses_and_input_failures_are_actionable(self):
        self.assertEqual(self.read("cache")["data"]["entries"], [])
        self.assertEqual(self.read("story", story_id="missing", policy="cache_only")["error"]["kind"], "cache_miss")
        self.assertEqual(self.read("snapshot", key="story:" + "0" * 24)["error"]["kind"], "cache_miss")
        self.assertEqual(self.read("lookup", url="file:///etc/hosts")["error"]["kind"], "invalid_input")
        self.assertEqual(self.read("search", query="x", limit=True)["error"]["kind"], "invalid_input")
        self.assertEqual(self.read("unknown")["error"]["kind"], "invalid_input")

    def test_cached_article_lookup_and_expansion_share_the_publisher_entry(self):
        self.seed_story()
        url = self.story["sources"][0]["url"]
        cache_key = self.seed("lookup", url, cache_client.LOOKUP_BASE +
                              "/search?url=https%3A%2F%2Fpublisher.example%2Fbudget",
                              {"status": "event", "event": {**self.story, "sourceCount": 21}})
        result = self.tool("lookup", url=url, policy="cache_only")
        self.assertEqual(result["data"]["event"]["sourceCount"], 21)
        coverage = self.read("story", story_id=self.story["id"], more_sources=True, policy="cache_only")
        self.assertEqual(coverage["data"]["sourceCount"], 14)
        self.assertEqual(coverage["data"]["expandedCoverage"]["sourceCount"], 21)
        self.assertEqual([read["kind"] for read in coverage["reads"]], ["story", "lookup"])
        saved = self.read("cache")["data"]["entries"]
        self.assertEqual([item["cache"]["key"] for item in saved], [cache_key])
        self.assertEqual(self.read("snapshot", key=cache_key)["data"]["sourceCount"], 21)

    def test_partial_feed_preserves_ids_and_cached_detail_misses(self):
        interest_id = "parliament"
        base = cache_client.API_BASE + f"/public/interest/{interest_id}"
        self.seed_story()
        self.seed("interest", interest_id, base, {"interest": {"id": interest_id, "name": "Parliament"}})
        self.seed("feed", "Parliament", base + "/events?limit=5", {"eventIds": [self.story["id"], "uncached"]})
        feed = self.read("feed", interest_id=interest_id, policy="cache_only")
        self.assertEqual(feed["data"]["events"]["eventIds"], [self.story["id"], "uncached"])
        self.assertEqual(feed["data"]["stories"][0]["title"], self.story["title"])
        self.assertEqual(feed["data"]["stories"][1]["error"]["kind"], "cache_miss")
        self.assertEqual(self.read("feed", interest_id=interest_id, place="US")["error"]["kind"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
