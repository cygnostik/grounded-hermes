# Grounded News for Hermes

Grounded News is an unofficial Hermes Agent and Desktop plugin for public Ground News reads. It uses the bundled Ground News CLI and the same SQLite cache, so a story opened from Hermes can be revisited through the CLI and vice versa.

## Install and enable

Use a Hermes Agent and Desktop build with unified plugin packages, scoped REST, and the composer draft API. Development targets Hermes revision `2506f5b0a4d310b96ec2eb6f2de4ea7349ba4d15`. [Hermes Desktop Plugin SDK](https://github.com/NousResearch/hermes-agent/blob/2506f5b0a4d310b96ec2eb6f2de4ea7349ba4d15/website/docs/developer-guide/desktop-plugin-sdk.md)

1. Install the repository into the Hermes profile that should run the backend.

   ```sh
   hermes plugins install https://github.com/cygnostik/grounded-hermes.git
   ```

2. If the agent plugin is disabled, run `hermes plugins enable grounded-hermes` in that profile. Restart its gateway if the plugin routes or tools are missing from a running Hermes instance.
3. In Desktop, open **Capabilities → Plugins**, rescan if necessary, and enable the **Grounded News** Desktop contribution. Open **Grounded News** from the sidebar or use its right pane beside a chat.

For a remote gateway, install and enable the Agent package on the remote profile. In Desktop's **Install from Git** dialog, install the Desktop contribution on the machine running the app. The reader uses the cache on the connected gateway.

The default cache is `~/.cache/ground-news`, or `$XDG_CACHE_HOME/ground-news` if set. To share a different cache, set `GROUND_NEWS_CACHE_DIR` to the same directory in both the gateway's process environment and the CLI shell. A Desktop app connected to a different machine reads that machine's cache. Opening the pane reads the cache only. Ground News receives a search, story ID, or publisher URL when an on-demand read misses the cache or an explicit refresh is requested. Opening an article loads the publisher's page in a sandbox when the Desktop SDK supports it. [CLI behavior and upstream terms](../skills/ground-news/references/cli.md) · [Hermes frame SDK](https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk#embedding-external-content)

## Read and compare

- Use **Open story** in the reader or right pane. Paste a Ground News link, publisher article link, or story ID and press Enter to open coverage directly.
- Search **Stories** or **Topics & publishers**. Select an interest to open its feed. Recent searches and feeds reuse their existing results while Desktop is open. Use **Refresh results** to request a new snapshot.
- In the mini pane, enter a headline and press **Search news**. Open a story and click a publisher headline to read it in Hermes. Use **Previous** and **Next** to move between publishers covering the same story. **Open in browser** is available for sites that restrict embedding or require a sign-in.
- Use **Compare coverage** in the mini pane to open the full view. Switch between **Articles**, **Bias**, **Factuality**, and **Ownership** from the story. The publisher rating filter and **More publishers** help you find other coverage. Ground News calculates bias percentages over the bias-rated subset.
- **Factuality** shows Ground News’s breakdown and lets you filter the publisher list by rating. Each rating describes the outlet. Select **Unknown** to see outlets without a reported rating.
- **Ownership** shows the breakdown, lists the owners Ground names for each outlet, and filters by ownership category. One outlet can appear under several categories.
- **Wire reports** shows reports Ground groups across two or more listed outlets. Each group gives separate outlet and article counts and links to the copies. **Hide paywalls** hides matching links without reducing the group totals. Articles outside these groups may still be syndicated.
- **Hide paywalls** applies across stories in Hermes. It uses public Ground News story-page labels to hide links marked paywalled or sometimes paywalled. Unlabeled links stay visible. The same filter applies to **Previous** and **Next** in the article reader.
- Use **Discuss in new chat** to switch to a fresh Hermes composer with the story ID, a coverage snapshot, and a comparison prompt. The draft is ready for review and manual submission. If the new composer already contains a draft, **Copy chat prompt** in the full view lets you keep it and paste the story where you choose.

## Agent tools

| Tool | Reads |
| --- | --- |
| `ground_news_search` | Story headlines and topic, publisher, or place interests |
| `ground_news_story` | Coverage and publisher links by exact story ID |
| `ground_news_lookup` | Coverage for a Ground News story link or matching publisher article |
| `ground_news_wire_reports` | Shared wire reports, distinct outlet counts, and article links, using the Ground News story URL and ID |
| `ground_news_feed` | Stories for an interest ID or place code |
| `ground_news_cache` | Saved story search and snapshot opening by cache key |
| `ground_news_blindspots` | Ground News's left and right blindspot lists |

Read tools default to the existing cache and accept `cache_only` or `refresh` as the read policy. The registered Hermes skill is available as `grounded-hermes:ground-news`. No account details or API keys are required for these public tools.

## Verify a checkout

For all CLI, Hermes, and map fixture suites, run `uv run --no-project --with fastapi --with httpx make test` from the repository root with Python, Node.js, Make, and uv available. The optional OSINT Map compatibility check also needs `OSINT_MAP_CHECKOUT`.

Run these from the repository root. The Python suite seeds a temporary cache and exercises the agent entry point and the Desktop REST router. The Node suite checks the Desktop registration, topic reuse, and draft handoff.

```sh
uv run --with fastapi --with httpx python -B -m unittest discover -s tests/hermes
node --experimental-vm-modules --test tests/hermes/desktop.test.mjs
hermes plugins validate .
```

In Desktop, search for a headline, open a result, and check that it appears in **Saved stories**. Open it in the pane and switch to **Compare coverage**. Verify that **Discuss in new chat** fills an empty composer and preserves a composer with an unsent draft.

## Marketplace listing

The catalog requires a publicly cloneable HTTPS repository. For a Grounded Hermes release, the owner or a major contributor submits `plugin-catalog/grounded-hermes.yaml` to `NousResearch/hermes-agent` with the full 40-character commit SHA, the tools above, and a tested Hermes version floor matching the manifest. Use `Grounded Hermes` as the display title, `community` as the tier, and `desktop` as the category. Run `hermes plugins validate . --install-deps` on the release checkout. Include UI screenshots and disclose requests to Ground, local cache access, and the bundled CLI subprocess in the PR. A maintainer’s merge creates the listing. [Submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)

Use [Please Stand By](images/please-stand-by.jpg) for the catalog’s `image` field (1200 × 600). Put the [coverage reader](images/coverage-reader.png) and [chat pane](images/chat-pane.png) in `screenshots`, which accepts up to six images. Use HTTPS GitHub-hosted image URLs pinned to the release SHA. The Marketplace also renders the README from that commit, including its *Evening Spin* header. [Catalog entry schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md#entry-schema)
