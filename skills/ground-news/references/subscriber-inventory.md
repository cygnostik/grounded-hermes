# Subscriber and personal reading data

Reviewed November 24, 2026. These observations come from Ground’s published website and Firefox extension. The referenced clients describe the requests below. **Signed-in requests, tier enforcement and private response schemas remain untested.** The public story summary already provides publisher links, bias counts, and aggregate factuality and ownership counts where available. A personal reading-history question requires different data from a question about a story’s coverage. [Subscription features](https://help.ground.news/en/articles/648513)

## Web client

Paths in this table are relative to `https://web-api-cdn.ground.news/api`. Parameters in braces are placeholders. The methods and result names reflect client code and may change between deployments.

| Reader feature | Observed read operation | What still needs a signed-in check |
| --- | --- | --- |
| Search custom feeds | `GET /v04/customFeed/list?limit={n}` with optional `q` | Compare the returned rows to the account’s Custom Feeds screen. Determine whether results include public feeds, owned feeds, or both. The site describes custom feed creation as a Premium/Vantage feature. [Client](https://ground.news/_next/static/chunks/1c5ea469517abd87.js) · [Help](https://help.ground.news/en/articles/866177) |
| Custom feed settings | `GET /v04/customFeed/{feedId}` and `GET /v04/customFeed/{feedId}/interests/list` | Compare the saved name, description and any/all/excluded topic or place rules with a feed already owned by the reader. Inspect where that feed’s *stories* are loaded. These two calls read configuration. [Client](https://ground.news/_next/static/chunks/1c5ea469517abd87.js) |
| Shared feed read | `GET /public/customFeedPublic/{feedId}?limit={n}` | The web client reads `feedInfo`. A working example requires an actual published feed ID. Verify with an intentionally shared feed. [Client](https://ground.news/_next/static/chunks/39d47d8fa2058016.js) |
| My Feed | `GET /v04/feed/my` with optional repeated `interestIds` parameters | The client reads `eventIds`. Compare ordering and filters with My Feed. Confirm how missing and empty filters differ. [Client](https://ground.news/_next/static/chunks/be175e20eb42e0d1.js) |
| Followed topics and sources | `GET /v04/interests/listMy?filter={text}&type={type}` | Confirm accepted type labels and the IDs needed to open the corresponding outlet or topic feed. [Client](https://ground.news/_next/static/chunks/dd81ceb217235121.js) |
| Hidden sources | `GET /v04/source/blocked` | Compare results with the account’s hidden publishers. [Client](https://ground.news/_next/static/chunks/3fe0c274b1b7924a.js) |
| Saved status for one story | `GET /v04/eventRoom/feedUserData/{eventId}?fields=youFollow` | Test one saved and one unsaved item. The client reads `youFollow`. [Client](https://ground.news/_next/static/chunks/df635722a7c02ad6.js) |
| Citations | `GET /v04/citations/get?limit=3&offset={offset}` | The web client starts at offset zero. Check a populated and an empty list, page ordering and available citation fields. Ground describes this as a registered-reader feature. [Client](https://ground.news/_next/static/chunks/f3c989c177bd4bd3.js) · [Citations screen](https://ground.news/my/citations) |
| Story ownership chart | `GET /public/event/{eventId}/ownershipSunburst` | The UI conditionally loads the `ownershipSunburst` field when ownership display is enabled. Verify a Vantage chart against the response, including unknown or missing owners. [Client](https://ground.news/_next/static/chunks/df635722a7c02ad6.js) |
| Existing outlet/topic summary | `GET /public/vectors/getInterestLevelSummary/{id}` | The client consumes `summary` and `citationsForSummary`. Verify availability for a selected outlet and the handling of absent summaries. The client also has a separate generation action. [Client](https://ground.news/_next/static/chunks/c9e5815a3d647de3.js) |

**My News Bias.** Ground’s web client uses a Next.js server action named `getMyNewsBiasDataAction`. The UI recognizes `days7`, `days30`, `days90`, `days180`, and `year1` time ranges. A Vantage session with reading history is needed to check the available ranges, returned fields and empty-history behavior. The action reference belongs to the deployed UI build. No stable standalone REST route was established. [Dashboard](https://ground.news/my-news-bias) · [Client](https://ground.news/_next/static/chunks/5c3189fe9a36f4c2.js)

## Saved stories in the browser extension

Ground’s Firefox extension 3.2.1 ships a saved-story read sequence in `js/menu.js`. These paths are relative to `https://production.checkitt.news/api`. Both requests take the reader’s session. The four-story preview is the limit used by the extension. Full list traversal remains unverified. [Published extension package](https://addons.mozilla.org/firefox/downloads/file/4465709/ground_news_bias_checker-3.2.1.xpi) · [Ground’s saved-story guide](https://help.ground.news/en/articles/2044545)

1. `GET /v06/story/feed/followed?ids=true&limit=4` retrieves saved story IDs.
2. `GET /public/extension/savedArticles?ids={comma-separated-ids}` requests records for that selection. The extension also reads `GET /public/extension/articleIsSaved?id={storyId}` for a single bookmark’s state.

## Testing with an account

Use an already signed-in Ground browser session and a reader-selected story, custom feed or saved item. Compare a single normal UI read with its network response. Record the view, plan, request method and path, response field names, empty cases and pagination. Keep account identifiers, session values, personal reading history, saved story titles and raw responses out of fixtures. Subscriber access and private fixtures are unnecessary for the public CLI and its local cache.
