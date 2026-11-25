"""Browser extension record tests through the CLI parser and shared cache."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "ground-news" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from ground_news import build_parser, run_cache, run_read
from ground_news_client import Cache, Client, EXTENSION_BASE, GroundError


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Cache(Path(self.temp.name))
        self.parser = build_parser()

    def test_popup_toolbar_and_cached_replay(self):
        story = {"id": "current-cluster", "left": 40, "right": 40, "center": 20, "sourceCount": 6, "biasSourceCount": 5}
        popup = {"story": story, "topSources": []}
        toolbar = {**popup, "source": {"id": "p1", "name": "Gazette", "readableBias": "Center"}}
        for args, expected, suffix, kind in [
            (["extension", "s1"], popup, "/popupData/s1", "extension-popup"),
            (["extension", "s1", "--publisher-id", "p1"], toolbar, "/toolbarData/s1/p1", "extension-toolbar"),
        ]:
            with self.subTest(kind), patch.object(Client, "fetch", return_value=expected) as fetch:
                client = Client(self.cache, 2)
                self.assertEqual(run_read(client, self.parser.parse_args(args)), expected)
                fetch.assert_called_once_with(EXTENSION_BASE + suffix, None)
                cached = Client(self.cache, 2, cache_only=True)
                self.assertEqual(run_read(cached, self.parser.parse_args(args + ["--cache-only"])), expected)
                self.assertEqual(cached.reads[0]["origin"], "cache")
                self.assertEqual(fetch.call_count, 1)
                entries = run_cache(self.cache, self.parser.parse_args(["cache", "list", "--kind", kind]))["entries"]
                self.assertEqual([entry["key"] for entry in entries], [client.reads[0]["key"]])

    def test_rejects_mismatched_publisher_or_story(self):
        args = self.parser.parse_args(["extension", "s1", "--publisher-id", "p1"])
        for payload in [
            {"story": {}, "source": {"id": "p1"}, "topSources": []},
            {"story": {"id": "s1"}, "source": {"id": "wrong"}, "topSources": []},
            {"story": {"id": "s1"}, "topSources": []},
        ]:
            with self.subTest(payload=json.dumps(payload)), patch.object(Client, "fetch", return_value=payload):
                with self.assertRaises(GroundError) as outcome:
                    run_read(Client(self.cache, 2), args)
                self.assertEqual(outcome.exception.details["kind"], "response")
        self.assertEqual(self.cache.browse([], "extension-toolbar", 10), [])


if __name__ == "__main__":
    unittest.main()
