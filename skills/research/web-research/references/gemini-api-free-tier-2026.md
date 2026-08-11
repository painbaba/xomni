# Gemini API / Google AI Studio free tier — verified knowledge bank (2026-08-07)

All facts verified live 2026-08-07 against ai.google.dev (page "last updated" dates in parentheses). Full report on disk: `C:\Users\HP\gemini_research\gemini_free_tier_2026.md`. Treat model statuses as point-in-time — re-verify before asserting.

## URL map (where each fact lives)
- Free-vs-paid per model + pricing: https://ai.google.dev/gemini-api/docs/pricing
- Catalog + endpoints + shutdown flags: https://ai.google.dev/gemini-api/docs/models (updated 2026-08-05)
- Per-model specs (context window, output limit, capability flags): https://ai.google.dev/gemini-api/docs/models/<model-id> (e.g. `/models/gemini-3.6-flash`)
- Rate limits mechanics + usage tiers: https://ai.google.dev/gemini-api/docs/rate-limits (updated 2026-07-21)
- **Per-model RPM/RPD: LOGIN-GATED** at https://aistudio.google.com/rate-limit (confirmed sign-in wall via browser). Docs removed the public table; only "per-project, RPD resets midnight Pacific, previews more restricted, limits not guaranteed" is documented.
- Shutdown schedule: https://ai.google.dev/gemini-api/docs/deprecations
- Regions (India listed): https://ai.google.dev/gemini-api/docs/available-regions
- Key types / auth migration: https://ai.google.dev/gemini-api/docs/api-key
- Historical free-tier ballpark (NOT verified for 2026): 2.5-flash ≈10 RPM/250 RPD, flash-lite ≈15 RPM/1,000 RPD, 2.5-pro ≈5 RPM/50 RPD.

## Free tier (Aug 2026)
- Free = "active project", no billing, spend limit N/A. Trade-offs: "content used to improve our products", limited model access, restricted limits. Paid tiers need a billing account; Tier 1 = $250 cap, Tier 2 = $2,000, Tier 3 = $20k–100k+.
- **Free models** (all 1,048,576 in / 65,536 out unless noted; all support function calling, structured outputs, thinking, and vision = text/image/video/audio/PDF input):
  - `gemini-3.6-flash` (GA Jul 21 2026 — flagship), `gemini-3.5-flash` (GA May 19 2026), `gemini-3.5-flash-lite` (GA Jul 21 2026), `gemini-3.1-flash-lite` (GA May 7 2026), `gemini-3-flash-preview` (still up)
  - `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` — still GA, no shutdown date
  - Live API: `gemini-3.1-flash-live-preview` (131K ctx); Live Translate: `gemini-3.5-live-translate-preview` (131K); TTS: `gemini-3.1-flash-tts-preview`, `gemini-2.5-flash-preview-tts` (8K ctx) — **TTS is on free tier**
  - Embeddings: `gemini-embedding-001`, `gemini-embedding-2`
- **Paid-only on free tier** (pricing shows "Not available"): `gemini-3.1-pro-preview` (+ `-customtools`), `gemini-omni-flash-preview` (video gen), ALL image gen — `gemini-3.1-flash-image` (Nano Banana 2), `gemini-3.1-flash-lite-image` (NB2 Lite), `gemini-3-pro-image` (NB Pro), `gemini-2.5-flash-image` (Nano Banana) — Veo 3.0/3.1 family, Imagen 4.0 family, Lyria 3 family, `gemini-2.5-computer-use-preview-10-2025`, `gemini-2.5-pro-preview-tts`. Context caching / Batch API / Flex: paid-only ("Not available" on free).
- Agent products `deep-research-*`, `antigravity-preview-05-2026`: billed at list rates, no free tier found (UNVERIFIED exact status).
- Image models: 131,072 in / 32,768 out; no function calling; structured outputs Not supported (except 2.5-flash-image SO=Supported).

## 2026 changes (the big ones)
- **Shutdowns:** `gemini-2.0-flash` + `gemini-2.0-flash-lite` (Jun 1 2026), `gemini-3-pro-preview` (Mar 9 2026), `gemini-3.1-flash-lite-preview` (May 25 2026), `gemini-3.1-flash-image-preview` + `gemini-3-pro-image-preview` (Jun 25 2026), Imagen 4.0 family (Aug 17 2026). `gemini-2.5-flash-image` deprecates Oct 2 2026. NOTE: shut-down models still appear on the pricing page — cross-check deprecations.
- **Image generation (Nano Banana) left the free tier** — free tier is now text/audio/live/embeddings only.
- **Key migration:** all new keys are *authorization keys* bound to a Google Cloud service account (auto-created for new users); **standard API keys are rejected from September 2026**. New users get a default project + key automatically after accepting ToS.
- New GA free models: 3.6-flash, 3.5-flash, 3.5-flash-lite, 3.1-flash-lite. Search grounding: 5,000 free requests/month shared across 3.x models (then $14/1k); listed "Not available" under free standard tier in pricing — UNVERIFIED for free tier.

## Signup / India
- India is explicitly in the supported-regions list (available-regions page). Works from India.
- No credit card required for free tier; requirements: Google account, 18+, possible age verification. Blocked regions / under-18 get a notice on the available-regions page.
- Same API key covers all Gemini API endpoints, but free ACCESS is per-model — Imagen/Veo/Lyria/Nano Banana stay paid even with a valid key.

## Extraction recipe that worked (ai.google.dev)
1. `curl -sSL <url>` → HTML (SSR'd, full content; a spoofed `-A` UA string failed where plain `-sSL` worked).
2. Python: strip `<script>/<style>` → `re.sub(r'<[^>]+>','|',s)` → `html.unescape` → `re.sub(r'\|+','\n',s)` → drop lines < 3 chars → greppable text.
3. Model specs: label:value table on `/docs/models/<id>` pages — regex `Input token limit\n([\d,]+)`, capability flags `Function calling\nSupported|Not supported`, etc. Parse all models in one batch.
4. Free/paid: on the pricing page, regex endpoint lines, window-scan ~40 lines for first `Free Tier`, classify `Free of charge` vs `Not available`.
