# Grounded News for Hermes

Grounded News is an unofficial Hermes Agent and Desktop plugin for public Ground News reads. It uses the bundled Ground News CLI and the same SQLite cache, so a story opened from Hermes can be revisited through the CLI and vice versa.

## Install and enable

Use a Hermes Agent and Desktop build with unified plugin packages, scoped REST, and the composer draft API. Development targets Hermes revision `2506f5b0a4d310b96ec2eb6f2de4ea7349ba4d15`. [Hermes Desktop Plugin SDK](https://github.com/NousResearch/hermes-agent/blob/2506f5b0a4d310b96ec2eb6f2de4ea7349ba4d15/website/docs/developer-guide/desktop-plugin-sdk.md)

1. Install the repository into the Hermes profile that should run the backend.

   ```sh
   hermes plugins install https://github.com/cygnostik/grounded-hermes.git
   ```

2. If the agent plugin is disabled, run `hermes plugins enable grounded-hermes` in that profile. Restart its gateway if the plugin routes or tools are missing from a running Hermes instance.
3. In Desktop, open **Capabilities → Plugins**, rescan if necessary, and enable the **Grounded News** Desktop contribution. Open **Grounded News** from the sidebar. The right pane shows saved stories and offers headline search and publisher URL lookup.

For a remote gateway, install and enable the Agent package on the remote profile. In Desktop's **Install from Git** dialog, install the Desktop contribution on the machine running the app. The reader uses the cache on the connected gateway.

The default cache is `~/.cache/ground-news`, or `$XDG_CACHE_HOME/ground-news` if set. To share a different cache, set `GROUND_NEWS_CACHE_DIR` to the same directory in both the gateway's process environment and the CLI shell. A Desktop app connected to a different machine reads that machine's cache. Opening the pane reads the cache only. Ground News receives a search, story ID, or publisher URL when an on-demand read misses the cache or an explicit refresh is requested. Original publisher links open in the default browser. [CLI behavior and upstream terms](../skills/ground-news/references/cli.md)

## Read and compare

- Search **Stories**, **Topics & publishers**, or **Article URL**. Select an interest to open its feed. Recent searches and feeds switch back to their existing results while Desktop is open. Use **Refresh results** to request a new snapshot.
- In the mini pane, enter a headline and press **Search news** to read the results there. Open a saved story to see its source counts, publication date and cached publisher links. **Compare coverage** opens the full view. Use the publisher rating filter and **More publishers** to inspect additional coverage when available. Ground News calculates bias percentages over the bias-rated subset.
- Use **Discuss in new chat** to switch to a fresh Hermes composer with the story ID, a coverage snapshot, and a comparison prompt. The draft is ready for review and manual submission. If the new composer already contains a draft, **Copy chat prompt** in the full view lets you keep it and paste the story where you choose.

## Agent tools

| Tool | Reads |
| --- | --- |
| `ground_news_search` | Story headlines and topic, publisher, or place interests |
| `ground_news_story` | Coverage and publisher links by exact story ID |
| `ground_news_lookup` | Ground story matching a publisher URL |
| `ground_news_feed` | Stories for an interest ID or place code |
| `ground_news_cache` | Saved story search and snapshot opening by cache key |
| `ground_news_blindspots` | Ground News's left and right blindspot lists |

Read tools default to the existing cache and accept `cache_only` or `refresh` as the read policy. The registered Hermes skill is available as `grounded-hermes:ground-news`. No account details or API keys are required for these public tools.

## Verify a checkout

Run these from the repository root. The Python suite seeds a temporary cache and exercises the agent entry point and the Desktop REST router. The Node suite checks the Desktop registration, topic reuse, and draft handoff.

```sh
uv run --with fastapi --with httpx python -B -m unittest discover -s tests/hermes
node --experimental-vm-modules --test tests/hermes/desktop.test.mjs
hermes plugins validate .
```

In Desktop, search for a headline, open a result, and check that it appears in **Saved stories**. Open it in the pane and switch to **Compare coverage**. Verify that **Discuss in new chat** fills an empty composer and preserves a composer with an unsent draft.
