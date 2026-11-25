---
name: ground-news
description: Use Ground News to find a story or publisher article, compare coverage and blindspots, browse outlet, topic, and place feeds, or return to saved Ground News research in Codex.
---

# Ground News

Run `python3 -B <ground-news skill directory>/scripts/ground_news.py`. Resolve the directory from this skill's installed location so the command works from any project. Use the CLI for user-directed reads.

- **Find a story.** Run `search story "headline or topic"`, then `story STORY_ID`. Use `lookup "PUBLISHER_URL"` to ground one article. If the lookup finds no story, use headline search when a headline is available.
- **Compare reporting.** Use `story STORY_ID --more-sources` for a broader set of publisher links when needed. Attribute coverage, bias, factuality, ownership, and blindspot labels to Ground News. Use `biasSourceCount` as the denominator for Ground's left, center, and right percentages. Report `sourceCount` separately. Cite the Ground story and the relevant original publisher links. A coverage cluster does not establish independent reporting by each outlet.
- **Switch subjects.** Run `search interest "outlet, topic, or place"` and pass the result's `id` to `feed INTEREST_ID` or `trending INTEREST_ID`. For a known place code, use `feed --place US`. Use `blindspots` or `editions` for discovery. Source links' `sourceInfo.id` and interest results' `legacyId` identify publishers or older records. Use the interest result's current ID for feeds.
- **Resume a read.** Run `cache list`, `cache search "subject"`, or `cache show KEY`. Normal reads reuse saved responses. Use `--cache-only` for offline work and `--refresh` when the user asks for fresh information. Check `reads` for which snapshots were used and when they were fetched.

Use [the CLI and API reference](references/cli.md) for installation, output fields, request behavior, upstream terms, and the status of subscriber custom-feed support.
