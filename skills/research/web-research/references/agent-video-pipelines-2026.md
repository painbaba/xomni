# AI Coding Agents Making Videos End-to-End — Verified Knowledge Bank (Aug 2026)

All entries live-fetched 2026-08-09 (GitHub READMEs via raw.githubusercontent, HN via Algolia API, Reddit via Arctic Shift archive, blog via curl; YouTube outputs verified via oEmbed). Full report: `C:\Users\HP\research_tmp\agent-video-pipelines-report.md`.

## Archetypes
1. **Full-stack agentic systems** — repo = tools + YAML pipeline manifests + skill files; the coding agent IS the orchestrator.
2. **Agent-skill studios** — SKILL.md turns Claude Code/Codex into a video studio for one genre.
3. **HTML → headless Chrome → FFmpeg** — agent writes HTML/CSS/GSAP (or React), Playwright/CDP captures frames, FFmpeg composites+muxes. Closest to our HyperFrames stack.
4. **Remotion-centric** — everything React, deterministic frame-driven time, Remotion Studio for human review.
5. **Spec-first director-bots** — interview → timed shot-by-shot `video-spec.md` → renderer.

Universal flow: `research → proposal → script → scene_plan → assets → edit → compose → render → automated self-review (ffprobe, frame sampling, audio levels, subtitles) → human approval gates`.

## Key verified sources
- **OpenMontage** github.com/calesthio/OpenMontage (~46k★) — "There is no code orchestrator. Your AI coding assistant IS the orchestrator." 12 pipelines, 100+ tools, 700+ skill files. Renders via Remotion **or HyperFrames** (`render_runtime`). Post-render gate: "If the review fails, the video is not presented." Slideshow-risk scoring, 7-dim provider scoring, budget caps ($0.50/action, $10 total). Costs: 60s short **$1.33** (Kling v3 + Chirp3), 70s elegy **$0.02**, product ad $0.69. Free real-footage path: CLIP-indexed Archive.org/NASA/Wikimedia/Pexels corpus.
- **Video Podcast Maker** github.com/Agents365-ai/video-podcast-maker (v5.2.1) — topic→research→script→11 TTS backends (Edge, MiniMax, ElevenLabs via `ttscn`)→Remotion→4K + BGM, FFmpeg mixing, React-rendered SRT. **Closest cousin to our pipeline.** Lesson: "A weak script renders into 4K garbage."
- **video-shotcraft** github.com/Vincentwei1021/video-shotcraft (~4.3k★) — 152 shot cards/209 previews + validated 36.2s template; its gallery intro was agent-made. Headless pitfalls: `--concurrency=1`, `chrome-headless-shell`, `--browser-executable` for blocked CDN.
- **claude-code-video-toolkit** github.com/digitalsamba/claude-code-video-toolkit (~1.9k★) — NARRATE▸SCORE▸GENERATE▸COMPOSE▸RENDER; skills incl. remotion/ffmpeg/playwright-recording/ltx2; Qwen3-TTS $0.01, LTX-2 $0.23; project.json lifecycle + auto CLAUDE.md resumption.
- **HyperFrames (HeyGen)** miguel07code.dev/writing/hyperframes + github.com/heygen-com/hyperframes — deterministic HTML video via CDP `BeginFrame` clock-stealing; 6 parallel Chrome processes (11-min render → 40s). "None of them have read After Effects… it can finally reply in a language it speaks natively." `npx skills add heygen-com/hyperframes`.
- **Framecraft** github.com/vaddisrinivas/framecraft (HN 47622914) — HTML scenes + **Edge TTS** + **Playwright MCP** + **FFmpeg MCP**, 4 auto-configured MCPs. 15s teaser ≈ **$1 / 49 LLM turns / 1.8M input tokens / 14 min** — "Token-heavy but it works."
- **Testreel** github.com/greentfrapp/testreel — JSON steps → Playwright → WebM/MP4/GIF demo videos, animated cursor.
- **video_explainer** github.com/prajwal-y/video_explainer (HN 46457051) — built in **3 days** with Claude Code (Opus 4.5). Whisper word-timestamps sync VO; MusicGen; natural-language feedback loop (Claude Code headless re-edits). "TTS generation happens BEFORE storyboard." Author still did VO himself ("TTS was too robotic").
- **Montage** github.com/simplexlabs/montage — "NOT meant to be run manually"; spring physics only, no CSS transitions. Remotion licensing caveat.
- **Shape of AI** yupanqui.xyz/shape-of-ai — 3:52 lyric video, 6,969 frames, zero video gen; agent fleet wrote all Remotion. "Automate what's automatable. Record what must be recorded. **Taste is the bottleneck.**"
- **Odyssey** (r/ClaudeAI 1v8bdj6) — "There's no application. Claude Code is the runtime… plain files: JSON for metadata, TSX for scenes." Planner / scene-builder / **visual-critic** / **fact-critic** agents. "A single agent building 30 minutes of video drifts a lot."
- **INFORMANT** (r/ClaudeAI 1vcpetw) — headless-Chrome frame pipeline → auto-uploaded YouTube 4K videos; **"number firewall"** (reject any script with an invented figure); adversarial per-task review caught a caption/audio race condition.
- **video-spec-builder** github.com/feicaiclub/video-spec-builder — director-bot → `video-spec.md` → HyperFrames renders. "The hard part isn't the rendering. It's figuring out what you actually want."
- **manim_skill** github.com/adithya-s-k/manim_skill — 3b1b-style; Manim CE vs ManimGL incompatible.
- r/ClaudeAI 1vcn6fr — YouTube AI-content **demonetization wave killed an agentic-video-editor business**; pivot to "un-ai-able" video; DaVinci Resolve assembly pipeline (beat-synced cuts) saved ~24h/project.

## Lessons
Playbooks beat orchestrators; critic agents that see only *output* catch drift; mandatory post-render verification; deterministic time over screen recording; TTS-first + word timestamps; human gates + budget caps; real cost $0.02–$1.33/short (token budget is the real spend); failure modes = drift, robotic TTS, headless env traps, weak scripts, platform demonetization, Remotion licensing.
