# Grounded Hermes

A personal Ground News reader for Codex and Hermes. Follow a story across publishers, compare coverage, and return to earlier research from the local cache.

## Try a search

Clone the private repository with your GitHub account, then run the standard-library CLI:

```sh
gh repo clone cygnostik/grounded-hermes
cd grounded-hermes
python3 skills/ground-news/scripts/ground_news.py search story "lunar exploration" --limit 3
```

Use an ID from `data.searchResults` with `story ID`. Later, `cache search "lunar"` finds the saved research locally. Each response includes its fetch time and whether it came from cache or the network. Use `--refresh` when you need a new snapshot. [CLI commands and examples](skills/ground-news/references/cli.md)

## Codex Desktop and TUI

Open this checkout as your project and start a chat. The project exposes the [Ground News skill](skills/ground-news/SKILL.md) through `.agents/skills/ground-news`. Try:

> Use $ground-news to find a recent story about lunar exploration. Compare which outlets covered it, show the rated-source denominator, and give me the original links.

To use the same checkout from other projects on macOS or Linux, link its skill into your personal skills directory. Run this from the repository root:

```sh
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/ground-news" "$HOME/.agents/skills/ground-news"
```

The link picks up future pulls. Open a new Codex chat to discover the skill. The scripts also work directly from a terminal.

## Hermes Desktop and Agent

Install the repository as a unified Hermes plugin. The reader and agent share the same local cache with the CLI when they run under the same user and cache directory. Select **Grounded News** in the Desktop sidebar to search, explore a story's coverage, inspect original publisher links, or preload the story in a fresh chat. The right pane keeps recently cached stories within reach during conversations. [Hermes setup and testing](docs/hermes.md)

For a map of selected stories, the [OSINT Map integration](integrations/osint-map/README.md) exports a local digest for the Operator feeds layer.

## Run the tests

With Python, Node.js, Make, and uv available, run the fixture suites from a clean checkout:

```sh
uv run --no-project --with fastapi --with httpx make test
```

Alternatively, run `make test PYTHON=/path/to/python` with an interpreter that already has FastAPI and httpx. The CLI itself uses only Python's standard library. The optional OSINT Map parser compatibility test runs when `OSINT_MAP_CHECKOUT` points to that plugin.

## Data access

The client reads the same public JSON used by Ground's web app and browser extension. News metadata and publisher links can change as coverage develops. Ground assigns political bias at the outlet level, and its percentage split uses the subset of sources with ratings. A missing rating means unknown.

This project uses undocumented endpoints. Ground's [site terms](https://about.ground.news/terms-and-conditions) address automated access in §6.1(d). The [subscriber inventory](skills/ground-news/references/subscriber-inventory.md) records the routes present in Ground's published clients and the checks that require a subscriber session.
