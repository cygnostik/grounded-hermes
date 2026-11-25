# Ground News CLI

## Install for Codex desktop and TUI

The CLI uses Python 3.9+ and its standard library. The repository exposes this skill to Codex through a project-local symlink. Open the repository in Codex and start a new chat, or invoke the script directly:

```sh
python3 -B skills/ground-news/scripts/ground_news.py --help
```

To use it in a different project, place the entire skill directory under that project's `.agents/skills/`, or under `~/.agents/skills/` for user-wide discovery. Invoke `$ground-news` in a new chat. [Codex skills](https://developers.openai.com/codex/skills/)

## Commands

In the examples below, `CLI` stands for `python3 -B /path/to/ground-news/scripts/ground_news.py`. Put command options after the subcommand.

| Command | Public read or local action |
| --- | --- |
| `CLI search story "NASA" --limit 2` | POST `/public/search?limit=2` with `type: event` and `searchText`. Select the matching story ID. |
| `CLI search interest "Reuters" --limit 2` | Same search with `type: interest`. Examine `subType` and use the matching current interest ID. |
| `CLI lookup "https://publisher.example/article"` | GET `https://extension.ground.news/search?url=ENCODED`. The result includes Ground's `status`, matching event if available, and any returned source and reference ID. The URL query string is preserved and any fragment is dropped. |
| `CLI lookup "https://ground.news/article/story-slug"` | Reads the cluster ID from the public story page and uses it to load coverage. Both reads are cached. |
| `CLI paywalls "https://ground.news/article/story-slug" STORY_ID` | Reads public publisher labels, including paywall status, factuality, named owners, and wire identifiers when Ground supplies them. Paywall values are `yes`, `sometimes`, or `no`. The story ID must match the page. |
| `CLI story STORY_ID --more-sources --sources-limit 12` | GET `/public/event/{id}/summary`. Optional expansion looks up a listed article URL and checks that the returned story ID matches. |
| `CLI extension STORY_ID` | Ground's browser-extension popup. Returns the compact story coverage counts and the supplied top sources. |
| `CLI extension STORY_ID --publisher-id PUBLISHER_ID` | The extension toolbar adds the selected publisher's name, domain and bias label. Use `data.source.id` from a publisher URL lookup, or a matching story source's `sourceInfo.id`. Outlet interest IDs belong to the feed command. |
| `CLI feed INTEREST_ID --limit 5 --details 2` | GET `/public/interest/{id}` and `/public/interest/{id}/events?limit=5`. Optionally resolve the first N story IDs to summaries. |
| `CLI feed --place US --limit 2 --details 0` | GET `/public/place/US/interest` and then read its event IDs. Use interest search for a named location. |
| `CLI blindspots --details 1` | GET `/public/interest/blindspot/blindspots`. Returns Ground's left and right story ID arrays with optional summaries per side. |
| `CLI trending INTEREST_ID` | GET `/public/interest/{id}/trending`. Returns trending interests. |
| `CLI editions` | GET `/v04/customFeed/topFeedEditions`. Returns edition metadata including `webFeedId` when present. |
| `CLI cache list --kind story` | List recent saved responses of one kind. |
| `CLI cache search "NASA Artemis"` | Find saved responses containing all words across labels, story or interest names, IDs, descriptions, or original links. |
| `CLI cache show KEY` | Return one complete saved response by the key from a read, list, or search. |

Public API paths in the table use `https://web-api-cdn.ground.news/api`. They come from Ground's clients and may change. The CLI bounds search and feed lists at 20, feed detail lookups at five, and blindspot detail lookups at three per side.

The extension command makes one GET to `https://production.checkitt.news/api/public/extension`, using `/popupData/{storyId}` or `/toolbarData/{storyId}/{publisherSourceId}`. Its output preserves `data.story`, `data.topSources`, and, for the toolbar, `data.source`. Ground can resolve an older cluster ID to a newer one. The read label records the requested story ID and `data.story.id` identifies the returned cluster. The story's `left`, `center`, and `right` fields are percentages. Popup and toolbar records can be listed locally with `cache list --kind extension-popup` and `cache list --kind extension-toolbar`. [Ground News browser extension](https://help.ground.news/en/articles/1750529)

## JSON contract

Successful commands emit one object on stdout with `schema_version: 1`, `command`, `data`, and `reads`. Each read has a `key`, `kind`, `label`, UTC `fetched_at`, `origin` of `network` or `cache`, and an `endpoint` without its query string. Add `--raw` to a network-capable command to include every upstream JSON payload in `upstream`, keyed by the corresponding read's key. `cache show` returns the full upstream JSON as `data.payload`.

- `search` preserves `data.searchResults`. An empty result list is a successful search. Results can include older stories near the top. Check the story’s `start` date before describing a result as recent.
- A story read preserves the supplied ID as `requestedStoryId` and Ground's returned ID as `id`. They can differ after Ground merges clusters. Expanded publisher coverage must resolve to one of these two IDs. Each saved response keeps its own timestamp and returned ID.
- `story` and `lookup` project story fields including Ground's counts and classifications, generated and original story headlines, the upstream `summary` when supplied, topic and place data, and source entries with their original publisher URLs. `sources` defaults to the first eight entries and `sourceEntriesAvailable` counts the entries supplied upstream before display limiting. The reported `sourceCount` and `biasSourceCount` are separate from the length of this list. Where present, bias percentages describe the rated subset. Use the figures and timestamp from the same read.
- Expanded coverage appears under `data.expandedCoverage` and has its own counts. These can differ from the summary due to separate upstream snapshots. A failed expansion returns the base summary with `data.expansionError`. Ground's normal URL miss, such as `status: "not_news"`, is a successful answer with `event: null`.
- `feed` returns `interestId`, `interest`, the upstream `events` object, and optional `stories`. `blindspots` preserves the left and right ID lists and adds `stories.left` and `stories.right`. If a requested detail read fails, its summary slot contains `id` and `error`.
- Primary read, cache miss, and I/O failures emit one object on stderr with `schema_version`, `command`, `reads`, and `error.kind` and `error.message`. The exit code is 1. HTTP errors include `error.status` and a retry delay when available. Argument errors use the CLI's standard usage output and exit code 2.

## Cache and network behavior

The per-user SQLite cache lives under `$XDG_CACHE_HOME/ground-news`, defaulting to `~/.cache/ground-news`. Use `GROUND_NEWS_CACHE_DIR` or a command's `--cache-dir` to point multiple clients at the same directory. Cache keys incorporate the exact request URL and search body. Requests with different limits or typed search queries can create separate entries. `cache list|search|show` use no network. A normal read reuses the saved response indefinitely, including after a process restart. `--refresh` fetches a new response and reports a failure if the refresh fails. The old entry remains readable. `--cache-only` uses existing entries and reports misses. A URL lookup shares the same cached response with `story --more-sources` when the lookup URL is identical.

Cache list, search and show expose `story_id` and an available `title` for story records and matching publisher lookups. The existing `label` retains the requested story ID or publisher URL.

The cache stores response data and lookup URLs locally. Send public publisher article URLs to lookup, since Ground's extension endpoint receives the supplied URL. Use a cache directory accessible only to readers who should see those queries and results.

An exclusive lock per cache directory limits concurrent requests to one. Requests start at least 0.6 seconds apart. The default socket and lock wait timeouts are 12 seconds and can be adjusted with `--timeout`. HTTP 429, 502, 503, and 504 may get one retry. A `Retry-After` delay up to four seconds can be waited out in the call. Longer cooldowns persist across invocations using the same cache, and fresh reads return the remaining wait without making a request. The CLI has no scheduled refresh, background collection, or bulk ingestion path.

Ground News Terms of Service section 6.1(d) prohibits using robots, spiders, or other automatic means to access the Site, including monitoring or copying. The documented paths are client endpoints and this skill has no published Ground News API permission. [Ground News Terms of Service](https://about.ground.news/terms-and-conditions)

For signed-in features and the remaining checks, see the [subscriber custom-feed inventory](subscriber-inventory.md).
