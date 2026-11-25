"""Public Ground News reads and a shared, process-safe response cache."""

import hashlib
import json
import os
import socket
import sqlite3
import time
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


API_BASE = "https://web-api-cdn.ground.news/api"
LOOKUP_BASE = "https://extension.ground.news"
EXTENSION_BASE = "https://production.checkitt.news/api/public/extension"
MIN_INTERVAL = 0.6
MAX_RETRY_WAIT = 4
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
TRANSIENT_HTTP = {429, 502, 503, 504}


class GroundError(Exception):
    def __init__(self, kind, message, **details):
        super().__init__(message)
        self.details = {"kind": kind, "message": message, **details}


def cache_path():
    explicit = os.environ.get("GROUND_NEWS_CACHE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME")
    return (Path(xdg).expanduser() if xdg else Path.home() / ".cache") / "ground-news"


def timestamp(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def search_text(value):
    """Index the strings used to recognize subjects and sources."""
    if isinstance(value, list):
        for item in value:
            yield from search_text(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                yield from search_text(item)
            elif isinstance(item, str) and (
                key.lower().endswith("id")
                or key in {
                    "title", "name", "slug", "description", "generatedHeadline",
                    "placeString", "url", "left", "right",
                }
            ):
                yield item
    elif isinstance(value, str):
        yield value


SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    key TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL,
    fetched REAL NOT NULL, searchable TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pacing (
    id INTEGER PRIMARY KEY CHECK (id = 1), next_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS story_cards (
    key TEXT PRIMARY KEY, fetched REAL NOT NULL, metadata TEXT NOT NULL
);
"""


def story_card(kind, data):
    event = data.get("summary" if kind == "story" else "event")
    if not isinstance(event, dict) or not event.get("id"):
        return {}
    card = {"story_id": event["id"]}
    title = event.get("generatedHeadline") or event.get("title")
    if isinstance(title, str) and title.strip():
        card["title"] = title
    return card


class Cache:
    def __init__(self, directory):
        self.directory = directory
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = directory / "responses.sqlite3"
        os.close(os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600))
        with closing(self.connect()) as db:
            db.executescript(SCHEMA)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def get(self, key):
        with closing(self.connect()) as db:
            return db.execute("SELECT * FROM responses WHERE key = ?", (key,)).fetchone()

    def put(self, key, kind, label, data):
        indexed = " ".join([key, kind, label, *search_text(data)]).casefold()
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False)
        fetched = time.time()
        with closing(self.connect()) as db, db:
            db.execute(
                "INSERT OR REPLACE INTO responses VALUES (?, ?, ?, ?, ?, ?)",
                (key, kind, label, fetched, indexed, payload),
            )
            if kind in {"story", "lookup"}:
                db.execute(
                    "INSERT OR REPLACE INTO story_cards VALUES (?, ?, ?)",
                    (key, fetched, json.dumps(story_card(kind, data), ensure_ascii=False)),
                )
        return fetched

    def browse(self, query, kind, limit):
        clauses = ["instr(searchable, ?) > 0" for _ in query]
        params = list(query)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        where = " AND ".join(clauses) if clauses else "1"
        with closing(self.connect()) as db:
            # Only selected legacy records need a payload read. New cards are small
            # and the timestamp also handles another client refreshing an old row.
            rows = db.execute(
                f"SELECT r.key, r.kind, r.label, r.fetched, c.metadata FROM responses r "
                f"LEFT JOIN story_cards c ON c.key = r.key AND c.fetched = r.fetched "
                f"WHERE {where} ORDER BY r.fetched DESC, r.key LIMIT ?", (*params, limit)
            )
            entries = []
            for row in rows:
                entry = describe(row)
                if row["metadata"] is not None:
                    entry.update(json.loads(row["metadata"]))
                elif row["kind"] in {"story", "lookup"}:
                    saved = db.execute("SELECT payload FROM responses WHERE key = ?", (row["key"],)).fetchone()
                    entry.update(story_card(row["kind"], json.loads(saved["payload"])))
                entries.append(entry)
            return entries

    def next_request(self):
        with closing(self.connect()) as db:
            row = db.execute("SELECT next_at FROM pacing WHERE id = 1").fetchone()
        return row["next_at"] if row else 0

    def defer_until(self, deadline):
        with closing(self.connect()) as db, db:
            db.execute(
                "INSERT INTO pacing VALUES (1, ?) ON CONFLICT(id) DO UPDATE "
                "SET next_at = max(pacing.next_at, excluded.next_at)",
                (deadline,),
            )

    @contextmanager
    def network_slot(self, timeout):
        # A separate SQLite write lock also works on Windows and leaves cached
        # response reads available while another process waits on the network.
        with closing(sqlite3.connect(self.directory / "network.lock", timeout=timeout)) as gate:
            try:
                gate.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                    raise GroundError("busy", "Another process is using the Ground News network slot.") from exc
                raise
            yield


def describe(row):
    return {
        "key": row["key"], "kind": row["kind"], "label": row["label"],
        "fetched_at": timestamp(row["fetched"]),
    }


def retry_after(value):
    if not value:
        return None
    if value.isascii() and value.isdigit():
        return float(value[:15])
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return max(0, date.timestamp() - time.time())
    except (TypeError, ValueError, OverflowError):
        return None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, cache, timeout, refresh=False, cache_only=False):
        self.cache = cache
        self.timeout = timeout
        self.refresh = refresh
        self.cache_only = cache_only
        self.started = time.time()
        self.reads = []
        self.responses = {}
        self.opener = build_opener(NoRedirect())

    def read(self, kind, label, path, check, *, body=None, service="web"):
        bases = {"web": API_BASE, "lookup": LOOKUP_BASE, "extension": EXTENSION_BASE}
        url = bases[service] + path
        request_body = json.dumps(body, sort_keys=True).encode() if body is not None else None
        digest = hashlib.sha256(url.encode() + b"\x00" + (request_body or b"")).hexdigest()
        key = f"{kind}:{digest[:24]}"
        if key in self.responses:
            return self.responses[key]
        row = self.cache.get(key)
        if row and (not self.refresh or row["fetched"] >= self.started):
            return self.cached(row, url)
        if self.cache_only:
            raise GroundError("cache_miss", f"No cached response for {label}.", cache_key=key)

        try:
            with self.cache.network_slot(self.timeout):
                row = self.cache.get(key)
                if row and (not self.refresh or row["fetched"] >= self.started):
                    return self.cached(row, url)
                payload = self.fetch(url, request_body)
                if not isinstance(payload, dict) or not check(payload):
                    raise GroundError("response", f"Unexpected Ground News response for {label}.")
                fetched = self.cache.put(key, kind, label, payload)
        except GroundError as exc:
            exc.details["cache_key"] = key
            if row:
                exc.details["cached_at"] = timestamp(row["fetched"])
            raise
        return self.record(key, kind, label, fetched, "network", url, payload)

    def cached(self, row, url):
        return self.record(
            row["key"], row["kind"], row["label"], row["fetched"],
            "cache", url, json.loads(row["payload"]),
        )

    def record(self, key, kind, label, fetched, origin, url, payload):
        self.reads.append({
            "key": key, "kind": kind, "label": label, "fetched_at": timestamp(fetched),
            "origin": origin, "endpoint": url.split("?", 1)[0],
        })
        self.responses[key] = payload
        return payload

    def fetch(self, url, body):
        headers = {"Accept": "application/json", "User-Agent": "ground-news-reading-skill/1"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers)
        for attempt in range(2):
            wait = self.cache.next_request() - time.time()
            if wait > MAX_RETRY_WAIT + 0.1:
                raise GroundError(
                    "cooldown", "Ground News requested a cooldown.",
                    retry_after_seconds=round(wait, 2),
                )
            if wait > 0:
                time.sleep(wait)
            self.cache.defer_until(time.time() + MIN_INTERVAL)
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
            except HTTPError as exc:
                seconds = retry_after(exc.headers.get("Retry-After")) if exc.headers else None
                exc.close()
                if exc.code in TRANSIENT_HTTP:
                    seconds = max(MIN_INTERVAL, seconds) if seconds is not None else 1
                    self.cache.defer_until(time.time() + seconds)
                    if attempt == 0 and seconds <= MAX_RETRY_WAIT:
                        continue
                details = {"status": exc.code}
                if seconds is not None:
                    details["retry_after_seconds"] = seconds
                raise GroundError("http", f"Ground News returned HTTP {exc.code}.", **details) from exc
            except (URLError, OSError, HTTPException) as exc:
                reason = getattr(exc, "reason", exc)
                kind = "timeout" if isinstance(reason, (socket.timeout, TimeoutError)) else "network"
                raise GroundError(kind, f"Ground News request failed: {reason}") from exc
            if len(raw) > MAX_RESPONSE_BYTES:
                raise GroundError("response", "Ground News response exceeded the size limit.")
            try:
                return json.loads(raw, parse_constant=reject_constant)
            except (ValueError, RecursionError) as exc:
                raise GroundError("response", "Ground News returned invalid JSON.") from exc


def reject_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")
