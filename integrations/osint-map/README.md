# Ground News stories on the Hermes OSINT Map

Export the stories you select from your local Ground News cache. The resulting JSON file is an operator feed for [Hermes OSINT Map 0.5.0](https://github.com/Adolanium/hermes-osint-map/blob/e67cb7dbb970a9a76f77f4e92f53321f47c2a271/osintmap/feeds.py).

From the repository root, run a Ground News coverage or publisher-URL lookup. Copy a story or lookup key from its JSON `reads[].key`, or find one with `python3 skills/ground-news/scripts/ground_news.py cache list --kind story`. Assign that key to the shell variable `story_cache_key` used below. Use the same cache location for the lookup and export. Run the exporter with one or more keys and a destination on the computer running the Hermes gateway.

```sh
python3 integrations/osint-map/export_digest.py --output "$PWD/ground-news-map.json" "$story_cache_key"
```

When a story has a single country code in Ground's place metadata, the exporter uses it. For ambiguous or missing geography, choose a country anchor for that item by appending its two-letter code to the key, for example `"${story_cache_key}=JP"`. This lets you deliberately file a story under a country. The exporter never guesses from a headline. OSINT Map renders a country anchor approximately and can prefer a known chokepoint mentioned in the item's text.

In OSINT Map settings, add the following entry to **Operator feeds**, substituting your gateway's absolute path. Open the **Operator feeds** layer on the globe.

```json
[{"file":"/absolute/path/to/ground-news-map.json","label":"Ground News"}]
```

Pass your complete current selection each time. A successful export atomically replaces the previous digest. A missing record, unsupported anchor or invalid selection leaves the previous file available to the map. The exporter reads the local cache on demand and the map reads the local file on its normal refresh cycle. An installation on a remote gateway must be able to read the file on that gateway.

Run the fixture tests with `python3 -m unittest discover -s integrations/osint-map`. To verify compatibility against a local checkout of OSINT Map, set `OSINT_MAP_CHECKOUT` to its package folder and `PYTHONDONTWRITEBYTECODE=1` before running the same command.
