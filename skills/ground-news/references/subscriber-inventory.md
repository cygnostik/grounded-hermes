# Subscriber custom-feed inventory

The web-client observations supplied for the integration identify these subscriber read paths:

| Path | Read purpose |
| --- | --- |
| `/v04/customFeed/list` | List the signed-in reader's custom feeds. |
| `/v04/customFeed/{feedId}` | Read one custom feed. |
| `/v04/customFeed/{feedId}/interests/list` | List the interests in a custom feed. |

The public CLI has no subscriber commands. To implement them later, verify the request methods, session mechanism, subscription entitlement, response schemas, pagination, and error responses using an authorized subscriber session. Check how a feed's entries are loaded and whether they are returned by one of these reads. Any later subscriber cache needs account separation and must keep session material out of stored response data and logs. Subscriber authentication and reads have not been tested.
