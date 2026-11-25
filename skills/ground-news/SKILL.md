---
name: ground-news
description: Use Ground News to find a story or publisher article, compare coverage and blindspots, browse outlet, topic, and place feeds, or return to saved Ground News research in Codex.
---

# Ground News

Run `python3 -B <ground-news skill directory>/scripts/ground_news.py`. Resolve the directory from this skill's installed location so the command works from any project. Use the CLI for user-directed reads.

- **Find a story.** Run `search story "headline or topic"`, then `story STORY_ID`. Use `lookup "ARTICLE_URL"` for a Ground News or publisher link. If the lookup finds no story, use headline search when a headline is available.
- **Tell the reader what happened.** Start with a short, neutral news brief. Use ordinary attribution for reported claims and keep the opening focused on the event. Follow with concrete differences in what outlets report or emphasize when relevant. Raise corrections, uncertainty, or access limits when they affect the answer.
- **Cite what you could read.** Link the Ground story and the relevant original articles. Attribute details to the source that supports them. Treat snippets, truncated text, and paywall prompts as partial access even when extraction reports success. If the Ground News snapshot is what you read, credit it for the summary. A coverage cluster does not establish independent reporting by each outlet.
- **Compare coverage.** Use `story STORY_ID --more-sources` for more publisher links when needed. Attribute coverage counts and blindspot labels to Ground News. Describe Ground News's bias, factuality, and ownership classifications as publisher-level. Use `biasSourceCount` as the denominator for the left, center, and right percentages. Report `sourceCount` separately when giving the split.
- **Check for wire copies.** When comparing coverage across outlets, use `paywalls GROUND_NEWS_STORY_URL STORY_ID` to get Ground News's wire identifiers. Count distinct outlets for each shared `wireStoryId` separately from article links. Coverage without a wire ID has unknown syndication status.
- **Switch subjects.** Run `search interest "outlet, topic, or place"` and pass the result's `id` to `feed INTEREST_ID` or `trending INTEREST_ID`. For a known place code, use `feed --place US`. Use `blindspots` or `editions` for discovery. Source links' `sourceInfo.id` and interest results' `legacyId` identify publishers or older records. Use the interest result's current ID for feeds.
- **Resume a read.** Run `cache list`, `cache search "subject"`, or `cache show KEY`. Normal reads reuse saved responses. Use `--cache-only` for offline work and `--refresh` when the user asks for fresh information. Check `reads` for which snapshots were used and when they were fetched.

Use [the CLI and API reference](references/cli.md) for installation, output fields, request behavior, upstream terms, and the status of subscriber custom-feed support.
