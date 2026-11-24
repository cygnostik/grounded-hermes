# Grounded Hermes

A personal Ground News reader for Codex and Hermes. Follow a story across publishers, compare coverage, and return to earlier research from the local cache.

## Codex Desktop and TUI

Open this checkout as your project and start a chat. The project exposes the [Ground News skill](skills/ground-news/SKILL.md) through `.agents/skills/ground-news`. Try:

> Use $ground-news to find a recent story about lunar exploration. Compare which outlets covered it, show the rated-source denominator, and give me the original links.

To use the same checkout from other projects on macOS or Linux, link its skill into your personal skills directory. Run this from the repository root:

```sh
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/ground-news" "$HOME/.agents/skills/ground-news"
```

The link picks up future pulls. Open a new Codex chat to discover the skill. The scripts also work directly from a terminal.

## Data access

The client reads the same public JSON used by Ground's web app and browser extension. News metadata and publisher links can change as coverage develops. Ground assigns political bias at the outlet level, and its percentage split uses the subset of sources with ratings. A missing rating means unknown.

This project uses undocumented endpoints. Ground's [site terms](https://about.ground.news/terms-and-conditions) address automated access in §6.1(d). The [subscriber inventory](skills/ground-news/references/subscriber-inventory.md) records the routes present in Ground's published clients and the checks that require a subscriber session.
