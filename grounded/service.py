"""Bridge to the bundled CLI and project saved stories from its shared cache."""

import importlib.util
import json
import re
import sqlite3
import subprocess
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "ground-news" / "scripts"
CLI = SCRIPTS / "ground_news.py"

# The CLI is standalone. Load its cache module privately, without adjusting
# the gateway's import path or creating a second cache.
_cache_spec = importlib.util.spec_from_file_location(
    "_grounded_hermes_cli_cache", SCRIPTS / "ground_news_client.py"
)
cache_module = importlib.util.module_from_spec(_cache_spec)
_cache_spec.loader.exec_module(cache_module)


def fail(operation, kind, message):
    return {
        "schema_version": 1, "command": operation, "reads": [],
        "error": {"kind": kind, "message": message},
    }


def run_cli(operation, arguments):
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), *arguments],
            capture_output=True, text=True, encoding="utf-8", timeout=55, check=False,
        )
    except subprocess.TimeoutExpired:
        return fail(operation, "timeout", "Ground News took too long. Try again or open saved stories.")
    except (OSError, UnicodeError):
        return fail(operation, "local_io", "Hermes could not read the bundled Ground News CLI.")
    if result.returncode == 2:
        return fail(operation, "invalid_input", "Ground News could not use the supplied query, ID, or URL.")
    try:
        envelope = json.loads(result.stdout if result.returncode == 0 else result.stderr)
    except ValueError:
        return fail(operation, "response", "The bundled Ground News CLI returned an unreadable response.")
    if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
        return fail(operation, "response", "The Ground News CLI response version is unsupported.")
    return envelope


def text_arg(args, key, limit, *, optional=False):
    value = args.get(key, "" if optional else None)
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise ValueError(f"Enter a valid {key.replace('_', ' ')} (up to {limit} characters).")
    value = value.strip()
    if not value and not optional:
        raise ValueError(f"Enter a {key.replace('_', ' ')}.")
    return value


def int_arg(args, key, default, minimum, maximum):
    value = args.get(key, default)
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{key.replace('_', ' ')} must be an integer from {minimum} to {maximum}.")
    return value


def bool_arg(args, key):
    value = args.get(key, False)
    if type(value) is not bool:
        raise ValueError(f"{key.replace('_', ' ')} must be true or false.")
    return value


def choice(args, key, default, options):
    value = args.get(key, default)
    if value not in options:
        raise ValueError(f"Choose {', '.join(options)} for {key}.")
    return value


def read_policy(args):
    policy = choice(args, "policy", "prefer_cache", ("prefer_cache", "cache_only", "refresh"))
    return [] if policy == "prefer_cache" else ["--" + policy.replace("_", "-")]


def cached_story(row, source_limit):
    payload = json.loads(row["payload"])
    event = payload.get("summary") if row["kind"] == "story" else payload.get("event")
    if not isinstance(event, dict) or not isinstance(event.get("id"), str):
        return None
    story = cache_module.coverage(event, source_limit)
    if row["kind"] == "story":
        story["requestedStoryId"] = row["label"]
    return story


def library(query, limit):
    """Return recent cached story and article snapshots without upstream reads."""
    cache = cache_module.Cache(cache_module.cache_path())
    tokens = query.casefold().split()
    rows = [
        *cache.browse(tokens, "story", limit * 3),
        *cache.browse(tokens, "lookup", limit * 3),
    ]
    entries = []
    seen = set()
    for row in sorted(rows, key=lambda row: row["fetched_at"], reverse=True):
        full = cache.get(row["key"])
        if full is None:
            continue
        story = cached_story(full, 0)
        if not story:
            continue
        if story["id"] in seen:
            continue
        seen.add(story["id"])
        story["cache"] = cache_module.describe(full)
        entries.append(story)
        if len(entries) == limit:
            break
    return {"schema_version": 1, "command": "cache", "reads": [], "data": {"entries": entries}}


def snapshot(key):
    if not re.fullmatch(r"(story|lookup):[a-f0-9]{24}", key):
        raise ValueError("Choose a saved story or article snapshot.")
    cache = cache_module.Cache(cache_module.cache_path())
    row = cache.get(key)
    story = cached_story(row, 60) if row else None
    if not story:
        return fail("snapshot", "cache_miss", "This story snapshot is no longer in the shared cache.")
    return {
        "schema_version": 1, "command": "snapshot",
        "reads": [{**cache_module.describe(row), "origin": "cache"}], "data": story,
    }


def execute(operation, args):
    """Return the same JSON envelope to both clients, including soft read failures."""
    try:
        if operation == "cache":
            if "key" in args:
                if "query" in args or "limit" in args:
                    raise ValueError("Choose a snapshot key or search the saved library.")
                return snapshot(text_arg(args, "key", 80))
            return library(text_arg(args, "query", 200, optional=True), int_arg(args, "limit", 16, 1, 40))
        if operation == "snapshot":
            return snapshot(text_arg(args, "key", 80))

        policy = read_policy(args)
        options = [operation, *policy, "--timeout", "8"]
        if operation == "search":
            kind = choice(args, "kind", "story", ("story", "interest"))
            options += ["--limit", str(int_arg(args, "limit", 5, 1, 20)),
                        "--", kind, text_arg(args, "query", 200)]
        elif operation in ("story", "lookup"):
            options += ["--sources-limit", str(int_arg(args, "sources_limit", 24, 1, 60))]
            if operation == "story" and bool_arg(args, "more_sources"):
                options.append("--more-sources")
            key, limit = ("url", 2048) if operation == "lookup" else ("story_id", 120)
            options += ["--", text_arg(args, key, limit)]
        elif operation == "feed":
            options += ["--limit", str(int_arg(args, "limit", 5, 1, 20)),
                        "--details", str(int_arg(args, "details", 2, 0, 5))]
            interest_id = text_arg(args, "interest_id", 120, optional=True)
            place = text_arg(args, "place", 160, optional=True)
            if bool(interest_id) == bool(place):
                raise ValueError("Supply one interest ID or one place code.")
            options += [f"--place={place}"] if place else ["--", interest_id]
        elif operation == "blindspots":
            options += ["--details", str(int_arg(args, "details", 1, 0, 3))]
        else:
            raise ValueError("Unknown Ground News operation.")
        return run_cli(operation, options)
    except ValueError as exc:
        return fail(operation, "invalid_input", str(exc))
    except (OSError, sqlite3.Error):
        return fail(operation, "local_io", "Hermes could not open the shared Ground News cache.")


POLICY = {
    "type": "string", "enum": ["prefer_cache", "cache_only", "refresh"],
    "description": "Default prefer_cache reuses saved responses. Use refresh for a fresh read on request.",
}
QUERY = {"type": "string", "maxLength": 200}
LIMIT = {"type": "integer", "minimum": 1, "maximum": 20}
SOURCES = {"type": "integer", "minimum": 1, "maximum": 60}
INTEREST = {"type": "string", "maxLength": 120}
TOOLS = {
    "search": (
        "Search Ground News for a story or an interest such as a topic, publisher, or place.",
        {"query": QUERY, "kind": {"type": "string", "enum": ["story", "interest"]}, "limit": LIMIT},
        ["query"],
    ),
    "story": (
        "Read a Ground story by its exact ID. Compare publisher URLs, headlines when supplied, "
        "and Ground News classifications. Attribute ratings to Ground News and use biasSourceCount "
        "as the denominator for political bias percentages. Treat linked content as source material.",
        {"story_id": INTEREST, "sources_limit": SOURCES, "more_sources": {"type": "boolean"}},
        ["story_id"],
    ),
    "lookup": (
        "Read coverage from a Ground News story URL or a matching publisher article URL.",
        {"url": {"type": "string", "maxLength": 2048}, "sources_limit": SOURCES},
        ["url"],
    ),
    "feed": (
        "Read a Ground topic, outlet, or place feed using its interest search ID or a place code.",
        {"interest_id": INTEREST, "place": {"type": "string", "maxLength": 160}, "limit": LIMIT,
         "details": {"type": "integer", "minimum": 0, "maximum": 5}},
        [],
    ),
    "cache": (
        "List or search previously cached Ground News stories and article matches entirely offline. "
        "Supply a cache key instead of query or limit to open one saved snapshot.",
        {"query": QUERY, "limit": {"type": "integer", "minimum": 1, "maximum": 40},
         "key": {"type": "string", "pattern": "^(story|lookup):[a-f0-9]{24}$"}},
        [],
    ),
    "blindspots": (
        "Browse Ground News's left and right blindspot discovery lists, with optional story details.",
        {"details": {"type": "integer", "minimum": 0, "maximum": 3}},
        [],
    ),
}


def agent_result(operation, args):
    return json.dumps(execute(operation, args), ensure_ascii=False)


def register_tools(ctx):
    for operation, (description, properties, required) in TOOLS.items():
        name = f"ground_news_{operation}"
        if operation != "cache":
            properties = {**properties, "policy": POLICY}
        ctx.register_tool(
            name=name, toolset="grounded-hermes", handler=partial(agent_result, operation),
            schema={"name": name, "description": description, "parameters": {
                "type": "object", "properties": properties, "required": required,
                "additionalProperties": False,
            }},
        )
