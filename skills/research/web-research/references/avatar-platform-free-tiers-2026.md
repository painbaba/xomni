# Cloud Talking-Head Avatar Platforms — Free Tiers (verified Aug 10, 2026)

Snapshot data — free tiers churn. Every fact below was fetched live from the cited URL on Aug 10, 2026 (curl + browser). Ranked for the use case "automated documentary narration (programmatic avatar generation)".

## Ranked table (free tier only)

| # | Platform | Free allowance | Watermark | API on free | Commercial on free | Quality | Max clip |
|---|----------|---------------|-----------|-------------|--------------------|---------|----------|
| 1 | Tavus (Developer Free) | **5 min/mo AI video gen + 25 min/mo conversational**, 25 stock replicas | **No** | **YES** (full suite, whitelabeled) | Not granted explicitly (plan framed "quickly test"; ToS not public on pricing page) | Photoreal (best-in-class) | minutes-based, no small cap stated |
| 2 | D-ID (Trial) | **3 min total** (videos+agents+translate+API), 14 days | **Full-screen** | **YES** (trial includes API) | No — "Personal use license" | Photoreal | 3 min total budget |
| 3 | Colossyan (Free) | **20 min/mo (NEO) + 0.5 min/mo (NEO2)** | Yes (removal = higher tiers) | No | Not granted | Photoreal | 20 min |
| 4 | Synthesia (Basic Free) | 1,200 credits/mo ≈ **10 min video/mo**, 25 AI assets | Yes (logo; removal = Starter) | No | Not granted ("experiment" tier, desktop-app CTA) | Photoreal | 10 min/mo total |
| 5 | HeyGen (Free) | **3 videos/mo, ≤1 min each**, 1 custom twin, ≤1080p | Yes (removal = paid) | No (API pay-as-you-go from $5) | No | Photoreal | 1 min |
| 6 | Elai (Free) | **1 min/mo**, 1 user | not stated on page | No (Public API row = dash) | Not granted | Realistic | — |
| 7 | DeepBrain AI (Free) | **3 videos ≤1 min**, 1 custom avatar, 16 one-time generative credits, 720p | not stated on page | No | Not on free | Realistic | 1 min |
| 8 | Vidnoz (Free) | **daily credits** (count JS-injected; promo: 60 cr/day Expressive Avatar), 720p | Yes | No | No (license paid) | Realistic | 3 min |
| 9 | Akool (Free) | limited free credits (not published), 5 GB, slow | **Full-screen** | No | No ("License: personal") | Realistic-ish (Seedance 2.0 limited) | up to 15 min (credit-limited) |
| 10 | Hedra (Free) | credits unpublished (in-app); "limited watermarked generations" | **Yes** | No (API separate, paid) | No (Commercial use = paid) | Expressive/stylized (Character-3 = 6 credits/sec) | — |
| 11 | Captions (Free) | **Zero AI credits** → cannot generate avatars | Yes (help article) | No (Mirage API paid: $0.175/sec video gen) | N/A | Realistic | N/A |
| 12 | Pika (Basic Free) | 80 video credits/mo, 480p only | No | No | Yes (stated) | Video-gen — NOT talking-head | per-credit |
| 13 | Arcads | no public pricing page (login-gated) | n/a | AI Video API + Lip Sync API exist (paid) | n/a | Realistic actors (1,000+) | n/a |
| 14 | Argil | **unreachable at fetch time** (curl + browser timeout; no recent archive) — NOT LIVE-VERIFIED | n/a | n/a | n/a | n/a | n/a |

## The two genuinely-free-API paths (the answer to "free programmatic avatar quota?")

- **Tavus Developer Free** — https://www.tavus.io/pricing : "Basic — Free, No upfront payment: Whitelabeled APIs · 25 minutes of AI conversational video · 5 minutes of AI Video Generation · Access to 25 stock replicas"; compare table: "API access — full access to our suite of developer APIs", "No watermark", 1080p. Async avatar API (script or audio → talking-face video, usage-based tokens, watermark only if you pass `watermark_image_url`): https://docs.tavus.io/api-reference/video-request/create-video.md . Starter $59/mo = 10 min video gen; Growth $397/mo = 100 min. 60s trailer with 2 presenter clips fits ~6× over. CAVEAT: free plan framed as testing; commercial rights not granted on the pricing page.
- **D-ID Trial** — https://www.d-id.com/pricing/ : $0, 14 days, "3 minutes for Videos, Agents, Video Translate & API", 100+ stock avatars, API access, **full-screen watermark**, **personal-use license**. Lite $4.7/mo = 10 min/mo (D-ID logo watermark); Pro $16/mo = 15 min/mo (commercial license, small AI watermark); Advanced $108/mo = 100 min. FAQ confirms full-screen watermark for trial.

## Largest manual (UI-only) free allowances

- **Colossyan Free** — https://www.colossyan.com/pricing : 20 min/mo with NEO (older model) + 0.5 min/mo NEO2, duration limit 20 min, 15 custom avatars, watermark (removal in Team+), no API on free.
- **Synthesia Free** — https://www.synthesia.io/pricing : "Basic Free — No credit card required; Includes 1,200 credits/mo · Usable for up to 10 minutes of video/month · 25 AI-generated video assets"; CTA "Get started on desktop"; Starter $29 adds MP4 download + logo removal + API → free = watermarked, no download, no API.

## Per-platform URL anchors (fetched Aug 10, 2026)

- Tavus: https://www.tavus.io/pricing (server-rendered 67KB — curl beat the region-gated browser shell)
- D-ID: https://www.d-id.com/pricing/ (JS cards — browser accessibility tree required; curl = skeleton + FAQ)
- Synthesia: https://www.synthesia.io/pricing (server-rendered; "plus-list" heuristic: Starter = "Basic + Download · Remove Synthesia logo · API access")
- HeyGen: https://www.heygen.com/pricing (Free: 3 videos/mo, ≤1 min, Avatar IV, ≤1080p, watermark removal = paid) + https://www.heygen.com/en-in/api-pricing ("Pay-as-you-go — from just $5")
- Colossyan: https://www.colossyan.com/pricing (JS cards; comparison table has the minute rows)
- Hedra: https://www.hedra.com/pricing (FAQ: free/cancelled = "limited watermarked generations"; video tab: Character-3 = 6 credits/sec, Veo 3.1 55/s, Sora 2 Pro 70/s, Kling 2.5 Turbo 10/s)
- Akool: https://www.akool.com/pricing (card "$0" = JS placeholder; comparison table = source of truth: Full-Screen watermark, Slow, 5 GB; API separate/paid)
- Captions: https://www.captions.ai/pricing (Free = "AI usage credits: None") + https://captions.ai/help/docs/troubleshooting/watermark + https://captions.ai/help/docs/api/pricing (Mirage API: captions $0.15/min; Mirage Video 1 talking-head $0.175/sec, 6s increments)
- Elai: https://elai.io/pricing (Free: 1 min, 80+ avatars; Public API row = dash on free)
- DeepBrain: https://www.deepbrain.io/pricing (Free: 3 videos ≤1 min, 720p, 16 one-time generative credits; "Commercial Use Rights" listed for paid)
- Vidnoz: https://www.vidnoz.com/pricing.html (Free: credits/day JS-injected, max 3 min/video, 720p, Vidnoz watermark; Full Commercial License = paid)
- Pika: https://pika.art/pricing (Free Basic: 80 credits/mo, 480p only, no watermark, commercial use — but not a talking-head tool)
- Arcads: https://www.arcads.ai/ (no public pricing; /pricing 404s in curl AND browser; AI Video API page exists at /features/ai-video-api)
- Argil: https://www.argil.co/pricing — UNREACHABLE (WinError 10060 timeouts; r.jina.ai 403; Wayback availability = no snapshots)

## Method notes (what worked)

- One execute_code batch: curl all pricing pages (Chrome UA), tag-strip, regex keyword windows (`free|trial`, `watermark|logo`, `credit`, `min`, `api`, `commercial|license`).
- Browser for JS-rendered plan cards (D-ID, Hedra, Colossyan); curl for server-rendered pages (Tavus, Synthesia, HeyGen, Elai, DeepBrain, Vidnoz, Pika, Akool table).
- DDG html hit a captcha challenge on the 3rd query — abandoned SERPs entirely; help centers + docs answered everything.
- Unverifiable = marked unverified (Argil, Arcads), never filled from memory.
