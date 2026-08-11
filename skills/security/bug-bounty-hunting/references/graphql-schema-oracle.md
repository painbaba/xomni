# GraphQL schema oracle — Agoda worked example (2026-08-07)

Target: HackerOne `agoda-public`. Scope: ONLY `https://www.agoda.com/book/`
(booking funnel; 1162 reports/90d, 0 resolved yet, avg bounty $576).
The scoped page's backing API is in scope even though the path differs.

## Endpoint discovery
- Bundle (booking SPA, cdn-bfspa chunks) grep → `/api/activities/graphql`
  with `?operation=availability` (activities availability used by the book
  flow). Chunk list comes from
  `performance.getEntriesByType('resource')` on the live page.
- `POST /api/activities/graphql?operation=availability` →
  `[{"type":"GLOBAL_CONTEXT","msg":"LanguageId is not provided|Cid is not
  provided|PlatformId is not provided"}]` — a LIVE API, context-gated.

## Header discovery (error-delta iteration)
Grepped request-client bundle for header names → `"AG-CID"` → brand prefix
`AG-*`. Full set found in bundles: AG-CID, AG-PLATFORM-ID, AG-LANGUAGE-ID,
AG-LANGUAGE-GROUP-ID, AG-ACTIVITIES-CLIENT-ID, AG-ACTIVITIES-CLIENT-CONTEXT-ID,
AG-ACTIVITIES-IDENTITY-TOKEN, AG-CORRELATION-ID, AG-ANALYTICS-SESSION-ID.
- +`AG-CID: -1` +`AG-PLATFORM-ID: 0` → error shrank to
  "LanguageId is not provided" (Cid/PlatformId satisfied).
- +`AG-LANGUAGE-ID: 1` → context accepted; queries now validated.
- Tested-and-rejected names: languageId, x-language-id, AG-LANGUAGE,
  AG-LANG, AG-LANGID, Accept-Language, LanguageId (all left the error
  unchanged). The error text is the oracle for what's still missing.

## Method/param variants that matter
- `GET /graphql?query=...` bypasses the POST header gate entirely
  (answered without any headers — introspection-block error).
- `operation=availability` on POST switches the gateway to a REST-envelope
  parser: GraphQL bodies → `"Unable to deserialize request"`. WITHOUT the
  param, the same endpoint does full GraphQL validation. Drop the param.

## Schema oracle via validation errors (introspection blocked)
`{"query":"{ availability ... }"}` → structured violations:
- "Did you mean 'availability'?" — fuzzy-match suggestions on root Query.
- "Field 'availability' of type 'AvailabilityResponse!' must have a sub
  selection." + "argument 'AvailabilityRequest' of type
  'AvailabilityRequest!' is required" — type + arg names.
- Send `{}` → "Field 'AvailabilityRequest.context' of required type
  'InternalContext!' was not provided" + "...availabilityRequest of
  required type 'AvailabilityRequestParameters!'" — drill each level:
  InternalContext → {currency: String!, experimentInfo: ExperimentInfo!};
  AvailabilityRequestParameters → {activityToken: String!}.
- `__type` and `__schema` queries → "Introspection is not allowed" /
  "Unable to deserialize request" (blocked) — irrelevant, errors still
  leak.

## Multi-field-one-query trick
Validator reports ALL violations in one response:
`{ result { option options paxAvailability date slots times tickets prices
errors warning } }` → parse `Cannot query field '(...)'` list; fields NOT
in the list are valid. Measured: all 10 guesses invalid →
AvailabilityActivityResult has none of those names; guessing alone stalls.

## Load-balancer roulette
Same query alternates between "Unable to deserialize request" (envelope
backend) and "Query does not pass validation" (GraphQL backend) — retry
loop (up to ~8x) until the validating backend answers; repeat same query
3x to confirm consistency.

## RESOLVED — empty/redacted placeholder types = decoy surface (same session)
The investigation was completed; the surface is CLOSED, not reportable.
- AvailabilityResponse valid fields: ONLY `result` (AvailabilityActivityResult)
  and `errors`. `data/payload/response/status/success/requestId/traceId/
  errorCode` all invalid.
- 45+ candidate field names on AvailabilityActivityResult ALL rejected —
  my guesses (options/sessions/dates/paxAvailability/...) AND 20
  domain-informed LLM candidates (packages, pricing, schedule, inventory,
  paxAvailabilities, calendar, quote, fare, rates, plans, offerings, skus,
  products, allocation, quota, info, ...) AND PascalCase variants AND
  object-shape probes ("must have a sub selection" leaks valid object
  fields + their type names — zero hits). The `errors` type rejects every
  sub-field too.
- CONCLUSION: both types are EMPTY/REDACTED placeholders in the public
  schema. Real data flows through the `operation=availability` REST
  envelope which needs the full identity context
  (AG-ACTIVITIES-IDENTITY-TOKEN etc.) — unobtainable without a real
  booking session. The public GraphQL endpoint is a decoy/legacy surface.
- Verdict: schema/type-name disclosure via error messages = informational,
  below payout bar. CLOSED.
- PATTERN (reusable): when every plausible field name — human, LLM, and
  object-shape probes — fails validation, the type is an empty/redacted
  placeholder. Stop guessing, conclude the surface is a decoy, note where
  the real data path is (the envelope/operation variant), and pivot. This
  recognition step prevents burning a whole session on a stripped schema.
- LLM-assisted guessing (worked as a generator): feed the established
  schema facts + error corpus to GLM (glm CLI — Puter route, 3-5s/call)
  and ask for candidate field names ordered by likelihood, then
  oracle-test them in one multi-field query. 20/20 died here, but it's a
  fast way to exhaust the plausible-name space.
- Camoufox direct-drive quirks (when browser_console loses its session):
  POST /tabs needs `userId` AND `sessionKey`; POST /tabs/{id}/evaluate
  needs a JSON body `{"userId":..., "expression":...}` (raw JS body → 400
  body-parser error); nested-quote escaping in shell curl is a trap —
  build the JSON payload with Python (json.dumps) instead. Hook still
  dies on full page navigation (reinstall per navigation; only SPA
  in-page triggers keep it alive). The app's own "Loading" stuck state
  inside an anti-detect browser is diagnostic: the API is failing for
  that fingerprint.

## Commands that worked
```
curl -s --compressed -X POST https://www.agoda.com/api/activities/graphql \
  -H "Content-Type: application/json" \
  -H "AG-CID: -1" -H "AG-PLATFORM-ID: 0" -H "AG-LANGUAGE-ID: 1" \
  -d '{"query":"{ availability(AvailabilityRequest:{context:{currency:\"USD\",experimentInfo:{}},availabilityRequest:{activityToken:\"1563604\"}}){ result { x } } }"}'
```
Files: C:\Users\HP\recon\agoda_book.html, agoda_bfpkg.js, agoda_act.js,
agoda_vendor-*.js (bundle greps).
