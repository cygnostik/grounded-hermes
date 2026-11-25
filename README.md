# Grounded Hermes

![A wall of old TVs shows one gathering under two headlines, “Chaos” and “Rally,” beside a grinning news anchor.](docs/images/the-evening-spin.jpg)

One channel calls it chaos. Flip over and it’s a rally. Give this independent Ground News reader a headline or article link to see who picked it up, compare outlet ratings, and read the original reporting.

## Try it

**Hermes.** Install with a GitHub account that can read this repo. Enable **Grounded News** in Desktop, open it from the sidebar, and paste a link or ID into **Open story**. **Discuss in new chat** brings the coverage into a draft. [Hermes setup](docs/hermes.md) · [Reader screenshot](docs/images/coverage-reader.png) · [Chat pane](docs/images/chat-pane.png)

```sh
hermes plugins install https://github.com/cygnostik/grounded-hermes.git
```

**Codex.** Open the checkout in Codex and ask `$ground-news Who else covered this story?` with an article link. Or run the CLI directly. [CLI commands and setup](skills/ground-news/references/cli.md)

```sh
gh repo clone cygnostik/grounded-hermes
cd grounded-hermes
python3 skills/ground-news/scripts/ground_news.py search story "lunar exploration" --limit 3
```

## How it works

Hermes runs the bundled Python CLI. On a cache miss or refresh, it sends the search, ID, or publisher URL to Ground’s public, undocumented endpoints. Results stay in a shared SQLite cache on the machine running the request. Bias percentages count only outlets Ground has rated.

Public reads work without a Ground account. Signed-in subscriber features are unverified. [Subscriber inventory](skills/ground-news/references/subscriber-inventory.md) · [Ground’s automation terms, §6.1(d)](https://about.ground.news/terms-and-conditions) · [OSINT Map export](integrations/osint-map/README.md) · [Tests](docs/hermes.md#verify-a-checkout)
