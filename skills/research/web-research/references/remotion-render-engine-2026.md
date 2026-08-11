# Remotion vs HyperFrames vs Motion Canvas — verified render-engine dossier (Aug 9, 2026)

Context: decision input for an agent-driven automated documentary pipeline ("is Remotion a better render core than HyperFrames?"). Every number below was live-verified at fetch time (remotion.dev, motioncanvas.io, GitHub API, npm registry, YouTube HTML). Full report on disk: `C:\Users\HP\remotion_research\remotion-deep-dive.md`; raw page extracts in `C:\Users\HP\remotion_research\docs\*.txt`.

## Ecosystem size (live, 2026-08-09)
- remotion-dev/remotion: **55,919★**, 4,157 forks, license "Other" (Remotion License, source-available), created 2020-06-23. npm/30d: `remotion` **6.25M**, `@remotion/cli` 4.01M, `@remotion/lambda` 675K. Latest 4.0.507 (5.0 unreleased — migration docs live, see /docs/5-0-migration).
- motion-canvas/motion-canvas: **18,907★**, MIT, created 2022-08-03. npm/30d: `@motion-canvas/core` 15.5K, `@motion-canvas/2d` 17.5K (there is NO bare `motion-canvas` package — that 404s on npm).
- HyperFrames: `hyperframes` npm **937K downloads/30d**, v0.7.103.

## Headless render performance & parallelism
- Model: every frame rendered by headless Chromium, stitched with FFmpeg. `--concurrency` = parallel Chrome tabs locally; on Lambda = parallel functions (`framesPerLambda`, `concurrencyPerLambda`). https://www.remotion.dev/docs/terminology/concurrency
- Official Lambda timings (4.0.381, 2048MB, us-east-1) https://www.remotion.dev/docs/lambda/cost-example:
  - Hello World: 7.56s warm / 11.02s cold, $0.001
  - **1-min video: 18.91s warm ($0.017) ≈ 3.2× realtime**
  - **10-min HD: 56.09s warm ($0.103) ≈ 10.7× realtime**
  - 10s 4K: 45.28s warm ($0.013)
- Speedup blog (Mar 21 2024, v4.0.130): 1-min 64.8s→**28.3s**, 10-min 134.7s→**31.8s**, 40-min 582.6s→**264.2s** (1080p looped OffthreadVideo, 3000MB). https://www.remotion.dev/blog/faster-lambda
- Tuning: `npx remotion benchmark --concurrencies=...`; `--hardware-acceleration` (disable/if-possible/required, default disable); png slower than jpeg; vp8/vp9 slow encoders; mp3 audio codec ≫ faster than AAC.
- GPU caveat: headless Chromium disables GPU → WebGL/blur/box-shadow/2D-canvas effects slow; `--gl` to enable; **Lambda/Cloud Run have no GPU** (swangle). Remotion 5.0 enables WebGL/WebGPU by default. https://www.remotion.dev/docs/gpu
- `parallelism` renderMedia arg = renamed to `concurrency` (v3.2.17), removed in v4.0.

## Audio / music
- `<Audio>` (from `@remotion/media`): local `staticFile()` or remote URL; **multiple tracks mixed**, volume/trim/speed/pitch controls. Audio-only export mp3/aac/wav via CLI or `renderMedia()`; `--muted`. https://www.remotion.dev/docs/audio/importing ; /docs/audio/exporting

## Subtitles / captions
- `@remotion/captions`: `parseSrt()` (.srt import); transcription via `@remotion/install-whisper-cpp` (local, free, offline), `@remotion/whisper-web` (browser WASM), `@remotion/openai-whisper`, `@remotion/elevenlabs`. `createTikTokStyleCaptions()` word-level pages; export burned-in or .srt. https://www.remotion.dev/docs/captions/importing ; /docs/captions/transcribing ; /docs/captions/displaying

## Chapter markers — NOT native
- Zero "chapter" hits in repo CHANGELOG; only stale issue #216 (2021). `--metadata`/`metadata` (v4.0.216) embeds title/artist/composer/date/description/keywords — **no MP4 chapter atoms**. https://www.remotion.dev/docs/metadata. Chapters exist only in the **Recorder** product (scene markers). https://www.remotion.dev/docs/recorder/editing/chapters → plan an external chapter pipeline (YouTube description / post-render MP4 atoms). Same gap in HyperFrames and Motion Canvas.

## AI-agent driving (best-in-class)
- Official: "Remotion works well with coding agents such as Claude Code, Codex, Kimi Code and OpenCode" — `npx create-video --yes --blank` → `npx remotion skills add` → prompt the agent. https://www.remotion.dev/docs/ai/coding-agents
- **12 official Agent Skills** (github.com/remotion-dev/skills): /remotion-create, -markup, -studio, -render, -maps, -captions, -saas, -docs, -upgrade, -best-practices, -interactivity, -multimedia. https://www.remotion.dev/docs/ai/skills
- **MCP deprecated → /remotion-docs skill** (hosted MCP shuts down no earlier than Aug 31, 2026). https://www.remotion.dev/docs/ai/mcp
- `https://www.remotion.dev/llms.txt` serves (HTTP 200) + official LLM system prompt. https://www.remotion.dev/docs/ai/system-prompt
- SSR API: `bundle()` → `selectComposition()` → `renderMedia()`/`renderFrames()`/`renderStill()`/`stitchFramesToVideo()`; Node/Bun, GitHub Actions, Docker, Azure, Cloudflare, Vercel Sandbox, Lambda. https://www.remotion.dev/docs/ssr
- CLI: `npx remotion render <comp> out.mp4 --props=... --concurrency=N`; audio-only, GIF, image sequences. https://www.remotion.dev/docs/cli/render
- Client-side: `@remotion/web-renderer` (WebCodecs, no server). https://www.remotion.dev/docs/web-renderer/
- AI templates: "Prompt to Video" (OpenAI + ElevenLabs), "Prompt to Motion Graphics". https://www.remotion.dev/templates/prompt-to-video

## Licensing (source-available, NOT OSS)
- Free: individuals; for-profit **≤3 employees**; non-profits; evaluation. Company License for 4+. https://www.remotion.dev/license ; https://www.remotion.dev/docs/license/pricing
- **Remotion for Automators: $0.01/render, $100/mo minimum** — for video editors / prompt-to-video apps / Player embedding; no seats. (The tier an automated pipeline buys.)
- Creators $25/mo/seat; Enterprise from $500/mo.
- v5.0 changes: contractors count toward headcount; mandatory telemetry for company licenses; free tier key = `"free-license"`. https://www.remotion.dev/docs/5-0-migration

## AI ecosystem (GitHub-verified)
- **calesthio/OpenMontage — 46,251★, AGPL-3.0** — agentic video production system that explicitly arbitrates the two engines: *"Remotion is the default for data-driven explainers and anything using the existing React scene stack; HyperFrames is the default for motion-graphics-heavy briefs that express naturally as HTML + GSAP"* (runtime locked as `render_runtime`). Remotion comps: TikTok word-level captions, WhisperX subtitles, audio fade curves, TalkingHead avatar; end-to-end cost examples: 60s short **$1.33**, product ad **$0.69**, stills-to-video **$0.15**. https://github.com/calesthio/OpenMontage
- **Vincentwei1021/video-shotcraft — 4,301★, Apache-2.0** — Claude Code/Codex skill, 152 shot recipes for Remotion product videos. https://github.com/Vincentwei1021/video-shotcraft
- **DEBUNKED as Remotion-based:** ShortGPT (7,773★) and brainrot.js (955★) — zero Remotion references in README/package.json/tree. Do not cite.
- Products on Remotion (https://www.remotion.dev/resources): Typeframes, ClipPulse, Augie, aicut, vidbuilder.ai, Indream, CutSnap, Frameloop AI, LaunchCut, VibeKnow; GitHub Unwrapped / Spotify Wrapped 2025 data videos.

## Motion Canvas (comparison target)
- Editor-only rendering: click RENDER in the browser editor; playback captures frames to /output; exporters = image sequence (built-in) + `@motion-canvas/ffmpeg` video exporter ("still relatively new and may not have all the features you need"). https://motioncanvas.io/docs/rendering ; /docs/rendering/video
- Single audio track via project.ts config (`audio` + `audioOffset`) — no multi-track mixing. https://motioncanvas.io/docs/media
- **No documented CLI/headless/server-side render, no parallelism, no captions SDK, no AI-agent tooling.** Self-description: "not meant to be a replacement for traditional video editing software." https://motioncanvas.io/docs

## 2025-26 tutorial wave (YouTube titles/channels/dates verified via curl+ytInitialData regex)
- "Create motion graphics with AI – Simple tutorial for beginners" (Remotion official, ~Feb 2026, 85.8k views)
- "Make Unlimited AI Videos for Free with Claude" (Hasan Aboul Hasan, ~Jan 2026, 208k views)
- "How I Vibe Code Technical Videos With Claude Code and Remotion" (John Hartquist, ~Dec 2025)
- "Your Videos Don't Have to Look Amateur Anymore (Claude + Remotion)" (vidIQ, ~Jul 2026)
- "Remotion + Codex = Auto-Generated Videos" (Julian Goldie Agency, ~Jul 2026)
- "Create AI Video in 3 Prompts — Claude Code + Remotion Full Guide" (Rananjay Raj, ~Apr 2026)

## Verdict + costs of switching (as delivered)
Adopt Remotion as documentary render core; keep HyperFrames for GSAP-heavy motion pieces (mirrors OpenMontage's matrix). Costs: Automators plan $0.01/render + $100/mo min (or Company License at 4+ employees); React/TS re-authoring of compositions; external chapter handling; precompute GPU-heavy CSS effects for GPU-less cloud renderers.
