# Quora dossier (H1 /quora, 381 resolved, $100 min) — measured 2026-08

## Access
- Cloudflare JS challenge: curl → 403 "Just a moment..."; Camoufox SOLVES it
  (verify via `document.title` after 15-25s). Then call the API from INSIDE
  the page context — same-origin requests carry the cf_clearance session.

## API surface (measured from the live page)
- `POST /graphql/gql_para_POST?q=<queryName>` — the GraphQL query transport.
  The URL is EXACTLY `?q=<name>` — no other params.
- `POST /graphql/gql_servers` — 404 on GET (HTML), 405 on POST. NOT a
  handshake/negotiation endpoint; ignore it.
- Real query names captured from the page's own resource entries:
  `QuestionPagedListPaginationQuery`, `facebookAutoLogin_Query`.

## Format matrix — ALL DEAD ENDS (silent 400, empty body)
Every one of these returned 400 with an EMPTY response body:
- body `{}` / `{"queryName":..., "variables":{}}` / `{"args":{}}` /
  `{"variables":{}}` / `{"query":<name>, "args":{}}`
- headers `X-Requested-With: XMLHttpRequest`, `Accept: application/json`
- URL param `&webnode=1`
- POST to `gql_servers` first (405 — not a handshake)
The format is NOT plain JSON-of-args. The webnode transport's exact body
shape remains unknown — see the capture problem below.

## Why capture failed (the technique lesson)
- The question page PRELOADS all data via SSR: scrolling AND clicking
  "More answers below" fired ZERO new requests → the fetch/XHR hooks saw
  nothing. Hook-blind because there's nothing to hook until a genuinely
  new query fires (e.g. a real authenticated flow).
- The app's fetch wrapper is bound at module load — a hook installed after
  load misses calls even when they DO fire.
- The webnode bundle is loaded dynamically: NOT in `document.scripts`,
  NOT in `performance.getEntriesByType('resource')` (only third-party ad
  scripts appear). Static format extraction is blocked.
- Anonymous session confirmed: `m-uid=None` cookie, no webnode/relay/
  redux/preload globals on `window` → the unauth surface exposes
  PUBLIC data only (questions/answers — already visible in HTML).

## In-page probing techniques (reusable)
- Same-origin SYNCHRONOUS XHR from an evaluate works and returns
  `status + '|' + responseText` directly. Async fetch in evaluate breaks
  with "Promise rejection value is a non-unwrappable cross-compartment
  wrapper" — always use sync XHR for probes.
- The evaluate result is truncated at ~400 chars — do regex/extraction
  INSIDE the page and return only the matches (e.g. the JS-URL list),
  never the full HTML.
- Multi-step probes: split into separate small evaluate calls; one
  multi-line expression tends to 500 the evaluate endpoint.

## Verdict + unlock
- Money classes (message-thread IDOR, drafts, private answers, account-
  level authz) are ALL behind auth. Unauth GraphQL = low/no bounty value.
- Unlock: ONE free registration (no payment) → paste cookies → hunt the
  authenticated GraphQL with the capture-and-replay pipeline (§10.12).
  This ask was made to the user ("tell me if u nedd me"); when cookies
  land, the next move is a capture of the logged-in page's gql calls to
  learn the REAL request shape.
