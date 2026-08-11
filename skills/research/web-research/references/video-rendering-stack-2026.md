# Video rendering stacks for faceless documentaries — verified knowledge bank (2026-08-09)

Purpose: choose a production stack for a Windows-based, agent-driven faceless documentary studio.
All facts live-verified 2026-08-09 (curl / browser / r.jina.ai mirrors; point-in-time — re-verify before asserting).
Full report on disk: `C:\Users\HP\rendering_stack_research.md`.
AI-video-gen vendor layer (Veo/Omni/Sora/Kling/Runway/Pika/Luma/Seedance/ComfyUI, Sora sunset dates) lives in `references/ai-video-gen-2026.md` and `references/video-gen-api-pricing-2026.md` — this file covers the RENDERING-FRAMEWORK + STOCK layers and the cost math that ties them together.

## Framework comparison (the decision table)

| | Remotion | Motion Canvas | HyperFrames | After Effects |
|---|---|---|---|---|
| Authoring | React/TS components; frame-number → markup (declarative) | TS generators; imperative timeline; single `<canvas>` | Plain HTML/CSS/JS + GSAP/Lottie/WAAPI; `data-*` timing attrs | GUI + ExtendScript JS / aerender CLI |
| GitHub | 55,918★, created Jun 2020, pushed Aug 9 2026 | 18,907★, MIT, created Aug 2022, pushed Jul 2 2026 | npm `hyperframes` 0.7.103, created Mar 23 2026 (repo heygen-com/hyperframes, Apache-2.0) | n/a (proprietary) |
| License | Source-available; free ≤3 people, paid above (Automators $0.01/render + $100/mo min; Creators $25/mo/seat) | MIT (truly open) | Apache 2.0 | US$22.99/mo (annual billed monthly) / $419.88/yr |
| Headless render | ✓ First-class: `renderMedia` (headless Chrome), Remotion Lambda (pay-while-rendering, <80 min FHD, 15-min AWS timeout) | ✗ **NO official headless path**: `@motion-canvas/cli` 404s on npm; issue #415 "Render projects headlessly" OPEN since 2023-02-25 (17 comments); render = editor RENDER button → image seq → ffmpeg, or `@motion-canvas/ffmpeg` plugin | ✓ CLI `npx hyperframes lint/check/render`; Node `@hyperframes/producer` API; managed cloud / AWS Lambda / Cloud Run; deterministic seek-render (puppeteer-core dep) | ✓ `aerender.exe` CLI for batch + render farms (`-project -comp -s -e -output -RStemplate -OMtemplate`; Adobe helpx doc updated Nov 3 2023) |
| Audio | Rich: import/trim/delay/volume/mute/speed/pitch/visualize/export; `<Audio>`, @remotion/elevenlabs | Basic: `makeProject({audio, audioOffset})` + ffmpeg exporter "Include audio" | AAC (MP4) / Opus (WebM); full timeline mix; TTS/captions pipeline | Full (GUI + AEOM) |
| Agent fit | Strong but React codegen + license >3 people | Weak: no headless path; releases stalled (last v3.18.0-alpha.0 Feb 2025) | **Built for agents**: "Write HTML. Render video. Built for agents." — 19 skills, CLI checks (lint/check), Studio; works with Claude Code/Cursor/Gemini CLI/Codex | Scriptable (aerender/ExtendScript) but GUI-licensed, render settings drift |

Official comparison pages (both fetched live): Remotion's "Difference to Motion Canvas" — https://v3.remotion.dev/docs/compare/motion-canvas (DOM vs canvas; declarative vs imperative; Remotion broad vs MC specialized for vector/informative animation w/ LaTeX + code blocks + GUI time-editing; Remotion commercial vs MC open source). HyperFrames' "HyperFrames or Remotion?" — https://hyperframes.heygen.com/guides/hyperframes-vs-remotion.md (HF: HTML+GSAP in seconds, no React/build step, Apache 2.0, agent-authored, seek-based deterministic render; Remotion: older/more established, more templates/tutorials/production history, mature Lambda; Remotion→HF port skill ≈80% mechanical, refuses useState/useEffect/async metadata).

## Negative findings (as important as the positives)
- **Motion Canvas cannot be driven headlessly** — no CLI package exists (`registry.npmjs.org/@motion-canvas/cli` = 404, 21-byte body); headless-render feature request open since Feb 2023 (https://github.com/motion-canvas/motion-canvas/issues/415). Any "MC in CI" plan needs a third-party puppeteer/player hack.
- **motioncanvas.io serves WordPress SEO-spam on unknown paths** (e.g. `/docs/player` returned a "digital marketing" parked page, generator tag "WordPress 7.0.3") while real docs pages (per sitemap) render fine. Hygiene flag: verify docs pages exist via the sitemap before trusting a URL; don't cite content from unknown paths.
- **Sora**: do not build on it — app discontinued Apr 26 2026, API discontinued Sep 24 2026 (official: https://help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation; press: the-decoder.com Mar 28 2026). API still priced on platform.openai.com/docs/pricing (sora-2 720p $0.10/s; sora-2-pro $0.30/$0.50/$0.70 at 720p/1024p/1080p; batch ≈50% off) — a live example of pricing pages outliving products.
- **Remotion license review above 3 people**: pricing page explicitly says "Must upgrade when your organization grows"; Automators tier is $0.01/render + $100/mo minimum — fine for products, wrong for an in-house studio that wants $0 infra.

## HyperFrames docs URL map (Mintlify — `.md` suffix + `/llms.txt` work)
- Index: https://hyperframes.heygen.com/llms.txt
- Rendering: /guides/rendering.md (MP4/MOV/WebM/GIF/PNG-seq; quality draft/standard/high; `--fps`, `--docker`; batch/cloud) · Node API: /packages/producer.md · Render paths: /deploy/overview.md (CLI → Producer → Engine → HyperFrames Cloud → AWS Lambda → Cloud Run) · vs Remotion: /guides/hyperframes-vs-remotion.md · determinism: /concepts/determinism.md
- npm `hyperframes` deps prove the render path: puppeteer-core, esbuild, sharp, hono, onnxruntime-node (layout checks).

## Stock footage + assembly (verified)
| Source | Cost | API | Limits |
|---|---|---|---|
| Pexels | Free, all content free | ✓ REST + key (Authorization header); video endpoint api.pexels.com/v1/videos/search | 200 req/hr + 20,000 req/mo default; unlimited with attribution; link-back required |
| Pixabay | Free | ✓ REST + key | 100 req/60s; attribution requested; **24h result caching REQUIRED** |
| Storyblocks | $21/mo billed annually ($252/yr) | ✗ no public API (web/app only) | Unlimited downloads, 1 user, individual license, 8K/4K/HD footage + templates + photos/vectors; "100% human-made stock" |
| ffmpeg | Free, open-source | CLI | Cross-platform convert/transcode/stream; v7.0 "Dijkstra"; multi-threaded CLI; hardware encoders |

## Cost math that settles the architecture debate (per 10-min, 1080p doc, ~60 shots)
- Full-AI pipeline: 300s of footage ≈ Veo 3.1 Standard $0.40/s = **$120+** (plus regens) · Kling 720p ≈ $33.6 · Runway Gen-4.5 (12 cr/s) ≈ 3,600 cr ≈ 1.6 Pro months ≈ $56.
- Hybrid (recommended): motion-graphics/data/type $0 + stock $0–21/mo + 8 AI hero shots × 6s = 48s @ Veo 3.1 Lite $0.05/s ≈ **$2.40** (or Kling ≈ $4.00).
- So: use AI only as a "footage generator" for hero shots; keep typography/data/numbers in the deterministic HTML core. Avoid AE-only (license + GUI + drift) and MC (no headless).

## Verification caveats from this run
- help.openai.com: Cloudflare Turnstile loop for curl AND browser (checkbox never passes) → r.jina.ai returns article markdown with canonical URL.
- Adobe helpx + adobe.com: curl 404s/blocks → r.jina.ai works (AE plans page shows US$22.99/mo + US$419.88/yr).
- platform.openai.com/docs/pricing.md → raw markdown tables (per-second video-gen pricing) — the `.md` mirror trick works on OpenAI's docs.
- kling.ai blog pages are Next.js but curl-able (credit guide with plan table); kling.ai/docs via llms.txt.
- motioncanvas.io sitemap is the authority on what pages exist (279 URLs); unknown paths = spam.
