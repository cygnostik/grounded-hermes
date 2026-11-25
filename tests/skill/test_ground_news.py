"""Exercise the installed CLI against a controlled public-API substitute."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


SKILL = Path(__file__).resolve().parents[2] / "skills" / "ground-news"
ARTICLE = "https://example.org/mission?ref=a&locale=en"
STORY = {
    "id": "story-artemis", "title": "Artemis launch", "slug": "artemis-launch_123",
    "sourceCount": 34, "biasSourceCount": 20,
    "blindspotData": {"leftPercent": 15, "centerPercent": 65, "rightPercent": 20},
    "sources": [{"url": ARTICLE, "sourceInfo": {"id": "publisher-id", "name": "Example News"}}],
    "factuality": {"high": 7}, "ownership": {"independent": 2}, "upstreamExtra": {"kept": True},
}
INTEREST = {"id": "feed-id", "legacyId": "publisher-id", "name": "Example News", "type": "source"}
PLACE = {"id": "place-id", "name": "United States", "type": "place"}
SUMMARY = "/public/event/story-artemis/summary"
EDITIONS = "/v04/customFeed/topFeedEditions"
SEARCH = "/public/search?limit=2"
WRAPPER = """
import runpy
import sys
from pathlib import Path
script, base, *args = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
import ground_news_client as client
client.API_BASE = client.LOOKUP_BASE = base
client.MIN_INTERVAL = 0.08
client.MAX_RETRY_WAIT = 0.2
sys.argv = [script, *args]
runpy.run_path(script, run_name="__main__")
"""


class Server(ThreadingHTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.calls = []
        self.overrides = {}
        self.guard = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.respond(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))

    def do_GET(self):
        self.respond()

    def log_message(self, *_):
        pass

    def respond(self, body=None):
        with self.server.guard:
            self.server.calls.append((self.path, body, time.monotonic()))
            queue = self.server.overrides.get(self.path, [])
            override = queue.pop(0) if queue else None
        code, headers, value, delay = override or self.default(body)
        time.sleep(delay)
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(code)
        for name, content in headers.items():
            self.send_header(name, content)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def default(self, body):
        path = urlsplit(self.path)
        responses = {
            SUMMARY: {"summary": STORY},
            "/public/interest/feed-id": {"interest": INTEREST},
            "/public/interest/feed-id/events": {"eventIds": ["story-artemis", "story-missing"]},
            "/public/interest/feed-id/trending": {"interests": [{"id": "related-id", "name": "Space"}]},
            "/public/interest/place-id/events": {"eventIds": ["story-artemis"]},
            "/public/place/US/interest": {"interest": PLACE},
            "/public/interest/blindspot/blindspots": {"left": ["story-artemis"], "right": ["story-missing"]},
            EDITIONS: {"editions": [{"id": "US", "webFeedId": "top-us"}]},
        }
        if path.path == "/public/search" and body:
            result = (
                [{"id": STORY["id"], "title": STORY["title"]}]
                if body["type"] == "event"
                else [{"id": INTEREST["id"], "title": INTEREST["name"], "subType": "source"}]
            )
            data = {"searchResults": [] if body["searchText"] == "empty" else result}
        elif path.path == "/search":
            url, = parse_qs(path.query)["url"]
            if url == ARTICLE:
                other_source = {"url": "https://second.example/report", "sourceInfo": {"id": "other-id"}}
                data = {
                    "status": "event",
                    "event": {**STORY, "sourceCount": 35, "sources": [*STORY["sources"], other_source]},
                    "source": {"id": "publisher-id"}, "refId": "ref-id", "url": url,
                }
            else:
                data = {"status": "not_news", "url": url}
        else:
            data = responses.get(path.path)
        return (200, {}, data, 0) if data is not None else (404, {}, {"error": "not found"}, 0)


@contextmanager
def local_server():
    with Server() as server:
        worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        worker.start()
        try:
            yield server, f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            worker.join()


class GroundNewsCLI(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.temporary = Path(temp_dir.name)
        self.cache_dir = self.temporary / "cache"
        self.skill = self.temporary / ".agents" / "skills" / "ground-news"
        self.script = self.skill / "scripts" / "ground_news.py"
        shutil.copytree(SKILL, self.skill)
        server = local_server()
        self.server, self.base = server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)

    def run_cli(self, *args, code=0, mock=True):
        command = [sys.executable, "-B", str(self.script)]
        if mock:
            command = [sys.executable, "-B", "-c", WRAPPER, str(self.script), self.base]
        result = subprocess.run(
            [*command, *args], cwd=self.temporary, timeout=10, text=True, capture_output=True,
            env={**os.environ, "GROUND_NEWS_CACHE_DIR": str(self.cache_dir)},
        )
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        if code == 2 or "--help" in args:
            return result.stderr or result.stdout
        self.assertEqual(result.stdout if code else result.stderr, "")
        return json.loads(result.stderr if code else result.stdout)

    def test_installed_script_help_and_offline_commands(self):
        self.assertIn("blindspots", self.run_cli("--help", mock=False))
        self.assertEqual(self.run_cli("cache", "list", mock=False)["data"], {"entries": []})
        error = self.run_cli("search", "story", "Artemis", "--cache-only", mock=False, code=1)["error"]
        self.assertEqual(error["kind"], "cache_miss")
        self.run_cli("lookup", "http://user:password@example.org/a", code=2)
        self.run_cli("feed", "a", "--place", "US", code=2)
        self.run_cli("story", "a", "--refresh", "--cache-only", code=2)
        self.assertEqual(self.server.calls, [])

    def test_search_coverage_lookup_and_local_subject_switch(self):
        story_search = self.run_cli("search", "story", "Artemis", "--limit", "2")
        self.assertEqual(story_search["data"]["searchResults"][0]["id"], STORY["id"])
        self.assertEqual(self.server.calls[0][:2], (SEARCH, {"type": "event", "searchText": "Artemis"}))
        source_search = self.run_cli("search", "interest", "Example News", "--limit", "2")
        self.assertEqual(source_search["data"]["searchResults"][0]["id"], INTEREST["id"])
        self.assertEqual(self.server.calls[1][1]["type"], "interest")
        self.assertEqual(self.run_cli("search", "story", "empty")["data"]["searchResults"], [])

        result = self.run_cli("story", STORY["id"], "--more-sources", "--sources-limit", "1", "--raw")
        data = result["data"]
        self.assertEqual((data["biasSourceCount"], data["sourceCount"]), (20, 34))
        self.assertEqual(data["blindspotData"]["centerPercent"], 65)
        self.assertEqual(data["sources"][0]["sourceInfo"]["id"], "publisher-id")
        self.assertEqual(data["groundUrl"], "https://ground.news/article/artemis-launch_123")
        self.assertEqual(data["expandedCoverage"]["sourceEntriesAvailable"], 2)
        self.assertEqual(data["expandedCoverage"]["sourceCount"], 35)
        key = result["reads"][0]["key"]
        self.assertEqual(result["upstream"][key]["summary"]["upstreamExtra"], {"kept": True})

        repeat = self.run_cli("lookup", ARTICLE + "#fragment")
        self.assertEqual(repeat["data"]["event"]["id"], STORY["id"])
        self.assertEqual(repeat["data"]["refId"], "ref-id")
        self.assertEqual(repeat["reads"][0]["origin"], "cache")
        miss = self.run_cli("lookup", "https://example.org/unknown")
        self.assertIsNone(miss["data"]["event"])
        self.assertEqual(miss["data"]["status"], "not_news")

        before = len(self.server.calls)
        matches = self.run_cli("cache", "search", "ARTEMIS example", "--kind", "story", mock=False)
        self.assertEqual(matches["data"]["entries"][0]["key"], key)
        self.assertEqual(self.run_cli("cache", "show", key, mock=False)["data"]["payload"], {"summary": STORY})
        self.assertEqual(len(self.server.calls), before)

    def test_feed_trending_editions_and_blindspot_details(self):
        feed = self.run_cli("feed", "feed-id", "--limit", "2", "--details", "2")["data"]
        self.assertEqual(feed["interestId"], "feed-id")
        self.assertEqual(feed["interest"]["legacyId"], "publisher-id")
        self.assertEqual(feed["stories"][0]["title"], STORY["title"])
        self.assertEqual(feed["stories"][1]["error"]["status"], 404)
        self.assertEqual(self.server.calls[1][0], "/public/interest/feed-id/events?limit=2")
        place = self.run_cli("feed", "--place", "us", "--details", "0")["data"]
        self.assertEqual(place["interest"], PLACE)
        self.assertEqual(place["stories"], [])
        self.assertEqual(self.run_cli("trending", "feed-id")["data"]["interests"][0]["id"], "related-id")
        self.assertEqual(self.run_cli("editions")["data"]["editions"][0]["webFeedId"], "top-us")
        blind = self.run_cli("blindspots")
        self.assertEqual(blind["data"]["left"], [STORY["id"]])
        self.assertEqual(blind["data"]["stories"]["right"][0]["error"]["status"], 404)
        self.assertEqual([read["origin"] for read in blind["reads"]], ["network", "cache"])

    def test_concurrent_requests_reuse_result_and_respect_pacing(self):
        self.server.overrides[SUMMARY] = [(200, {}, {"summary": STORY}, 0.25)]
        with ThreadPoolExecutor(max_workers=3) as executor:
            calls = [executor.submit(self.run_cli, *args) for args in (
                ("story", STORY["id"]), ("story", STORY["id"]), ("editions",),
            )]
            first, second, third = [call.result() for call in calls]
        self.assertCountEqual([first["reads"][0]["origin"], second["reads"][0]["origin"]], ["cache", "network"])
        self.assertEqual(third["reads"][0]["origin"], "network")
        self.assertEqual(Counter(call[0] for call in self.server.calls), {SUMMARY: 1, EDITIONS: 1})
        times = [call[2] for call in self.server.calls]
        self.assertGreaterEqual(times[1] - times[0], 0.06)

    def test_refresh_replaces_response_and_failure_preserves_it(self):
        self.run_cli("story", STORY["id"])
        changed = {**STORY, "title": "Updated Artemis launch"}
        self.server.overrides[SUMMARY] = [
            (200, {}, {"summary": changed}, 0), (200, {}, b"{", 0),
            (200, {}, {"summary": {"id": "wrong-id"}}, 0),
        ]
        refreshed = self.run_cli("story", STORY["id"], "--refresh")
        self.assertEqual(refreshed["data"]["title"], changed["title"])
        self.assertEqual(refreshed["reads"][0]["origin"], "network")
        for _ in range(2):
            error = self.run_cli("story", STORY["id"], "--refresh", code=1)["error"]
            self.assertEqual(error["kind"], "response")
            self.assertEqual(error["cached_at"], refreshed["reads"][0]["fetched_at"])
        repeat = self.run_cli("story", STORY["id"], "--cache-only")
        self.assertEqual(repeat["data"]["title"], changed["title"])
        self.assertEqual(len(self.server.calls), 4)

    def test_retry_after_and_shared_cooldown(self):
        self.server.overrides[EDITIONS] = [(429, {"Retry-After": "0"}, {}, 0)]
        self.assertTrue(self.run_cli("editions")["data"]["editions"])
        self.assertEqual(len(self.server.calls), 2)
        deadline = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
        self.server.overrides[SUMMARY] = [(503, {"Retry-After": deadline}, {}, 0)]
        error = self.run_cli("story", STORY["id"], code=1)["error"]
        self.assertEqual(error["status"], 503)
        self.assertGreater(error["retry_after_seconds"], 25)
        blocked = self.run_cli("editions", "--refresh", code=1)["error"]
        self.assertEqual(blocked["kind"], "cooldown")
        self.assertEqual(self.run_cli("editions")["reads"][0]["origin"], "cache")
        self.assertEqual(len(self.server.calls), 3)

    def test_socket_timeout_is_reported_and_not_cached(self):
        self.server.overrides[EDITIONS] = [(200, {}, {"editions": []}, 1.4)]
        error = self.run_cli("editions", "--timeout", "1", code=1)["error"]
        self.assertEqual(error["kind"], "timeout")
        self.assertEqual(self.run_cli("cache", "list")["data"]["entries"], [])

    def test_story_mismatch_leaves_original_coverage(self):
        query = "/search?url=https%3A%2F%2Fexample.org%2Fmission%3Fref%3Da%26locale%3Den"
        self.server.overrides[query] = [
            (200, {}, {"status": "event", "event": {**STORY, "id": "other-story"}}, 0),
        ]
        result = self.run_cli("story", STORY["id"], "--more-sources")["data"]
        self.assertEqual(result["id"], STORY["id"])
        self.assertEqual(result["expansionError"]["kind"], "no_match")
        self.assertNotIn("expandedCoverage", result)

    def test_merged_cluster_preserves_requested_and_canonical_ids(self):
        old_id = "previous-story"
        alias_path = f"/public/event/{old_id}/summary"
        self.server.overrides[alias_path] = [(200, {}, {"summary": STORY}, 0)]
        result = self.run_cli("story", old_id, "--more-sources")
        data = result["data"]
        self.assertEqual((data["requestedStoryId"], data["id"]), (old_id, STORY["id"]))
        self.assertEqual(data["expandedCoverage"]["id"], STORY["id"])
        self.assertEqual(result["reads"][0]["label"], old_id)
        replay = self.run_cli("story", old_id, "--more-sources", "--cache-only")
        self.assertEqual(replay["data"], data)
        self.assertTrue(all(read["origin"] == "cache" for read in replay["reads"]))
        query = self.server.calls[-1][0]
        self.server.overrides[alias_path] = [(200, {}, {"summary": STORY}, 0)]
        self.server.overrides[query] = [(200, {}, {"status": "event", "event": {**STORY, "id": "third-id"}}, 0)]
        other = self.run_cli("story", old_id, "--more-sources", "--refresh")["data"]
        self.assertEqual(other["expansionError"]["kind"], "no_match")
        self.assertNotIn("expandedCoverage", other)


if __name__ == "__main__":
    unittest.main()
