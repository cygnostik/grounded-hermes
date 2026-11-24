import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from export_digest import CLI, map_item

sys.path.insert(0, str(CLI.parent))
from ground_news_client import Cache


STORY = {
    "id": "f3869f56-8e77-488b-93a4-1c56fc1071cf",
    "title": "Transit hearing",
    "start": "2026-01-28T10:20:00Z",
    "place": {"id": "QC,CA", "type": "administrative_area_level_1", "name": "Québec"},
    "slug": "transit-hearing",
    "description": "Two <b>outlets</b> cover the regional hearing.",
}


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache_dir = Path(self.tmp.name) / "cache"
        self.cache = Cache(self.cache_dir)
        self.target = Path(self.tmp.name) / "digest.json"
        self.key = "story:" + "a" * 24
        self.cache.put(self.key, "story", "Transit hearing", {"summary": STORY})

    def run_export(self, *keys):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("export_digest.py")), "--output", str(self.target), *keys],
            env={**os.environ, "GROUND_NEWS_CACHE_DIR": str(self.cache_dir)},
            capture_output=True, text=True, timeout=15, check=False,
        )

    def test_file_refresh_is_offline_and_all_or_nothing(self):
        result = self.run_export(self.key)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.target.read_bytes()
        doc = json.loads(before)
        self.assertEqual(doc["items"], [{
            "country": "CA", "time": STORY["start"], "summary": "Two outlets cover the regional hearing.",
            "tag": "ground-news", "title": "Transit hearing", "url": "https://ground.news/article/transit-hearing"
        }])
        result = self.run_export(self.key, "story:" + "b" * 24)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_lookup_record_and_selection_deduplication(self):
        lookup_key = "lookup:" + "c" * 24
        self.cache.put(lookup_key, "lookup", "Example publisher", {"status": "event", "event": STORY})
        result = self.run_export(self.key + "=JP", lookup_key + "=jp")
        self.assertEqual(result.returncode, 0, result.stderr)
        item, = json.loads(self.target.read_bytes())["items"]
        self.assertEqual(item["country"], "JP")
        result = self.run_export(self.key, lookup_key + "=JP")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("two different country anchors", result.stderr)

    def test_country_override_and_empty_geography(self):
        story = dict(STORY, place=[{"id": "US", "type": "country"}, {"id": "CA", "type": "country"}])
        with self.assertRaisesRegex(ValueError, "No unique country"):
            map_item(story, None)
        self.assertEqual(map_item(story, "CA")["country"], "CA")
        with self.assertRaisesRegex(ValueError, "country code"):
            map_item(story, "XX")

    @unittest.skipUnless(os.getenv("OSINT_MAP_CHECKOUT"), "optional OSINT Map parser checkout")
    def test_with_osint_map_loader(self):
        result = self.run_export(self.key)
        self.assertEqual(result.returncode, 0, result.stderr)
        sys.path.insert(0, os.environ["OSINT_MAP_CHECKOUT"])
        self.addCleanup(sys.path.pop, 0)
        from osintmap import feeds
        data = feeds.load({"kind": "file", "file": str(self.target), "label": "Ground News"})
        self.assertEqual(data["dropped"], 0)
        item, = data["items"]
        self.assertEqual((item["country"], item["layer"], item["kind"]), ("CA", "feeds", "ground-news"))
        self.assertEqual(item["url"], "https://ground.news/article/transit-hearing")
        self.assertIsNone(item["lat"])
        self.assertIsNone(item["lon"])


if __name__ == "__main__":
    unittest.main()
