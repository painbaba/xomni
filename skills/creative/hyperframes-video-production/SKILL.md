---
name: hyperframes-video-production
description: Use when producing videos with HeyGen HyperFrames.
---

# HyperFrames Video Production

HeyGen HyperFrames (github.com/heygen-com/hyperframes, npm `hyperframes`) renders
video from HTML: a composition is an HTML file whose DOM declares timing with
`data-*` attributes, driven by a paused GSAP timeline. Works for anything from a
10s title card to a 30+ minute documentary. This skill is the production
playbook proven end-to-end on a 33-minute documentary (47 scenes, 8 chapters).

## When to use

- Any "make a video" request where HyperFrames is the stack (default unless the
  user picks another framework)
- Long-form / narrated / multi-scene pieces (docs, explainers, trailers)
- Any render that needs narration (edge-tts), music beds, or SFX

## The production pipeline (proven end-to-end)

1. **Research first, in parallel.** Dispatch 3 leaf subagents (bio/career, the
   core event, systemic context) with strict instructions: named-publication
   sources only, inline URLs + dates, UNVERIFIED tags, allegations vs
   established facts kept apart. Agents should save notes to disk (parent
   reads them even if a subagent hits its iteration cap and loses its summary).
2. **Scaffold:** `npx hyperframes init videos/<project> --non-interactive
   --example=blank --skill=general-video` (general-video for anything >3min).
3. **Write the script as chapter specs** (JSON): 8 chapters × ~6 scenes ≈ 40
   min. Each scene: kind (divider/title/stat/quote/timeline/list/headline/
   endcard), on-screen text, and narration text. Target ~60-70 words/min of
   runtime for documentary pacing (21 min voice in a 33 min doc = dense).
4. **TTS narration:** batch edge-tts per scene → mp3 + durations.json (see
   `scripts/tts_batch.py`). Scene duration = narration duration + padding
   (10s for docs, 1.2s for fast trailers) — derive from measured audio, never
   guess.
5. **Generate chapters:** `scripts/gen_chapter.py` turns a spec JSON into a
   standalone composition HTML (clips + narration/music/SFX audio elements +
   deterministic GSAP timeline with per-kind entrances/exits).
6. **Validate:** `npx hyperframes check` (project-scoped, validates index.html
   AND compositions/*.html). Then render each chapter file separately:
   `npx hyperframes render -c compositions/chXX.html --quality high -w 3
   --output renders/chXX.mp4`.
7. **Render in parallel pairs** (2 at a time, ~3 workers each) — 8 chapters ≈
   60-90 min on a 12-core/16GB Windows box. See `scripts/render_all.sh` pattern.
8. **Concat:** ffmpeg -f concat -c copy (chapters share encoder settings, lossless).
9. **Verify:** ffprobe codecs/duration, `volumedetect` for levels, and a
   speech-band check (highpass 4kHz on a narration window vs a music-only
   window — narration must dominate) to prove the audio mix landed.

User's default mode: **full automation** (flow: automation, storyboard: no,
no brief questions). Parallelize aggressively (subagents for research, renders
in pairs, trailer alongside main doc when asked). If the user pivots topics
mid-build (they do), park research artifacts + the pipeline and re-point it —
the tooling is topic-agnostic.

## HyperFrames contract essentials (verified)

- Root: `<div data-composition-id data-start="0" data-width data-height
  data-duration>`; timed children need `class="clip"` + `data-start` +
  `data-duration` + `data-track-index`, and must be DIRECT children of root.
- Timeline: `gsap.timeline({paused:true})` registered synchronously on
  `window.__timelines["<id>"]` (key = root data-composition-id).
- Entrances: `tl.fromTo(el, {autoAlpha:0, y:...}, {...})` — never pair a CSS
  initial transform with a tween on the same property (lint rejects).
- Count-ups: tween a proxy `{v:0}→target` with onUpdate writing
  `Math.round(v).toLocaleString("en-IN")` — deterministic (seek-driven).
- No `<br>` in body text; transformed elements must be block-level + sized;
  no `repeat:-1`; no Math.random/Date.now.
- Auto-fit headline font size by plain-text length (~22 chars → 118px, 30 →
  96px, 40 → 80px, else 68px) or the layout check flags overflow.
- **Media srcs resolve PROJECT-ROOT-relative**, even from compositions/chXX.html:
  `src="narration/a1s1.mp3"`, `src="assets/beds/bed-tense.wav"`.
- Audio: separate `<audio>` elements (data-start/duration/track-index/volume);
  multiple elements MIX into the render. Volume ducking: `tl.to("#music",
  {volume:0.22})`. Give each SFX type its own track index (narration=10,
  music=11, whoosh=12, riser=13, boom=14, tick=15) or lint flags overlaps.

## Pitfalls (each cost real debugging time)

- **Windows `spawn EFTYPE`** ("not a valid application for this OS platform"
  from PowerShell despite valid PE32+ x64 headers) = corrupt cached
  chrome-headless-shell in `%USERPROFILE%\.cache\puppeteer\chrome-headless-shell
  \win64-<ver>\`. Fix: delete that version dir, then `npx hyperframes browser
  ensure` — a working build lands in `%USERPROFILE%\.cache\hyperframes\chrome\`.
  `browser path` keeps resolving the corrupt copy until it's deleted.
- **Cross-file audio warnings are false positives.** When compositions render
  independently via `-c`, lint's `duplicate_audio_track` /
  `overlapping_clips_same_track` compare audio across FILES as if one timeline
  (each file's t=0 collides). Check passes with 0 errors anyway; the warnings
  are noise. Prove correctness with one real render + audio-band analysis.
- **`check`/`lint` are project-scoped** (take a dir, not a file). For a single
  composition, either copy it to index.html for check, or rely on
  `render -c` as the functional gate (runtime errors surface there).
- **wpm varies 90-170 by text at the SAME edge-tts rate** — always measure
  with ffprobe and derive scene durations from real audio.
- **git-bash/MSYS**: `node <path>` with `$HOME`-prefixed args gets mangled to
  `C:\c\Users\...` — use native `C:/Users/...` paths. Projects with
  `"type": "module"` need `.cjs` for CommonJS test scripts.
- **edge-tts argparse**: rate/pitch values starting with `-` MUST use the
  `=` form (`--rate=+8%`), never `--rate -8%` (argparse eats the value).
- **Batch TTS subprocesses**: use `sys.executable` in scripts, not `"python"`
  (PATH may resolve a different interpreter than the one running the script).

## TTS with edge-tts

- `python -m edge_tts --voice en-US-ChristopherNeural --rate=+0% --text "..."
  --write-media out.mp3`
- Documentary narrator: en-US-ChristopherNeural (male, authoritative).
  Fast trailer pace: rate +12%. No paid keys needed; free + offline-friendly.
- Batch via `scripts/tts_batch.py manifest.json outdir [--voice ...]
  [--rate +8%]` → mp3s + durations.json.

## Music & SFX sourcing (CC0, verified)

- archive.org advancedsearch works: filter
  `licenseurl:"http://creativecommons.org/publicdomain/zero/1.0/"` + mediatype
  audio + title terms; files at `archive.org/download/<id>/<file>`.
- **Jamendo mirrors on archive.org are usually BY-NC-ND — unusable for
  monetized YouTube.** Check licenseurl before trusting a title.
- Pixabay/Bensound/Openverse searches are walled or dry via curl — don't burn
  time; the 84MB CC0 drone (8hertzAmbientLoopDrone) + synthesized SFX covers a
  whole documentary.
- Synth SFX with ffmpeg (no licensing): boom (80Hz sine + fades), whoosh (pink
  noise + lowpass + fades), riser (sine with volume ramp), tick (1kHz, 80ms).
- Trailer bed trick: amix the tense drone with a gated 160bpm kick
  (`aevalsrc=if(lt(mod(t\,0.375)\,0.12)\,0.8*sin(2*PI*52*t)*exp(-14*mod(t\,0.375))\,0)`).

## Documentaries about real people

See `references/real-person-documentaries.md` — legal-care rules that kept a
raids documentary defensible: sourced-only claims, attribution on screen,
"as reported" framing, allegations vs clean chits separated.

## Files

- `scripts/tts_batch.py` — manifest → edge-tts mp3s + durations.json
- `scripts/gen_chapter.py` — chapter spec JSON → standalone composition HTML
- `templates/chapter-spec.json` — example scene spec (all kinds + audio flags)
- `references/real-person-documentaries.md` — sourcing/attribution rules
