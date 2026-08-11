# GraphQL capture-and-replay: beating the identity wall (Agoda, Aug 2026)

Context: H1 program `agoda-public`, scope https://www.agoda.com/book/.
The activities GraphQL gateway (`/api/activities/graphql`) backs that
flow. Prior session state (see graphql-schema-oracle*.md): schema mapped
via validation errors, but every execution returned
`{"data":null,"errors":[{"message":"Internal server error"}]}` for ALL
inputs — the "identity wall". This session went THROUGH the wall.

## What was actually wrong
NOT auth. The request FORMAT. The app POSTs:
- URL: `/api/activities/graphql?operation=details&activityId=1563604`
- BODY: `{"queryString":"?operation=details&activityId=1563604","query":"query details ($DetailsRequest: DetailsRequest!) { ... }","variables":{"DetailsRequest":{...}}}`
  (three keys: queryString + query + variables; plain `{"query":...}`
  bodies 500 on this gateway)
- HEADERS (complete set, from capture):
  ag-language-locale: en-us, ag-request-id, ag-retry-attempt: 0,
  ag-request-attempt: 1, ag-analytics-session-id, ag-correlation-id,
  ag-cid: -1, ag-language-id: 1, ag-language-group-id: 1,
  ag-origin: IN, ag-platform-id: 1 (NOT 0 — earlier probes used 0 and
  validation still passed, but the app sends 1), ag-whitelabel-id: 1,
  ag-whitelabel-token: F1A5905F-9620-45E5-9D91-D251C07E0B42 (== the
  `wlt` claim of the user JWT `token` cookie — decode JWT payload to
  find it), ag-use-mock: false, ag-activities-client-id:
  activities-web, ag-activities-client-context-id: 9102,
  ag-activities-identity-token: <per-service JWT>

## The per-service identity token
`AG-ACTIVITIES-IDENTITY-TOKEN` is NOT the session cookie. It is a
separate 5-part (non-standard JWT) token minted per client id
("activities-web") into the logged-in page's SSR bootstrap:
regex the page HTML for
`identityTokens":{"activities-web":"([^"]+)"` — present only when
session cookies are set (logged-out pages omit it entirely). Also in
the same bootstrap JSON: userId, languageId, cultureCode, origin,
currencyId, clientProfile, cid, whiteLabelId, pageTypeId, sessionId,
gatewayUrl, multiProductMse.cookieValue (often empty), isBotV2 flag.

## Capture pipeline (the reliable way)
browser_console fetch-hooks die on full page navigation (context
reset). Instead, standalone script:
1. `require('camoufox-js')` from C:\Users\HP\camofox\node_modules
   (module exports {Camoufox, launchOptions, NewBrowser, launchServer};
   `const browser = await Camoufox();` — callable, not `new`).
2. `ctx.addCookies([...])` with the session cookies (token, ul.token,
   xsrf_token, agoda.l2, agoda.user.03, ASP.NET_SessionId, agoda.cid).
3. `page.on('request')` → push {url, method, headers, postData} for
   URLs matching the API; `page.on('response')` → {url, status}.
4. goto the real page (waitUntil domcontentloaded + 9s settle), close,
   dump JSON. 51 requests captured incl. search/details/review/calendar/
   availability — the app's real queries with real field names.
5. Replay verbatim: python urllib with captured headers + body, handle
   Content-Encoding gzip. STATUS 200 + real data (110KB availability
   response: offers, offerId/offerGroupId/supplierOfferCode, payment
   {paymentModel MERCHANT, NON_REFUNDABLE 100P}, enrichedOfferOption
   specifications, offerOptionToken, INR prices 211.11 excl / 233.27
   incl).

## Isolation matrix (true auth boundary)
Replay captured request, strip one thing at a time:
- no identity token (cookies kept) → VALIDATION_ERROR BAD_REQUEST
- no cookies + no identity token → same VALIDATION_ERROR
- no cookies + identity token → FULL REAL DATA (110KB)
Conclusion: the per-service identity token ALONE authenticates;
cookies are not consulted by the gateway. Session-bound token =
expected auth (not a finding by itself); the finding class to chase is
whether a token is reusable/forgeable/not-bound-to-session.

## Signed product tokens resist tampering (verified Aug 2026)
The availability response embeds PRICES inside the client-visible
activityToken/offerOptionToken. Before writing the price-manipulation
finding, test token integrity:
1. DECODE: token = 5-byte header + base64url (urlsafe — contains `-`/`_`,
   standard base64 fails) of a mixed serialization: JSON with
   binary-tagged fields. Price appears as PLAIN ASCII in the stream:
   `"price":{"dt":"BOOK","q":1,"t":251.6,"co":278.02}`. A binary tail
   follows (the signature). Note: different offers/contexts mint tokens
   with different embedded prices (251.6 vs 211.11) — grep for the actual
   values in YOUR token, don't assume the docs' numbers.
2. TAMPER: same-length ASCII replacement (251.6 -> 1.000, 278.02 ->
   1.0000) keeps the binary framing intact; re-encode base64url, replay
   the captured request.
3. CONTROL: replay the ORIGINAL captured request in the same loop.
   Measured: tampered -> 6/6 HTTP 400 "Unable to deserialize request";
   control -> 200 + 84KB real data. Token is server-signed/HMAC'd; any
   modification rejected at deserialization. => price manipulation via
   token tampering BLOCKED. Verdict: refuted by PoC, mark it in the
   ledger, do not re-chase.
4. The remaining price/IDOR vectors (getBooking IDOR by reference +/- 1,
   createBookingNoCC on paid inventory, negative/zero quantity,
   expectedPrice mismatch) all require the createBooking mutation — which
   only fires on real form submission in the booking flow (Choose ->
   customer info -> submit). Capture it the same way (drive the flow in
   the standalone capture script), then test each vector. Until the
   mutation is captured, those vectors are UNTESTED, not disproven.

## Lesson distilled
When hand-built requests 500 while the app works: capture the app's
real request with a standalone browser script and replay verbatim
before touching another hypothesis. Format/header deltas are the usual
cause; auth is the last thing to blame.

Files on disk: C:\Users\HP\recon\agoda_capture.cjs (capture),
agoda_capture.json (51 requests), agoda_replay.py / agoda_replay2.py
(verbatim replays), agoda_details_resp.json, agoda_availability_resp.json
(110KB real data), agoda_auth.sh (cookie/AG header set).
