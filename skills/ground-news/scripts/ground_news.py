#!/usr/bin/env python3
"""On-demand Ground News reading CLI for Codex and other local readers."""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlencode, urlsplit

from ground_news_client import coverage, Cache, Client, GroundError, cache_path, describe, story_card


KINDS = (
    "search-story", "search-interest", "lookup", "story", "interest",
    "feed", "place", "blindspots", "trending", "editions", "extension-popup", "extension-toolbar", "story-link",
    "paywalls",
)


def bounded_int(low, high):
    def parse(value):
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("expected an integer") from exc
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f"expected a value from {low} to {high}")
        return number
    return parse


ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,119}")


def identifier(value):
    if not ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("expected a Ground News ID")
    return value


def place_code(value):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_,.-]{0,159}", value):
        raise argparse.ArgumentTypeError("expected a Ground News place code such as US")
    return value.upper() if len(value) == 2 else value


def article_url(value):
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname
            and parsed.username is None
            and not any(char.isspace() or ord(char) < 32 for char in value)
        )
        if valid:
            return value.split("#", 1)[0]
    except (TypeError, ValueError, AttributeError):
        pass
    raise argparse.ArgumentTypeError("expected an HTTP(S) article URL without credentials")


def nonempty(value):
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("expected nonempty text")
    return value


def is_dict(payload, key):
    return isinstance(payload.get(key), dict)


def has_id(data):
    return isinstance(data, dict) and isinstance(data.get("id"), str) and bool(data["id"])


def is_list(payload, key):
    return isinstance(payload.get(key), list)


def is_id_list(payload, key):
    return is_list(payload, key) and all(isinstance(item, str) for item in payload[key])


def search(client, kind, query, limit):
    return client.read(
        f"search-{kind}", query, f"/public/search?limit={limit}",
        lambda data: is_list(data, "searchResults"),
        body={"type": "event" if kind == "story" else "interest", "searchText": query},
    )


def story_page_id(raw):
    # Ground's serialized article component names the cluster independently of its URL slug.
    ids = set(re.findall(rb'\\"articleId\\":\\"([A-Za-z0-9][A-Za-z0-9_-]{0,119})\\"', raw))
    if len(ids) != 1:
        raise GroundError("response", "Ground News did not identify the story in that link. Try its headline or story ID.")
    return {"id": ids.pop().decode("ascii")}


def ground_story_slug(url):
    parsed = urlsplit(url)
    match = re.fullmatch(r"/article/([^/]+)/?", parsed.path)
    slug = unquote(match[1]) if match else ""
    if parsed.hostname not in {"ground.news", "www.ground.news"} or not re.fullmatch(r"[\w-]{1,512}", slug):
        raise GroundError("input", "Use a Ground News story link from its /article/ page.")
    return slug


def story_paywalls(raw):
    page = story_page_id(raw)
    articles = {}
    decoder = json.JSONDecoder()
    html = raw.decode("utf-8", errors="replace")
    chunks = []
    for marker in re.finditer(r"self\.__next_f\.push\(", html):
        try:
            chunk, _ = decoder.raw_decode(html, marker.end())
        except ValueError:
            continue
        if isinstance(chunk, list) and len(chunk) > 1 and chunk[0] == 1 and isinstance(chunk[1], str):
            chunks.append(chunk[1])

    data = "".join(chunks)
    for marker in re.finditer(r'"articleSources"\s*:\s*(?=\[)', data):
        try:
            sources, _ = decoder.raw_decode(data, marker.end())
        except ValueError:
            continue
        for source in sources:
            if not isinstance(source, dict) or source.get("paywall") not in ("yes", "sometimes", "no"):
                continue
            url = source.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                continue
            info = source.get("sourceInfo")
            info = info if isinstance(info, dict) else {}
            articles.setdefault(url, {
                "url": url, "paywall": source["paywall"], "title": source.get("title"), "date": source.get("date"),
                "sourceInfo": {key: info.get(key) for key in ("name", "bias")},
            })
    return {**page, "sources": list(articles.values())[:60]}


def lookup(client, url):
    parsed = urlsplit(url)
    if parsed.hostname in {"ground.news", "www.ground.news"}:
        slug = ground_story_slug(url)
        page = client.read("story-link", slug, "/article/" + quote(slug, safe=""), has_id,
                           service="site", parse=story_page_id)
        summary = read_story(client, page["id"], None)
        return {"status": "event", "event": summary}
    return client.read(
        "lookup", url, "/search?" + urlencode({"url": url}),
        lambda data: isinstance(data.get("status"), str)
        and (data.get("event") is None or has_id(data["event"]))
        and (data["status"] != "event" or has_id(data.get("event"))),
        service="lookup",
    )


def extension_view(client, story_id, publisher_id):
    story_path = quote(story_id, safe="")
    if publisher_id:
        kind = "extension-toolbar"
        path = f"/toolbarData/{story_path}/{quote(publisher_id, safe='')}"
    else:
        kind = "extension-popup"
        path = f"/popupData/{story_path}"

    def matches(payload):
        story = payload.get("story")
        # Ground can resolve an older cluster ID to its current story.
        if not has_id(story) or not is_list(payload, "topSources"):
            return False
        source = payload.get("source")
        return not publisher_id or (has_id(source) and source["id"] == publisher_id)

    return client.read(kind, story_id, path, matches, service="extension")


def valid_story_summary(payload, requested_id):
    event = payload.get("summary")
    if not has_id(event) or not ID_PATTERN.fullmatch(event["id"]):
        return False
    if event["id"] == requested_id:
        return True
    # Ground resolves merged clusters on the original summary URL. A bare
    # foreign ID is insufficient evidence of a usable replacement record.
    return (
        isinstance(event.get("slug"), str) and bool(event["slug"].strip())
        and isinstance(event.get("title"), str) and bool(event["title"].strip())
        and isinstance(event.get("sources"), list)
    )


def read_story(client, story_id, source_limit):
    payload = client.read(
        "story", story_id, f"/public/event/{quote(story_id, safe='')}/summary",
        lambda data: valid_story_summary(data, story_id),
    )
    return {"requestedStoryId": story_id, **coverage(payload["summary"], source_limit)}


def read_story_details(client, ids, limit):
    details = []
    for story_id in ids[:limit]:
        try:
            details.append(read_story(client, story_id, 0))
        except GroundError as exc:
            details.append({"id": story_id, "error": exc.details})
    return details


def story(client, args):
    item = read_story(client, args.story_id, None if args.more_sources else args.sources_limit)
    if args.more_sources:
        url = first_publisher_url(item["sources"])
        if url:
            try:
                event = lookup(client, url).get("event")
                if not event or event["id"] not in {item["id"], item["requestedStoryId"]}:
                    raise GroundError("no_match", "The publisher URL did not resolve to the same Ground story.")
                item["expandedCoverage"] = coverage(event, args.sources_limit)
            except GroundError as exc:
                item["expansionError"] = exc.details
        else:
            item["expansionError"] = {"kind": "no_source", "message": "The summary has no publisher URL."}
    item["sources"] = item["sources"][:args.sources_limit]
    return item


def first_publisher_url(sources):
    for entry in sources:
        if isinstance(entry, dict) and isinstance(entry.get("url"), str):
            try:
                return article_url(entry["url"])
            except argparse.ArgumentTypeError:
                continue
    return None


def read_interest(client, interest_id):
    return client.read(
        "interest", interest_id, f"/public/interest/{quote(interest_id, safe='')}",
        lambda data: has_id(data.get("interest")) and data["interest"]["id"] == interest_id,
    )


def feed(client, args):
    place = None
    if args.place:
        place = client.read(
            "place", args.place, f"/public/place/{quote(args.place, safe='')}/interest",
            lambda data: has_id(data.get("interest")),
        )
        interest_id = place["interest"]["id"]
        interest = place["interest"]
    else:
        interest_id = args.interest_id
        interest = read_interest(client, interest_id)["interest"]

    events = client.read(
        "feed", interest.get("name") or interest_id,
        f"/public/interest/{quote(interest_id, safe='')}/events?limit={args.limit}",
        lambda data: is_id_list(data, "eventIds"),
    )
    return {
        "interestId": interest_id, "interest": interest, "events": events,
        "stories": read_story_details(client, events["eventIds"], args.details),
    }


def blindspots(client, details):
    data = client.read(
        "blindspots", "Blindspots", "/public/interest/blindspot/blindspots",
        lambda payload: all(is_id_list(payload, side) for side in ("left", "right")),
    )
    stories = {side: read_story_details(client, data[side], details) for side in ("left", "right")}
    return {**data, "stories": stories}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    policy = common.add_mutually_exclusive_group()
    policy.add_argument("--refresh", action="store_true", help="fetch again and keep the old entry if a refresh fails")
    policy.add_argument("--cache-only", action="store_true", help="allow cached reads only")
    common.add_argument("--timeout", type=bounded_int(1, 60), default=12, metavar="SECONDS")
    common.add_argument("--raw", action="store_true", help="include the upstream JSON keyed by cache key")
    common.add_argument("--cache-dir", type=Path, help="override the shared cache directory")
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("search", parents=[common], help="find Ground stories or feed interests")
    cmd.add_argument("kind", choices=("story", "interest"))
    cmd.add_argument("query", type=nonempty)
    cmd.add_argument("--limit", type=bounded_int(1, 20), default=5)

    cmd = sub.add_parser("lookup", parents=[common], help="open a Ground News or publisher article URL")
    cmd.add_argument("url", type=article_url)
    cmd.add_argument("--sources-limit", type=bounded_int(0, 500), default=8)

    cmd = sub.add_parser("paywalls", parents=[common], help="read public paywall labels for a Ground News story")
    cmd.add_argument("url", type=article_url)
    cmd.add_argument("story_id", type=identifier)

    cmd = sub.add_parser("story", parents=[common], help="read coverage and publisher links")
    cmd.add_argument("story_id", type=identifier)
    cmd.add_argument("--sources-limit", type=bounded_int(0, 500), default=8)
    cmd.add_argument("--more-sources", action="store_true", help="look up a listed URL for expanded coverage")

    cmd = sub.add_parser("extension", parents=[common], help="read compact coverage and top sources from Ground's extension")
    cmd.add_argument("story_id", type=identifier)
    cmd.add_argument("--publisher-id", type=identifier, help="include the toolbar view for a publisher source ID")

    cmd = sub.add_parser("feed", parents=[common], help="read an outlet, topic, or place interest")
    target = cmd.add_mutually_exclusive_group(required=True)
    target.add_argument("interest_id", nargs="?", type=identifier)
    target.add_argument("--place", type=place_code, help="resolve a Ground place code, for example US")
    cmd.add_argument("--limit", type=bounded_int(1, 20), default=5)
    cmd.add_argument("--details", type=bounded_int(0, 5), default=2, metavar="N",
                     help="add summaries for the first N IDs (default 2)")

    cmd = sub.add_parser("blindspots", parents=[common], help="read Ground's left and right blindspot lists")
    cmd.add_argument("--details", type=bounded_int(0, 3), default=1, metavar="N",
                     help="add summaries for the first N IDs per side (default 1)")

    cmd = sub.add_parser("trending", parents=[common], help="read trending interests for an interest ID")
    cmd.add_argument("interest_id", type=identifier)
    sub.add_parser("editions", parents=[common], help="list Ground's top-feed editions")

    cmd = sub.add_parser("cache", help="browse saved requests offline")
    cache = cmd.add_subparsers(dest="action", required=True)
    browse = argparse.ArgumentParser(add_help=False)
    browse.add_argument("--kind", choices=KINDS)
    browse.add_argument("--limit", type=bounded_int(1, 200), default=25)
    browse.add_argument("--cache-dir", type=Path)
    cache.add_parser("list", parents=[browse], help="list recent responses")
    cmd = cache.add_parser("search", parents=[browse], help="find stored subjects, IDs, and links")
    cmd.add_argument("query", type=nonempty)
    cmd = cache.add_parser("show", help="show the full saved upstream JSON for a key")
    cmd.add_argument("key")
    cmd.add_argument("--cache-dir", type=Path)
    return parser


def run_read(client, args):
    if args.command == "search":
        return search(client, args.kind, args.query, args.limit)
    if args.command == "lookup":
        data = lookup(client, args.url)
        event = data.get("event")
        return {**data, "event": coverage(event, args.sources_limit) if event else None}
    if args.command == "paywalls":
        slug = ground_story_slug(args.url)
        page = client.read("paywalls", slug, "/article/" + quote(slug, safe=""), has_id,
                           service="site", parse=story_paywalls)
        if page["id"] != args.story_id:
            raise GroundError("no_match", "The Ground News page resolved to a different story.")
        return page
    if args.command == "story":
        return story(client, args)
    if args.command == "extension":
        return extension_view(client, args.story_id, args.publisher_id)
    if args.command == "feed":
        return feed(client, args)
    if args.command == "blindspots":
        return blindspots(client, args.details)
    if args.command == "trending":
        return client.read(
            "trending", args.interest_id, f"/public/interest/{quote(args.interest_id, safe='')}/trending",
            lambda data: is_list(data, "interests"),
        )
    return client.read(
        "editions", "Top-feed editions", "/v04/customFeed/topFeedEditions",
        lambda data: is_list(data, "editions"),
    )


def run_cache(cache, args):
    if args.action == "show":
        row = cache.get(args.key)
        if row is None:
            raise GroundError("cache_miss", "Unknown cache key.", cache_key=args.key)
        payload = json.loads(row["payload"])
        entry = describe(row)
        if row["kind"] in {"story", "lookup"}:
            entry.update(story_card(row["kind"], payload))
        return {**entry, "payload": payload}
    query = args.query.casefold().split() if args.action == "search" else []
    return {"entries": cache.browse(query, args.kind, args.limit)}


def output(value, stream=sys.stdout):
    json.dump(value, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    stream.write("\n")


def main(argv=None):
    args = build_parser().parse_args(argv)
    command = f"cache {args.action}" if args.command == "cache" else args.command
    envelope = {"schema_version": 1, "command": command, "reads": []}
    try:
        cache = Cache((args.cache_dir or cache_path()).expanduser())
        if args.command == "cache":
            envelope["data"] = run_cache(cache, args)
        else:
            client = Client(cache, args.timeout, refresh=args.refresh, cache_only=args.cache_only)
            envelope["reads"] = client.reads
            envelope["data"] = run_read(client, args)
            if args.raw:
                envelope["upstream"] = client.responses
    except GroundError as exc:
        output({**envelope, "error": exc.details}, sys.stderr)
        return 1
    except (OSError, sqlite3.Error) as exc:
        output({**envelope, "error": {"kind": "local_io", "message": str(exc)}}, sys.stderr)
        return 1
    output(envelope)
    return 0


if __name__ == "__main__":
    sys.exit(main())
