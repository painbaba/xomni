---
name: video-documentary-production
description: >
  Use when building long-form narrated videos (10-40 min).
---

# Video Documentary Production

Class-level workflow for building long-form (10–40+ min) faceless documentaries — kinetic
typography, data-viz, narration, music beds, SFX. Complements the vendor `hyperframes-*`
skills: read `/hyperframes` + `/hyperframes-core` for the composition HTML/GSAP contract;
this skill is the production system AROUND it (audio pipeline, chapter architecture,
research discipline, orchestration).

Proven end-to-end: 8 chapters × 6 scenes = 33 min documentary rendered with voice, music,
SFX (Mundhe/India FDA raids, Aug 2026).

## Architecture (the core pattern)

One project, **standalone chapter compositions** (NOT sub-compositions):

- `chapters/chXX.json` — chapter spec: scenes with `kind`, visual fields, `narration` id
  (scene kinds: `divider, title, stat, quote, timeline, list, headline, endcard`)
- `scripts/gen_chapter.py` — spec + narration durations → `compositions/chXX.html`
- Render each file independently: `npx hyperframes render -c compositions/chXX.html --quality high --output renders/chXX.mp4`
- Run **2 renders in parallel** (`-w 3` each), verify each, then `ffmpeg -f concat -safe 0 -i list.txt -c copy documentary-full.mp4`

Scene durations are **derived from actual narration length** (narration + 10s breathing,
min 40s) — never hardcoded. Total runtime = sum of scenes; ~50-65% narration density is
good documentary pacing.

## Short-form / trailer mode ("fast": true — for 1-3 min pieces)

The project-local `tools/gen_chapter.py` (videos/mundhe-documentary) supports
`"fast": true` in the chapter spec: scene duration = `max(3.0, narration + 1.2)`s instead
of the long-form min 40s. Proven: 13-scene 62s trailer (trailer.json → 63.86s trailer.mp4)
and the 8-scene 54s UPI demo (videos/upi-demo, Aug 2026). Recipe that works:

- TTS manifest at `rate: "+12%"` (trailer punch); one punchy line per scene, 3-9s each
- Scene kinds: title (hook, riser+boom) → stat with `count:true` (boom) → headline
  (masthead+deck, boom) → list (staggered rows) → quote (boom) → endcard
- Music: `bed-trailer` + riser on scene 1 + boom on impact stats; whooshes between scenes
  are auto-added for i>0
- ⚠️ The SKILL.md-shipped `scripts/gen_chapter.py` does NOT have the fast flag — copy the
  project-local version (videos/mundhe-documentary/tools/gen_chapter.py, which has
  `fast = spec.get("fast", False)` / `max(3.0, ...)`), or add it yourself.
- ⚠️ `npx hyperframes check` FAILS with "No composition found / No index.html file found"
  unless a root `index.html` exists — create a 6s index card (data-composition-id="main",
  data-duration="6") even when all real content renders from `compositions/`. Chapters
  still render via `npx hyperframes render -c compositions/chXX.html --output renders/chXX.mp4`.

## Narration (edge-tts, free, high quality)

- Documentary voice: `en-US-ChristopherNeural` (male, authority). Female alt: `en-US-AriaNeural`.
- Default rate `+0%` ≈ 120-155 wpm depending on text (edge voices vary by sentence structure).
- `scripts/tts_batch.py`: manifest `[{"id","text"}]` → mp3s + `durations.json` (ffprobe).
- Pitfalls (all hit in practice):
  - The batch script's subprocess must use `sys.executable`, not `"python"` — PATH python can
    differ from the interpreter running the script (uv-managed pythons).
  - `--rate -12%` breaks argparse (value starts with `-`) → use `--rate=-12%` = form.
  - Spell tricky numbers for TTS ("one point six lakh litres", "eleven hundred and thirty-one").
  - `edge-tts` needs `pip install edge-tts` in the interpreter you run (not necessarily the shell default).
  - **edge-tts license = LGPLv3** (only `src/edge_tts/srt_composer.py` is MIT — verified in repo LICENSE, Aug 2026). Fine as a CLI pipeline tool (generated audio isn't a derivative work), but it's an unofficial wrapper on Microsoft Edge's online service → no commercial guarantee, service can change/be throttled anytime. For monetized-at-scale narration, have a license-clean fallback ready (Kokoro — see below).

### Paid TTS upgrade paths (live-verified Aug 2026)

Monetized channels → edge-tts has no commercial guarantee; paid engines add license + quality:

- **ElevenLabs** (`elevenlabs.io/pricing`): Free $0/10k credits (~10 min, no commercial license) · Starter $6/30k (~30 min, +Commercial License, IVC) · Creator $22/121k (~2 h, +PVC; annual ≈ $18.33/mo) · Pro $99/600k (~10 h, +44.1kHz PCM & 192kbps). API track (`/pricing/api`): **$0.10 per 1K chars** Multilingual v2/v3, $0.05 Flash/Turbo; **40,000-char per-request cap**; long-form continuity via `previous_request_ids`/`next_request_ids` (≤3 each) + `seed` + `apply_text_normalization`.
- **OpenAI gpt-4o-mini-tts**: **~$0.86–1.30 per 60 min** ($12/1M audio output tokens; 1 token/50 ms output ≈ 1,200 tok/min; 4096-char/request cap → ~15 requests per hour); 13 voices (`marin`/`cedar` recommended), promptable `instructions` for documentary tone/accent; custom voices ≤30 s sample, sales-gated. `openai.com/api/pricing` is Cloudflare-walled — use `developers.openai.com/api/docs/pricing.md` instead.
- **Rule of thumb**: 60 min ≈ 60k chars ≈ $6 ElevenLabs API / ~$1 OpenAI / $0 edge-tts. Full verified tables + model IDs + cloning (IVC/PVC) + docs-fetch tricks: `references/tts-providers-2026.md`.

### Free TTS tiers + local open-source TTS (live-verified Aug 2026)

Full data, quotes, and URLs in `references/free-media-stack-2026.md`. Short version:
- **Cloud free**: ElevenLabs 10k credits/mo ≈ 10 min (NO commercial license on free) · OpenAI **no free tier** · Google Cloud TTS **0–4M chars/mo free per model** (WaveNet/Standard 4M; Neural2/Chirp3 HD/Studio/Polyglot 1M; billing card REQUIRED; ~1M chars ≈ 1,000 min ≈ 16.6 h narration/mo) · Azure Speech F0 0.5M chars/mo · AWS Polly neural 1M chars/mo + standard 5M/mo, first 12 months.
- **Local (free forever, Windows)**: **Kokoro** — Apache-2.0, 82M params, 54 voices/9 langs, real-time CPU, `pip install kokoro` + espeak-ng `.msi`; deep males `am_michael`/`am_fenrir`/`am_puck` (US), `bm_george` (UK). **Best free-forever default after edge-tts.** · **Chatterbox** — MIT, Multilingual V3 0.5B (23+ langs), clone a deep male from a ~10 s ref clip, GPU recommended (Nano runs CPU 3× realtime on 8 cores) · **Piper** — MIT (archived Oct 2025) → piper1-gpl is **GPL**; ~45 langs, v1.6.0 ships a Windows wheel; fast but flatter · **MeloTTS** — MIT, 6 langs, 1 voice/lang · ⚠️ **Coqui XTTS-v2 = Coqui Public Model License = NON-commercial → do not use for monetized YouTube** (repo also unmaintained).

## Audio layers (all proven to mix in render)

- `<audio>` elements work at any depth; **multiple overlapping tracks mix** into the render
  (verified by speech-band energy check: narration window ≈17× the highpass-4k RMS of music-only).
- Track allocation: narration=10, music=11, SFX=12..15 — **one track index per SFX type**.
  Same-track overlapping SFX = lint error `overlapping_clips_same_track`.
- Volume: static `data-volume` (music ≈0.22); duck via timeline `tl.to("#music",{volume:0})` — never swap data-volume for fades.
- **Media `src`s are PROJECT-ROOT-relative even from `compositions/` files** (e.g. `narration/a1s1.mp3`, `assets/beds/bed-tense.wav`).

## Music & SFX (CC0 / synthesized)

- CC0 music: `https://archive.org/advancedsearch.php?q=...` with
  `licenseurl:"http://creativecommons.org/publicdomain/zero/1.0/"` AND `mediatype:audio` (+ title terms).
  Archive.org items give direct download URLs (`https://archive.org/download/<id>/<file>`).
- **archive.org has purpose-built TRAILER cuts** — e.g. Frank Schlimbach "Dark Legacy 60 sec"
  (`archive.org/details/monster-in-the-closet-main`, exactly 60s, riser+release built in, stem
  variants incl. No-Riser/No-Drums/Underscore). Caveat hit in practice: item license field says
  CC BY 4.0 but the description says "Free for personal use" — verify with the rights holder
  before MONETIZED use, or fall back to Incompetech CC BY (e.g. "Rising", cut to length).
- Long drone items (e.g. 75-min ambient) → cut 600s beds at different offsets with different
  lowpass filters for dark/tense/calm moods.
- Synthesize SFX with ffmpeg (boom/riser/whoosh/tick) — exact commands in
  `references/pipeline-recipe.md`. Deterministic, no licensing.
- License flags: CC0 = safe for monetized YouTube; CC BY = attribution required; jamendo
  items on archive.org are often BY-NC-ND (unusable) — check `licenseurl` first.
- **Monetization-safe music/SFX sources (all live-verified Aug 2026, details in
  `references/free-media-stack-2026.md`):** YT Audio Library (explicitly monetizable for YPP,
  Content-ID-safe, filter "Attribution not required"; includes SFX tab) · archive.org CC0
  (**75,512 audio items** — verified live count) · Incompetech CC BY 4.0 (monetize OK with
  credit; working URLs are `incompetech.com/music/royalty-free/{faq,licenses,music}.html`) ·
  FMA (CC per track — check; BY-NC tracks unusable) · freesound (CC0 / CC BY / CC BY-NC — filter
  CC0 for docs) · ⚠️ Suno free (50 credits/day) and Udio free (10 credits/day) are **both
  non-commercial** on free tiers — useless for monetized channels; AI music only via paid
  ($8 Suno Pro / $10 Udio Standard).

## Assembly & motion-graphics layers (FREE stack, live-verified Aug 2026)

HyperFrames renders scene-level compositions; the assembly + motion layers around it are all free/OSS. Verified matrix + agent recipes + URL index: `references/free-assembly-motion-stack-2026.md`. Quick map:

- **Assembly:** FFmpeg (LGPL-2.1+/GPL-2+ — "not available under any other licensing terms") stays the backbone; **MoviePy** (MIT, `pip install moviepy`, pure-Python wheel) is the programmatic timeline/orchestration layer an agent drives; **MLT/melt** (LGPL-2.1) is the headless multi-track XML engine — Shotcut (GPL-3.0, GUI-only) renders via a `melt` subprocess (source-verified), so `.mlt`/Shotcut projects render headlessly with `melt file.mlt -consumer avformat:out.mp4`; **libopenshot** (LGPL-3.0-or-later, Python bindings, Windows) is the no-GUI alternative with multi-layer compositing; **DaVinci Resolve 21 Free = human finishing only** — proprietary freeware, GUI must be running, and free-tier scripting access is disputed (pydavinci README: "Free version does not allow API access" — verify on your install; even when it works it's not headless).
- **Motion:** **Manim** (MIT, `pip install manim`, Windows-supported) for explainers — agent generates scene code, `manim render` CLI outputs mp4/frames; **Apache ECharts SSR** (Apache-2.0) is the agent-friendly data-viz (official server-side SVG rendering, no browser); D3 (ISC)/Chart.js (MIT)/GSAP ("100% free for all users" per gsap.com/pricing — no-cost commercial license, NOT OSI) render via headless Chrome/Playwright frame grabs; **Motion Canvas (MIT) has NO headless render** (browser-bound, confirmed in docs) — human-only; **Remotion free license = individuals / for-profit ≤3 employees / non-profits** (commercial use OK for free licensees) — paid company license above that, so only free if our org qualifies.
- **Subtitles:** **faster-whisper** (MIT, ~4× faster than openai-whisper, Windows wheels via ctranslate2 win_amd64) is the default engine; openai-whisper CLI (`whisper file --model turbo --output_format srt`), whisper.cpp (`-osrt`, CPU-only, Windows MSVC+MinGW), whisperX (BSD-2-Clause, word-level timestamps + diarization); ⚠️ **whisper-timestamped is AGPL-3.0 — avoid**. Burn-in stays `ffmpeg -vf "ass=subs.ass"`.

## Kinetic captions & source chips (implementation — verified in the ULTIMATE cut, Aug 2026)

No Whisper needed — the script IS the transcript; generate word-by-word captions directly
from scene `text` fields. All of this is implemented and lint-clean in the project-local
`tools/gen_chapter.py` (videos/upi-demo) — copy that file for new projects.

- Caption bar = timed `.clip` on **track 3** (above text track 2):
  `<div id="cap-{sid}" class="clip" data-start data-duration data-track-index="3">` containing
  `.captions` (bottom-center flex of `.w` word spans; 42px Segoe UI 600, white, text-shadow
  `0 2px 10px rgba(0,0,0,.85)` for readability over footage) + optional `.chip` (bottom-left,
  24px, 0.30em letter-spacing, uppercase gray — source attribution).
- Word reveal: `words = text.split()`; per word i: `tl.fromTo(word, {autoAlpha:0,y:10},
  {autoAlpha:1,y:0,duration:0.14,ease:"power2.out"}, cap0 + i*step)` with
  `cap0 = sceneStart + 0.6` and `step = max((sceneDur - 1.4)/nwords, 0.18)`.
- Gold active word (the karaoke highlight): `tl.call(() => {words.forEach(w =>
  w.classList.remove("active")); words[i].classList.add("active");}, null, t)` — classList
  toggles are deterministic and allowed (not animating display/visibility, not on `.clip`).
- Count-up tick SFX: 6× `assets/tick.wav` (0.08s, **track 15**, `data-volume=0.45`) at
  `sceneStart + 0.95 + k*0.3` during the count (ticks non-overlapping → no same-track lint).
- Source chips on stat/data scenes: scene-level `"chip": "NPCI · As reported"` field → `.chip`
  div inside the same caption clip (no extra track).
- These pass `npx hyperframes check` with 0 errors; track-density warnings are informational.

## Research discipline (real people / legal sensitivity)

- Parallel subagents per track (bio / events / systemic context), each required to return
  facts with outlet + date + URL, `UNVERIFIED` tags, and allegations-vs-established split.
- Script uses "as reported by <outlet>, <date>" framing throughout; single-source claims
  flagged; never dramatize accusations. This is non-negotiable for real-person docs.
- **Monetization/strategy planning for a doc channel** (RPM by niche, video length, mid-roll
  economics, retention/CTR benchmarks, inauthentic-content policy): load the `web-research`
  skill's `references/youtube-creator-economy-2026.md` (verified Aug 9, 2026) — complements
  this skill's production-side `references/engagement-research-2026.md`.

## Verification

- `npx hyperframes check` (project-scoped, takes a DIR not a file — but it scans
  `compositions/*.html` too). `npm run check` in the project.
- **Known false positive**: `duplicate_audio_track` warnings comparing audio ACROSS chapter
  files (each starts at t=0). Chapters render independently → ignore; the check itself
  passes 0 errors.
- `timeline_track_too_dense` = informational, ignore for 5-6 scene files.
- Post-render: `ffprobe` duration/codec (expect h264+aac), `ffmpeg ... volumedetect`
  (mean ≈ -19 to -25 dB with narration), and the speech-band check to prove narration is
  audible over the bed.

## Pitfalls & Windows notes

- `check` rejects a file path ("Not a directory") — run from project root.
- Corrupt puppeteer chrome cache → `spawn EFTYPE` — fix documented in the vendor
  `hyperframes-cli` skill (`references/doctor-browser.md`).
- git-bash mangles `$HOME/.claude/...` paths for node/python → use native `C:/Users/...`.
- git-bash temp: `/tmp` may not exist/write → `curl -o /tmp/...` dies with "No such file"; use `~/<dir>/` instead.
- Projects' package.json has `"type": "module"` → CommonJS test scripts need `.cjs`.
- Headlines: auto-fit font size by plain-text length (118→96→80→68px) — long headlines at
  118px overflow 1920×1080 with 170px padding.
- Count-ups: `Math.round(v).toLocaleString("en-IN")` for Indian digit grouping (1,60,000).
- TTS/rate/edge quirk: wpm varies 90-175 by text; always measure actual durations and drive
  scene length from them, don't estimate.
- **VP9/VP8 webm footage DROPS FRAMES in headless render** → the coverage gate aborts the
  render ("video captured 173 of expected 304 frames", threshold 95%,
  `HF_VIDEO_COVERAGE_THRESHOLD=0` disables it but ships BLANK clips — don't). ALWAYS transcode
  footage to h264 mp4 before rendering:
  `ffmpeg -y -i in.webm -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -an -movflags +faststart out.mp4`
  (h264 decodes cleanly; also shrinks 100MB+ webms). Footage scenes render ~3.5x slower than
  stills — pre-trim clips to scene length for long-form.
- **Wikimedia big-file DOWNLOADS need the same User-Agent as the API** — without it,
  upload.wikimedia.org returns ~2KB HTML error pages that save as ".webm"/".ogv" (check with
  `file`/ffprobe; 2254 bytes = error page, not media). Retry with
  `curl -A "Mozilla/5.0 ... HermesResearch/1.0" --retry 3 --retry-delay 5` + sleep ~8s between
  large files (throttling). For stills, the thumbnail URL pattern
  (`.../thumb/<hash>/<File>/1920px-<File>`) gives fixed-width JPEGs and dodges filename-mismatch
  404s that the bare File URL hits.

## Engagement specs (verified Aug 2026 — details + URLs in references/engagement-research-2026.md)

Retention is won or lost in the first 30s (≥70% retention at 30s = good hook; <50% = rebuild).
Verified production specs: change the visual every 3–5s inside stat/data scenes (eye absorbs ~1
idea per 2–3s); cold-open scene 1 with the payoff, value promise ≤15s, silent start (no music bed
first ~5s — a music intro cost +5.8% 15s-retention vs straight-to-vocal); b-roll/alternate visual
coverage 35–50% of runtime (+15–25% watch time, irrelevant footage hurts); tension cues
(risers/booms/stingers) at chapter boundaries, not constant beds under narration (music helps
retention only pre-roll); chapters ≥3 with 00:00 first, aligned to visual dividers; keep docs
≤ ~25 min (−11% engagement past 30 min). Count-ups/charts exploit 60,000× faster visual
processing — land the visual before the narrator finishes the sentence.
**Narration rate for scene/spec math: 125–150 wpm (conversational) / 150–160 wpm (documentary
register) — 5 min ≈ 625–750 words, 10 min ≈ 1,250–1,500 words. APV benchmark bands by length
(<5 min 50–70% / 5–15 min 40–55% / 15–30 min 30–45% / >30 min 25–35%): see the Aug 10 addendum
in `references/engagement-research-2026.md` for the full second-verified-pass table + URLs.**

## AI video generation layer (b-roll / hero shots — verified Aug 2026)

Full data, pricing, verdicts, and report paths in `references/ai-video-generation-2026.md`.
Quick map: **Sora 2 is DEAD** (app Apr 2026, API shut down Sep 24 2026 — never build on it).
Cloud per-second: Kling 3.0 $0.084–0.168/s (4K, native audio — per-dollar king), Runway
Gen-4.5 $0.12/s (best cinematic realism, MCP for agents), Veo 3.1 fast/lite $0.05–0.12/s
(8s clips, native audio), Luma Ray 3.2 $0.06/s 720p. **Local FREE: ComfyUI + Wan 2.2**
(Apache-2.0, commercial OK, 720p/24fps ~5s clips, /prompt API + official MCP for agent
automation). Render-core verdict: HyperFrames stays agent-native; Remotion wins for
data-heavy/react flows (audio mixing, caption SDK, parallel render) at the cost of React/TS
re-authoring + license >3 employees; Motion Canvas has NO headless render. Agent pipelines
to copy: yopiesuryadi/video-doc-pipeline (Claude Code skill, raw clips → published doc in
~1 day) and OpenMontage (46k★, "the coding agent IS the orchestrator" — skills + YAML
manifests). USER PREFERENCE: free-first — local/CC0 over paid APIs wherever quality allows.

## Avatar / presenter scenes (FREE path — verified Aug 2026)
Pro narrator formula = avatar presenter segments + cinematic b-roll + motion graphics. User
rejected paid HeyGen API; the free winners: **MuseTalk 1.5** (local, MIT/commercial-safe,
officially runs on RTX 3050 Laptop 4GB fp16 — this user's exact GPU) and **Tavus Developer
Free** (cloud, 5 min/mo API, no watermark — the only recurring free avatar API). ETHICS: never
lip-sync real identifiable people — generate a SYNTHETIC face and zoompan it into a
base video. Portrait QUALITY matters to this user ("best in quality, best in assets"):
use the high-res ladder — FLUX.1-schnell official HF Space (1536px, ZeroGPU quota) over
Pollinations (caps at 768px), mirror to catbox.moe — details in
`references/musetalk-local-avatar.md`. Full verdict table + install recipe (Python ≤3.11 trap,
**torch 2.1.0+cu121 — NOT cu128**; mmcv/mmdet/mmpose have **NO Windows wheels** —
skip the whole mmpose stack, the mediapipe FaceMesh bypass is REQUIRED (see ref),
model downloads, inference cmd, splice pattern): `references/free-avatars-2026.md` +
`references/musetalk-local-avatar.md`.
**USER VERDICT (2026-08-10): the talking-head result on 4GB was REJECTED** ("its fucked
up … without approach was best") — do not default to lip-sync on this GPU. The approved
look: a **static synthetic-portrait host card that POPS UP at narration moments**
(circular portrait + name chip, slide/scale/fade in at narration start, out at scene end;
u1 hook + u8 endcard; bottom-right, clear of centered captions). Remotion impl = AvatarPop
component (interpolate-driven transform/opacity, `staticFile` portrait) — pattern in
`references/remotion-migration.md`. MuseTalk stays as the engine ONLY if a future
higher-quality source face changes the outcome.

## Support files

- `references/ai-video-generation-2026.md` — AI video tool layer: per-second pricing
  (Kling/Veo/Runway/Luma), Sora death notice, Wan 2.2 local recipe, render-core verdict
  (HyperFrames vs Remotion vs Motion Canvas), Claude Code video pipelines + repos, data-viz
  pattern ranking, paths of all full swarm reports.
- `references/tts-providers-2026.md` — live-verified TTS provider data: ElevenLabs tiers/API rates, long-form stitching, models, voice cloning, OpenAI gpt-4o-mini-tts, edge-tts, 60-min cost model, docs-as-markdown fetch technique.
- `references/free-media-stack-2026.md` — live-verified FREE voice+music+SFX sources for monetized docs: cloud free tiers (ElevenLabs/OpenAI/Google/Azure/Polly), local TTS (Kokoro/Chatterbox/Piper/XTTS/MeloTTS + Windows install), music licensing (YT Audio Library/FMA/Incompetech/archive.org CC0/Suno/Udio), SFX (freesound), working URLs + 404 pitfalls, definitive stack table.
- `references/engagement-research-2026.md` — verified engagement/retention knowledge bank with
  source URLs (hooks, pacing/shot data, b-roll, sound, chapters, structure, faceless stats).
- `references/free-assembly-motion-stack-2026.md` — live-verified FREE assembly + motion-graphics + subtitle stack for the doc pipeline (Aug 9, 2026): per-tool license/Windows/headless/agent-fit matrix (FFmpeg, MoviePy, Shotcut, MLT/melt, OpenShot/libopenshot, DaVinci Resolve Free, Manim, GSAP, D3, Chart.js, ECharts SSR, Motion Canvas, Remotion, Whisper family), agent recipes, and the full LIVE-VERIFIED URL index. Load for any free-tool-for-assembly/motion/subs choice or pipeline gap-fill.
- **B-roll / footage sourcing (stock APIs, free AI-video tiers, archival, Ken-Burns stills):** load the `web-research` skill's `references/free-footage-playbook-2026.md` (verified Aug 9, 2026) — Pexels/Pixabay/Coverr/Mixkit API limits, Videvo+Mazwai→Magnific consolidation, Veo/Kling/Runway/Pika free-tier reality, Prelinger/NASA keyless archival, and the ranked $0/month combo. Monetization rule: stock + public-domain + local Wan 2.2 (Apache-2.0) only; Kling/Pika free tiers are explicitly non-commercial.
- `references/mcp-video-production-2026.md` — MCP servers for video: verdicts (Remotion MCP DEPRECATED → Agent Skills; ElevenLabs MCP = the working voice path; kinocut = guardrailed ffmpeg), ranked repos by pipeline stage (elevenlabs-mcp/davinci-resolve-mcp/blender-mcp/comfy-mcp), Hermes `mcp_servers:` wiring recipe (config.yaml schema, `mcp_<server>_<tool>` naming, `pip install mcp`, npx.cmd on Windows, `hermes mcp add`), and the verified YT references. Load before wiring any video MCP. ⚠️ `hermes mcp add` prompts "Enable all N tools? [Y/n]" and CANCELS silently on non-interactive runs — always pipe `echo Y | hermes --accept-hooks mcp add <name> --command npx --args -y <pkg>`; verify with `hermes mcp list` (new tools load in the NEXT session).
- `references/free-footage-sourcing.md` — the NO-KEY footage recipe actually executed Aug 2026 (UPI demo): Wikimedia Commons API (UA header or 403, 429 backoff, videoinfo, strip `?utm`), verified India/UPI clip table (incl. 1929 Bombay archival), bitmap-search → Ken-Burns STILLS fallback for semantic matching (v3), stills layer lint contract (img CAN nest in timed clips, untimed scrim child), render-cost reality (video scenes ~3.5x slower), archive.org Prelinger, curl+transcode for HyperFrames, and the footage-layer composition pattern (muted video clip + scrim + Ken Burns under kinetic type).
- `references/remotion-migration.md` — CONCRETE Remotion upgrade recipe (working ref: videos/upi-remotion): scaffold + version-pinning (npm view — guessed versions ETARGET), `<Audio>` has no `from` (wrap in `<Sequence from>`; startAt trims), `Easing.power2` doesn't exist, `remotion skills add` spawn EINVAL on Windows → `npx --loglevel=error skills@1.5.20 add remotion-dev/skills --yes`, manual crossfade via overlapping Sequences (avoid TransitionSeries total math), staticFile/public layout, patterns carried from the HyperFrames cut (Ken Burns, count-up, word captions, audio offsets).
- `references/remotion-map-technique.md` — WORKING animated country-map recipe (UPI trailer, Aug 2026): dev-time d3-geo + world-atlas topojson → precompiled SVG path + projected city coords (fitSize 1200×1200), stroke-dashoffset draw-on (no path-length math needed), pulse-dot pattern, scene wiring. Also indexes the swarm's other pro techniques (bar-chart race = pure React spring, gradient text, wipe/glitch transitions) + MoSidd's Vox-style tutorial.
- `scripts/verify-remotion.py` — reusable ad-hoc verification for Remotion projects after edits: `python3 scripts/verify-remotion.py <proj> [out.mp4]` → tsc + literal staticFile refs (template-literal refs checked by prefix dir — avoids the false-positive regex trap) + optional ffprobe artifact specs. Use instead of hand-writing a fresh check each time.

## User expectation — footage, not just graphics (2026-08-09)
Text/graphics-only output was explicitly REJECTED: "we need overlays, videos… very engaging stuff". The target look = REAL footage backgrounds with dark scrims + Ken Burns motion, kinetic type / stat count-ups ON TOP (Johnny Harris / Fern style). B-roll coverage 35-50% of runtime is the expected baseline, not optional garnish; text-only cards are acceptable only as short beats between footage scenes. Same lesson applies when reviewing a render: a pure graphics cut gets sent back.

## User expectation #2 — semantic match + the pro pipeline (2026-08-10)
Second rejection: footage that doesn't match the narration beat ("lots of clip don't match")
is worse than no footage. EVERY scene's visual must match its beat — per-scene topic search,
and Ken Burns STILLS as the fallback when no matching video exists (see
`references/free-footage-sourcing.md` — bitmap-search + img-layer pattern). Target shape the
user wants next ("we have to be the best"): NOT footage-everywhere — the pro hybrid used by
top channels = avatar presenter segments (HeyGen avatars — we're on the HeyGen stack) +
semantically-matched b-roll + motion graphics + KINETIC CAPTIONS (word-highlight; the script
IS the transcript, no Whisper needed) + pro overlays (lower-thirds with attribution, data
callouts, picture-in-picture) + synthesized transitions/SFX + OWN generated assets (local
ComfyUI/Wan once GPU headroom exists) instead of stock. Research-driven wiring (ElevenLabs
MCP, Kinocut, davinci-resolve-mcp — config recipes in the MCP hunt reports) is the enabler
the user is betting on.
- `references/pipeline-recipe.md` — full session recipe: exact commands, chapter-spec shape,
  ffmpeg SFX synthesis, archive.org queries, render orchestration, verification probes.
- `scripts/tts_batch.py` — batch edge-tts generation + durations.json (sys.executable-safe).
- `scripts/gen_chapter.py` — chapter spec JSON → standalone HyperFrames composition
  (auto-fit headlines, en-IN count-ups, narration-derived durations, SFX track separation).
