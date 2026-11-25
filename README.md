# Grounded Hermes

![A wall of old TVs shows one gathering under two headlines, “Chaos” and “Rally,” beside a grinning news anchor.](docs/images/the-evening-spin.jpg)

One channel calls it chaos. Flip over and it’s a rally. Open the story in Hermes and see what each outlet led with, where coverage leans, and which stories one side is barely covering.

Ask the agent you already work with to find news you care about, show you the original reporting, and check where the facts come from. Compare Ground News’s publisher factuality ratings and ownership details, hide paywalled links, or see how many outlets ran the same wire report. When five outlets carry one report, your conversation can say exactly that.

## Ground News on the web and your phone

Grounded Hermes is an independent plugin. Its public story reader works without a subscription. Ground News offers paid features on its own site and apps, including expanded Blindspot and factuality tools on Premium and personal reading insights on Vantage. Annual offers can make a substantial difference. Compare the features you’ll use and the full annual checkout total before picking a plan. [Ground News](https://ground.news/) · [Plans and features](https://help.ground.news/en/articles/648513) · [Apple App Store](https://apps.apple.com/app/ground-news/id1324203419) · [Google Play](https://play.google.com/store/apps/details?id=com.checkitt)

## Try it

**Hermes 0.23.4 or newer.** Install the plugin, enable **Grounded News** in Desktop, and open it from the sidebar. Paste a link or ID into **Open story**, then choose **Discuss in new chat** to bring the coverage into a draft. [Hermes setup](docs/hermes.md) · [Reader screenshot](docs/images/coverage-reader.png) · [Chat pane](docs/images/chat-pane.png)

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

Hermes runs the bundled Python CLI. On a cache miss or refresh, the CLI sends the requested search, story ID, or publisher URL to Ground News and stores the result in a local SQLite cache on the machine running the request. The reader also uses public Ground News story pages for wire groups and publisher details. Opening a publisher link connects to that publisher in the browser or a sandboxed Hermes reader. Bias percentages count only outlets Ground has rated.

Public reads and **Hide paywalls** work without a Ground account. Member data integration is pending. [Subscriber inventory](skills/ground-news/references/subscriber-inventory.md) · [Ground’s automation terms, §6.1(d)](https://about.ground.news/terms-and-conditions) · [OSINT Map export](integrations/osint-map/README.md) · [Tests](docs/hermes.md#verify-a-checkout)
