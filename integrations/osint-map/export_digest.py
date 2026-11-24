#!/usr/bin/env python3
"""Export selected Ground News cache records to an OSINT Map operator feed."""

import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import quote


CLI = Path(__file__).resolve().parents[2] / "skills/ground-news/scripts/ground_news.py"
# Country anchors supported by OSINT Map 0.5.0's geographic index.
COUNTRIES = frozenset("""
AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AZ BA BB BD BE BF BG BH BI BJ BM BN BO BR BS BT BW BY
BZ CA CD CF CG CH CI CK CL CM CN CO CR CU CV CW CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI
FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HN HR HT HU ID IE IL
IM IN IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY
MA MC MD ME MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NG NI NL NO NP NR NU
NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK
SL SM SN SO SR SS ST SV SX SY SZ TC TD TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG US UY UZ VA
VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW
""".split())


def country_from_place(place):
    """Use only explicit country codes in the story's structured places."""
    if isinstance(place, dict):
        place = [place]
    if not isinstance(place, list):
        return None
    countries = set()
    for entry in place:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("id", "")
        if not isinstance(identifier, str):
            continue
        if entry.get("type") == "country":
            code = identifier
        elif "," in identifier:
            code = identifier.rsplit(",", 1)[1]
        else:
            continue
        if code in COUNTRIES:
            countries.add(code)
    return next(iter(countries)) if len(countries) == 1 else None


def plain_text(value, limit):
    if not isinstance(value, str):
        return ""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())[:limit]


def map_item(story, country):
    if country and country not in COUNTRIES:
        raise ValueError(f"OSINT Map does not recognize country code {country!r}.")
    country = country or country_from_place(story.get("place"))
    if not country:
        raise ValueError("No unique country in the story's place data. Append =CC to select an anchor.")
    title = plain_text(story.get("generatedHeadline") or story.get("title"), 200)
    slug = story.get("slug")
    if not title or not isinstance(slug, str) or not slug.strip():
        raise ValueError("The cached story has no headline or Ground News article slug.")
    item = {
        "title": title,
        "country": country,
        "url": "https://ground.news/article/" + quote(slug, safe=""),
        "tag": "ground-news",
    }
    summary = plain_text(story.get("description") or story.get("dek") or story.get("summary"), 240)
    if summary:
        item["summary"] = summary
    if isinstance(story.get("start"), str) and story["start"]:
        item["time"] = story["start"]
    return item


def write_digest(path, items):
    doc = {"version": 1, "updated": datetime.now(timezone.utc).isoformat(), "items": items}
    content = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode()
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("Digest exceeds OSINT Map's 2 MiB limit.")
    temporary = tempfile.NamedTemporaryFile(dir=path.parent, delete=False)
    try:
        with temporary:
            temporary.write(content)
        os.replace(temporary.name, path)
    finally:
        Path(temporary.name).unlink(missing_ok=True)


def cached_story(key, cache_dir):
    args = [sys.executable, str(CLI), "cache", "show", key]
    if cache_dir:
        args.extend(["--cache-dir", str(cache_dir)])
    response = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    if response.returncode:
        try:
            message = json.loads(response.stderr)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = response.stderr.strip() or "Cache command failed."
        raise ValueError(message)
    data = json.loads(response.stdout)["data"]
    field = {"story": "summary", "lookup": "event"}.get(data["kind"])
    event = data["payload"].get(field) if field else None
    if not isinstance(event, dict) or not event.get("id"):
        raise ValueError("Select a cached story or a publisher lookup that matched a story.")
    return event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selections", metavar="CACHE_KEY[=CC]", nargs="+")
    parser.add_argument("--output", type=Path, required=True, help="destination JSON file")
    parser.add_argument("--cache-dir", type=Path, help="same directory used by the Ground News CLI")
    args = parser.parse_args()
    if len(args.selections) > 200:
        parser.error("OSINT Map supports up to 200 entries per operator feed.")
    items = {}
    try:
        for selection in args.selections:
            key, sep, country = selection.partition("=")
            if not key or (sep and not country):
                raise ValueError(f"Invalid selection {selection!r}. Use CACHE_KEY or CACHE_KEY=CC.")
            try:
                story = cached_story(key, args.cache_dir)
                item = map_item(story, country.upper())
            except ValueError as err:
                raise ValueError(f"{key}: {err}") from err
            prior = items.get(story["id"])
            if prior and prior["country"] != item["country"]:
                raise ValueError(f"Selected story {story['id']} has two different country anchors.")
            items[story["id"]] = item
        target = args.output.expanduser()
        write_digest(target, list(items.values()))
        print(f"Wrote {len(items)} selected stories to {target}.")
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as err:
        parser.exit(1, f"Export failed: {err}\n")


if __name__ == "__main__":
    main()
