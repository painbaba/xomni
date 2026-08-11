# Video-Gen Vendor APIs: Kling vs Runway — verified pricing/specs (Aug 9, 2026)

Session source: "DEEP DIVE: Kling AI (2.0/2.1) and Runway (Gen-4/Gen-4.5) APIs for programmatic video generation" — data fetched live this session; final side-by-side deliverable was NOT yet written when the session ended. All numbers below were read from official pages at fetch time. Items not reached are explicitly marked **UNVERIFIED** — do not fill them in from memory.

## Source URLs (all fetched live this session)
- `https://docs.dev.runwayml.com/llms.txt` → index; pages as `.md`: `guides/pricing.md`, `guides/models.md`, `ai-context.md`; bundle `_llms-txt/core-api.txt` (usage tiers at ~line 2240).
- `https://runwayml.com/pricing` (HTML; FAQ answers in embedded FAQPage JSON-LD — grep `acceptedAnswer`).
- `https://kling.ai/llms.txt` and `https://kling.ai/document-api/api.md` (raw markdown). SPA shell came back for `overview/pricing.md` — use the browser for table pages: `browser_navigate https://kling.ai/document-api/overview/pricing` → `browser_snapshot(full=true)` renders the full price table.
- Note: `app.klingai.com/...` redirects to `kling.ai/...`.

## RUNWAY — Gen-4 / Gen-4.5 (API = "Runway Dev")

### Credit economics
- API credits: **$0.01 per credit** (developer portal, dev.runwayml.com). Min top-up: **1,000 credits**. Sales tax may apply.
- **Gen-4.5 (`gen4.5`) = 12 credits/second** of output → **$0.12/s**.
- **Gen-4 Turbo (`gen4_turbo`) = 5 credits/s** ($0.05/s) — image-to-video only.
- `act_two` (character performance) = 5 cr/s. Others on the API: seedance2_5 (30 cr/s 720p, 20 cr/s 480p, 80-credit min), seedance2 (36-40 cr/s, 150 cr/s at 4K), hailuo3 (10-15 cr/s), aleph2 (28 cr/s, 56-credit min), veo3.1 (20-40 cr/s), gemini_omni_flash (10-11 cr/s), grok_imagine_1_5 (10-29 cr/s). Gen-4 image: 5 cr (720p) / 8 cr (1080p); gen4_image_turbo: 2 cr.
- Calculator logic in docs JS: `cost = duration × creditsPerSecond × 0.01`.

### API specs (gen4.5)
- `ratio`: **1280:720 or 720:1280**; `duration`: any **integer 2–10 seconds**.
- Async task model: POST create task (`/v1/image_to_video`, `/v1/text_to_video`, `/v1/video_to_video`) → returns task id → poll `GET /v1/tasks/{id}` until `SUCCEEDED`/`FAILED`. Every request needs **`X-Runway-Version: 2024-11-06`** header.
- SDKs: **`@runwayml/sdk` (Node)** and **`runwayml` (Python)** — `client.image_to_video.create({...}).waitForTaskOutput()` (default 10-min timeout). Also OpenAPI 3.1 spec at `/openapi.json`.
- Model Router: route by cost/latency/quality, billed at standard rate of selected model — no extra charge.
- **Agent-friendliness: high** — clean REST + official SDKs + queueing handled server-side (see tiers below). No RPM cap; concurrency throttling returns `THROTTLED` status and tasks are enqueued in order.

### API usage tiers (per model, per org; from core-api.txt)
| Tier | Max concurrency | Max gens/day | Max spend/mo | Reach tier by |
|---|---|---|---|---|
| 1 | 1 | 50 (video) / 200 (image) | $100 | default |
| 2 | 3 | 500 / 1,000 | $500 | after $50 purchased |
| 3 | 5 | 1,000 / 2,000 | $2,000 | after $100 purchased |
| 4 | 10 | 5,000 / 10,000 | $20,000 | after $1,000 purchased |
| 5 | 20 | 25,000 / 30,000 | $100,000 | after $5,000 purchased |

- **No requests-per-minute limit.** Over-limit task creation returns `429`.

### Runway app plans (runwayml.com/pricing; billed-annually prices)
- **Free**: $0 — 125 one-time credits, 5GB storage, "a selection of models". Watermark: pricing page lists "No watermarks" as a Standard+ feature → free tier implied watermarked (**implied, not explicitly stated on page**).
- **Standard**: $15 → **$12/mo** (annual) — 625 credits/mo (≈52s of Gen-4.5), 4K upscaling, no watermarks.
- **Pro**: $35 → **$28/mo** (annual) — 2,250 credits/mo (≈187s Gen-4.5), custom voices, 500GB.
- **Max**: **$76/mo** (annual) — 9,500 credits/mo, first access to new models, unlimited Topaz upscale.
- Credits on Standard/Pro do NOT roll over (reset within 24h of billing date). Free credits never expire. Newest app models include Gen-4.5, Nano Banana Pro, Aleph, Veo 3.1, "Kling 3.0" (Runway now resells Kling 3.0 in-app).
- **Commercial license terms: UNVERIFIED** (session ended before ToS fetch — check runwayml.com/terms; historically Runway grants commercial rights on paid plans).

## KLING — API (KlingAI Open Platform)

### Units
- **1 Unit = $0.14** (prices shown as "X Units ($Y)"). Per-second billing.

### Video model price table (API, fetched from kling.ai pricing page)
| Model | 720P /s | 1080P /s | 4K /s |
|---|---|---|---|
| Kling 3.0 Turbo (w/ native audio) | 0.8 U = $0.112 | 1.0 U = $0.14 | — |
| Kling 3.0 (no audio) | 0.6 U = $0.084 | 0.8 U = $0.112 | 3.0 U = $0.42 |
| Kling 3.0 (+ native audio, no voice control) | 0.9 U = $0.126 | 1.2 U = $0.168 | 3.0 U = $0.42 |
| Kling 3.0 Omni (no video input, no audio) | 0.6 U = $0.084 | 0.8 U = $0.112 | 3.0 U = $0.42 |
| Kling 3.0 Omni (+ audio / + video input) | 0.8–0.9 U = $0.112–0.126 | 1.0–1.2 U = $0.14–0.168 | 3.0 U = $0.42 |
| Kling O1 | 0.6–0.9 U = $0.084–0.126 | 0.8–1.2 U = $0.112–0.168 | — |
| Kling 2.6 (no audio) | 0.3 U = $0.042 | 0.5 U = $0.07 | — |
| Kling 2.6 (+ audio) | — | 1.0–1.2 U = $0.14–0.168 | — |
| Kling 2.5 Turbo | 0.3 U = $0.042 | 0.5 U = $0.07 | — |
| **Kling 2.1** | **0.4 U = $0.056** | **0.7 U = $0.098** | — |
| **Kling 2.1 Master** | — | **2.0 U = $0.28** | — |
| **Kling 2.0 Master** | — | **2.0 U = $0.28** | — |
| Kling 1.6 / 1.5 | 0.4 U = $0.056 | 0.7 U = $0.098 | — |
| Kling 1.0 | 0.2 U = $0.028 | 0.7 U = $0.098 | — |

- Multi-image-to-video: 0.4/0.7 U per s. Multi-element video editing: 0.6/1.0 U per s. Video Extension: 2.0 U ($0.28) / 3.5 U ($0.49) per call. Avatar: 0.4/0.8 U per s. TTS 0.05 U, Lip Sync 0.5 U per 5s, Text/Video-to-Audio 0.25 U per call, Image Recognition 0.1 U per call.
- Plain "Kling 2.0" no longer listed — only **2.0 Master** remains (2.1 & 2.1 Master still available; 2.0/2.1 are the legacy low-cost tier vs 3.0).

### API surface (kling.ai docs, Aug 2026)
- **"Kling API 2.0" just launched**: model-specific endpoints (one per model version, decoupled params), standardized auth, **deduction records via API** (cursor pagination — good for reconciliation/automation), markdown docs export. This is the API protocol version, NOT the model version.
- Current model lineup: 3.0 / 3.0 Omni / 3.0 Turbo, O1, 2.6, 2.5 Turbo, 2.1, 2.1 Master, 2.0 Master, 1.x.
- Docs nav: Developer Guide / API / Pricing / Updates. Full endpoint reference: `https://kling.ai/document-api/api.md` (41KB markdown — contains per-model request fields, durations, resolutions).
- **UNVERIFIED (not yet extracted):** per-generation max duration/resolution for each model (5s/10s clips at up to 1080p for 2.0/2.1 historically — read `api.md` to confirm), rate limits/concurrency, watermark policy on paid tiers, commercial license terms (see kling.ai Terms of API Paid Service + SLA pages in docs nav; app memberships at klingai.com pricing page — SPA, use browser).

## Next-session checklist (to finish the deliverable)
1. Read `api.md` for Kling per-model `duration`/`resolution`/`ratio` allowed values + endpoint paths (text2video/image2video/video2video) and any rate-limit section.
2. Kling watermark + commercial terms: kling.ai Terms of API Paid Service; Runway ToS for commercial-use clause.
3. Kling app subscription tiers (member plans) via browser on klingai.com/global/pricing for the app-side comparison.
4. 2026 reviews (Tom's Guide, The Verge, fxguide, YouTube tests) — use Bing News RSS / Google News RSS per main skill.
5. Cost model for documentary b-roll (10s clips): Runway gen4.5 = $1.20/10s clip; Kling 2.1 = $0.56/10s (720p) or $0.98 (1080p); Kling 2.0/2.1 Master = $2.80/10s (1080p only).
