"""Exercise the installed CLI contract with existing and current story caches."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[2] / "skills/ground-news/scripts"
sys.path.insert(0, str(SCRIPTS))
import ground_news
from ground_news_client import Cache, Client


class ReaderQualityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.cache = Cache(self.directory)
        self.event = {
            "id": "robot-moon", "title": "Moon mission", "generatedHeadline": "Robots on the Moon",
            "description": "Mission description.", "summary": "Additional details from Ground.",
        }
        self.url = "https://publisher.example/robot-moon"
        client = Client(self.cache, timeout=2)
        with patch.object(client, "fetch", return_value={"summary": self.event}):
            ground_news.read_story(client, self.event["id"], 0)
        with patch.object(client, "fetch", return_value={"status": "event", "event": self.event}):
            ground_news.lookup(client, self.url)

    def cli(self, *args):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "ground_news.py"), *args],
            cwd=self.directory,
            env={**os.environ, "GROUND_NEWS_CACHE_DIR": str(self.directory)},
            text=True, capture_output=True, check=True,
        )
        return json.loads(result.stdout)["data"]

    def assert_readable_cards(self):
        page = self.cli("cache", "list")["entries"]
        self.assertEqual(len(page), 2)
        filtered = self.cli("cache", "search", "Robots", "--kind", "story")["entries"]
        self.assertEqual(filtered, [entry for entry in page if entry["kind"] == "story"])
        for entry in page:
            self.assertEqual(entry["title"], self.event["generatedHeadline"])
            self.assertEqual(entry["story_id"], self.event["id"])
            self.assertEqual(entry["label"], self.url if entry["kind"] == "lookup" else self.event["id"])
            saved = self.cli("cache", "show", entry["key"])
            self.assertEqual({k: v for k, v in saved.items() if k != "payload"}, entry)
            self.assertNotIn("payload", entry)

    def test_current_cache(self):
        self.assert_readable_cards()
        story = self.cli("story", self.event["id"], "--cache-only")
        lookup = self.cli("lookup", self.url, "--cache-only")
        self.assertEqual(story["summary"], self.event["summary"])
        self.assertEqual(lookup["event"]["summary"], self.event["summary"])

    def test_legacy_cache_without_card_table(self):
        with sqlite3.connect(self.cache.path) as db:
            db.execute("DROP TABLE story_cards")
        self.assert_readable_cards()

    def test_refreshed_lookup_without_match(self):
        client = Client(self.cache, timeout=2, refresh=True)
        with patch.object(client, "fetch", return_value={"status": "not_news"}):
            ground_news.lookup(client, self.url)
        entry = self.cli("cache", "list", "--kind", "lookup")["entries"][0]
        self.assertNotIn("story_id", entry)
        self.assertNotIn("title", entry)


if __name__ == "__main__":
    unittest.main()
