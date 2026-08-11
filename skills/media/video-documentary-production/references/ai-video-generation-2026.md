# AI Video Generation Layer for Documentaries (verified Aug 2026)

Condensed from the Aug 9 2026 17-agent research swarm. Full reports on disk:
- C:\Users\HP\ai_video_tools_2026_report.md (tool landscape + ranked recs)
- C:\Users\HP\veo_research\VEO_API_DEEP_DIVE.md (exact Veo numbers)
- C:\Users\HP\comfy_research\local-video-gen-deep-dive.md (local ComfyUI)
- C:\Users\HP\remotion_research\remotion-deep-dive.md (Remotion verdict)
- C:\Users\HP\rendering_stack_research.md (render approaches comparison)
- C:\Users\HP\motion_graphics_pattern_catalog.md (15 data-viz patterns, wow÷effort)
- C:\Users\HP\claude-code-video-playbook.md + claude-code-video-hunt.md (agent pipelines + YT videos)

## The dead one: Sora 2
App discontinued Apr 26 2026; **API shut down Sep 24 2026** (openai.com/sora = discontinuation
notice; CNET dropped it from 2026 best-of). Never build on it.

## Cloud AI video (paid, per-second pricing — all live-verified)
- **Kling 3.0 / 3.0 Omni** (Feb 2026): native audio, 4K, API 2.0 **$0.084–0.168/s (1080p)**.
  Per-dollar engagement king for b-roll. Pika API Club resells at $0.09/s.
- **Veo 3.1** (preview): 8s clips (4/6/8s; 8 required for 1080p/4k/i2v), 24fps, native audio
  always on, extension to 148s. Gemini API: **$0.40/s** (720p/1080p) / $0.60 (4k);
  Fast $0.10 (720p)/$0.12 (1080p)/$0.30 (4k); Lite **$0.05** (720p)/$0.08 (1080p). Vertex:
  video-only $0.20 (silent cheaper); sampleCount 1-4 per request; videos deleted after 2 days.
  Veo 3 GA shut down Jun 30 2026 — use 3.1. Gemini Omni Flash ≈$0.10/s is Google's new
  multi-turn editing default.
- **Runway Gen-4.5**: best-reviewed cinematic realism (Digit: beats Veo 3.1), API **$0.12/s**,
  Model Router + **MCP for agent automation**, plans bundle Veo 3.1 + Kling 3.0 + Seedance 2.5.
- **Luma Ray 3.2** ("Dream Machine" → Luma Agents): 720p $0.06/s, 1080p $0.24/s, max 10s.
- Practical: a 60-min doc at ~35% b-roll coverage ≈ 20 min of footage ≈ $60-120 at Kling
  prices, $240+ at Veo standard — budget or go local.

## Local FREE AI video (ComfyUI) — the $0 path
- **Wan 2.2 = best local documentary b-roll model**: Apache-2.0, commercial use allowed.
  `Wan2.2-TI2V-5B` = hybrid T2V+I2V in one model; A14B series 480P/720P. 720p@24fps,
  ~5s/clip, "cinematic-level aesthetic control", good landscapes/locations/objects/people.
- HunyuanVideo / LTX-Video: viable alternatives; AnimateDiff/SVD = legacy (removed from
  official ComfyUI examples).
- **Agent automation**: ComfyUI local `/prompt` API + first-party Comfy MCP; ComfyUI Desktop
  v0.9.4 as browser front end. Civitai has ~63K-download Wan 2.2 workflows.
- Hardware: 720p video needs a real GPU (vendor claims only — test on target machine).
- Free footage (no AI): Pexels/Pixabay/Coverr/Mixkit/Videvo APIs (free tiers), archive.org
  Prelinger Archives, NASA, Library of Congress — see free-media-stack-2026.md for the
  footage-source matrix.

## Render core verdict (agent-driven docs)
- **HyperFrames = agent-native** (Apache-2.0, "Write HTML. Render video. Built for agents.",
  19 agent skills, deterministic seek-render, Node @hyperframes/producer API). Current stack
  validated.
- **Remotion = better for data-heavy/react flows**: deterministic frames, `--concurrency`
  parallel render (local tabs / serverless Lambda), built-in multi-track audio mixing,
  first-party caption SDK, agent skills + llms.txt. Costs: React/TS re-authoring + license
  (free ≤3 employees; Automators $0.01/render or Company License above).
- **Motion Canvas: NO headless render** (request #415 open since Feb 2023; editor-button →
  image sequence → ffmpeg) — human-only.
- Chapters are NOT native in HyperFrames or Remotion — add chapter markers via ffmpeg or
  YouTube chapters in upload metadata.
- OpenMontage (46k★ agentic video system) splits engines: HTML/GSAP motion (HyperFrames-
  class) for graphics, Remotion for data-heavy sequences.

## Claude Code / agent video pipelines (steal these)
- **yopiesuryadi/video-doc-pipeline** (github.com/yopiesuryadi/video-doc-pipeline): a Claude
  Code SKILL — screening → transcription → paper edit → voiceover → music → timeline
  assembly → QC → YouTube-ready. Proven: 215 raw clips (~57 min) → published 12:29 doc in
  ~1 working day. Ships GOTCHAS.md + launchd watcher.
- **OpenMontage** (github.com/OpenMontage, 46k★): "There is no code orchestrator. Your AI
  coding assistant IS the orchestrator." — skills + tools + YAML pipeline manifests.
- Universal flow: research → proposal → script → scene plan → asset gen → composition →
  render → automated self-review (ffprobe, frame sampling, audio levels, subtitle presence).
- Top YouTube tutorial: "Make the PERFECT Videos with Claude Code (Full Workflow)" — Cole
  Medin, youtube.com/watch?v=Ya51a1EJPZk. More in claude-code-video-hunt.md (20-30 verified
  videos).

## Data-viz / motion patterns ranked by wow÷effort (from motion_graphics_pattern_catalog.md)
1. Count-up numbers (effort 1) 2. SplitText kinetic type 3. Line draw-on 4. Bar chart race
5. Map route/connection-path draw (Johnny Harris signature) 6. Choropleth reveal 7. FLIP
morph transitions. Headless path: D3/GSAP/Chart.js/ECharts in HTML → Puppeteer/Playwright
frame grabs → ffmpeg; ECharts has official server-side SVG (no browser needed).
