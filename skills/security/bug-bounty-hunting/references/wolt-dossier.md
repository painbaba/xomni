# Wolt dossier (H1 /wolt) — recon 2026-08-08

## Program stats (live at recon)
- Launched Jul 2026 (fresh — early-bird dup odds)
- Assets in scope: 12 (wolt.com + iOS app + Android app + more)
- Reports received | 90 days: 694 | Resolved: 0 | Hackers thanked: 2
- Top bounty $2,500; total paid <$10,000; response efficiency 100%
- Gold Standard Safe Harbor; $100 floor
- Rule: "detailed reports with reproducible steps" required

## Asset surface (all unauth-probed)
- wolt.com — SSR SPA (venue page ~1MB HTML, data embedded server-side;
  no email/phone/token fields leaked in SSR — checked)
- Bundles: wolt-com-static-assets.wolt.com/{runtime,vendor,<chunk>}.js
- Venue URL pattern: /en/<cc>/<city>/venue/<slug> — TEST venues exist in
  the index (e.g. test-670e7897e3c56dcc5b5a0989-sh0p); slugs are Mongo
  ObjectIds (timestamp-based — enumerable, but venue data is public
  catalog anyway)

## API hosts discovered from the app's own requests (captured)
- consumer-api.wolt.com/consumer-api/... (consents-router/v1/
  consent-enrollments-config → 404 without proper path/params; regatta/
  consumer_client/exposures → 404)
- restaurant-api.wolt.com/v2/config (+ /config?lat=..&lon=.., /config/
  consents) — 200 unauth, rich config: feature_flags, ab_assignments,
  gift_card_shop { search_venue_ids: per-country venue ObjectIds (FIN=
  584ec11a24d4660d6806f550, ...) }, payment_methods { allowed_payment_
  methods: every country → ["card"] }
- gift-card-shop-http-api.wolt.com/api/v1/giftcard/config?country=fin —
  200 unauth: themes/styles, possible_amounts, max_gift_cards, max_bulk_
  gift_cards, available_countries
- **gift-card-shop-http-api.wolt.com/api/v1/giftcard/validate** — the
  money surface: GET→405 (exists, method-gated), POST→"Not authenticated"
  for every body shape ({code}, {gift_card_code}, {giftCardCode},
  {card_code}, {}). Auth check happens BEFORE code validation (good
  posture). OPTIONS→200 (CORS preflight open)
- unified-gateway.dashapi.com/decision-systems/v1/dvedge/evaluation/
  evaluate-struct — DoorDash risk/decision engine (anti-fraud) — fired by
  the page; likely needs auth, untested
- hcaptcha on the page (login/registration flow)

## Finding candidates (ranked, NOT yet tested — need account)
1. Gift-card validate: rate-limiting on code validation (enumeration →
   balance theft) — needs a logged-in account (FREE registration, no
   payment) + one gift card code to understand the format
2. Order-tracking IDOR (order reference enumeration → courier/customer
   PII) — needs an account + ideally one order
3. gift-card-shop purchase/redemption logic — post-auth
4. consumer-api consents-router IDOR (per-member preferences) — post-auth

## The one unlock step (free)
Register a Wolt account (email+password, NO payment) → harvest session
cookies → run the request-capture harness on the gift-card shop + order
flow → test validate rate-limit / reference IDOR. Mirrors the Agoda
cookie-dump unlock pattern (use ONLY wolt.com cookies from any dump).

## Files from this session
- C:\Users\HP\recon\wolt_venue.html (1MB SSR page)
- C:\Users\HP\recon\wolt_capture.json (127 requests from venue page load)
- C:\Users\HP\recon\wolt_capture.cjs (capture harness for wolt)
- C:\Users\HP\recon\wolt_h1.txt (H1 program page text)
