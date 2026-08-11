---
name: hyperframes-video-pipeline
description: >
  Build HyperFrames videos: promos, explainers, documentaries.
---

# HyperFrames Video Pipeline

HyperFrames renders deterministic MP4s from HTML compositions (npm pkg `hyperframes`, projects in `C:\Users\HP\videos\`). The vendor skills (`hyperframes`, `hyperframes-core`, `hyperframes-cli`, `faceless-explainer`) are the framework contract — read them for `data-*` attributes, clip rules, determinism, and CLI commands. THIS skill is the orchestration layer: how to actually produce a finished narrated video end to end, with the pitfalls that cost real time.

## Pipeline stages (proven order)

1. **Research** — for factual videos, dispatch parallel `delegate_task` subagents (max 3). Tell each to SAVE notes to a file on disk (e.g. `C:\Users\HP\<topic>-research.md`) and to mark unverifiable claims `UNVERIFIED` — subagents can hit iteration caps and lose their summary; the on-disk file survives. For Indian news: Google News RSS is the most reliable curl-able source: `curl -s -A "Mozilla/5.0" "https://news.google.com/rss/search?q=<query>&hl=en-IN&gl=IN&ceid=IN:en"`.
2. **Script** — one narration text block per scene (~120 words ≈ 45s at default edge-tts rate). Keep facts attributed ("as reported by X") for real-person/litigation topics; distinguish allegations from established facts on screen.
3. **TTS** — batch edge-tts per scene → mp3 + durations.json (see `templates/tts_batch.py` and `references/tts-and-audio.md`).
4. **Music/SFX** — archive.org CC0 sourcing + ffmpeg synthesis (see `references/media-sourcing.md`).
5. **Chapter generation** — one JSON spec per chapter (`{id, dur, music, scenes:[{id, kind, start, dur, headline, sub, narration, boom, riser, count}]}`) → generated standalone composition in `compositions/chXX.html`. Scene kinds: divider, title, stat (count-up), quote, timeline, list, headline, endcard. Generator mechanics in `references/chapter-generator.md`.
6. **Check** — `npx hyperframes check` is project-scoped (dir, not file) but automatically scans `compositions/*.html` too; no need to copy chapters into `index.html`. Keep a short valid `index.html` at project root (a title card) so the project check passes.
7. **Render** — `npx hyperframes render -c compositions/chXX.html --quality high --output renders/chXX.mp4`. Chapters are independent → run 2-3 in parallel (watch RAM; ~256MB per worker ×4). Budget: draft ≈ 0.75s wall per video-second, high ≈ 3.8s. 8 × ~5min chapters ≈ 1.5-2.5h total. Then `ffmpeg` concat (same codec/size/fps).

## Critical pitfalls (each one cost real debugging time)

- **Media srcs are project-ROOT-relative, even from `compositions/chXX.html`** rendered via `-c`. Use `src="assets/x.mp3"`, `src="narration/x.mp3"`, NOT paths relative to the composition file. Lint error: `audio_src_not_found`.
- **Overlapping `<audio>` on the same `data-track-index` fails lint** (`overlapping_clips_same_track`). Give one track per SFX type: narration=10, music=11, whoosh=12, riser=13, boom=14.
- **Multiple overlapping `<audio>` elements DO mix into the render** (verified: narration audible over a music bed). Verify mixes empirically: render, then compare speech-band energy of two windows with `ffmpeg -ss <t> -t 2 -i out.mp4 -af highpass=f=4000 -ac 1 -ar 16000` + RMS via python wave. Music bed at data-volume 0.22 under narration at 1.0.
- **`check` returns "Not a directory" for a file arg** — run it project-scoped; it still validates `compositions/*.html`.
- **Count-ups are deterministic via GSAP proxy-object tween** (`tl.to(counter, {v: target, onUpdate})`) — seek-safe. Use `Math.round(v).toLocaleString("en-IN")` for Indian-style number formatting ("1,60,000").
- **Long headlines overflow** (118px × ~0.55em × chars > 1580px content width) and get flagged. Auto-fit: ≤22 chars → 118px, ≤30 → 96px, ≤40 → 80px, else 68px.
- **edge-tts `--rate -12%` breaks** — argparse eats values starting with `-`; use `--rate=-12%` form. Subprocess must use `sys.executable`, not bare `python` (can resolve to a different interpreter → MODULE_NOT_FOUND).
- **edge-tts wpm varies with text** (~116-158 wpm at default rate; slower with more punctuation/short sentences). Never assume duration from word count — always ffprobe the generated audio and size scenes from actual duration (scene dur = narration + ~6-8s breathing).
- **Windows browser cache corruption → `spawn EFTYPE`** ("not a valid application for this OS platform"): fix documented in the `hyperframes-cli` skill's `references/doctor-browser.md` (delete corrupt `~/.cache/puppeteer/chrome-headless-shell/<ver>`, then `npx hyperframes browser ensure`).
- **`npm run dev`/preview is a long-running server** — background it, never foreground.
- **git-bash mangling**: `node $HOME/.claude/...` becomes `C:\c\Users\...` — use native `C:/Users/HP/...` paths. Projects with `"type": "module"` need `.cjs` for CommonJS test scripts.

## Project layout that worked

```
videos/<project>/
  index.html            # short valid title-card composition (keeps `check` green)
  compositions/ch01..ch08.html   # standalone chapter compositions (render via -c)
  chapters/ch01..ch08.json       # chapter specs (source of truth)
  narration/<scene>.mp3 + durations.json
  assets/beds/{dark,tense,calm}.wav   # CC0 music beds
  assets/{boom,riser,whoosh,tick}.wav
  tools/tts_batch.py, gen_chapter.py, narration.py
```

## Support files

- `references/media-sourcing.md` — archive.org CC0 music/SFX sourcing recipes + dead ends + ffmpeg SFX synthesis
- `references/tts-and-audio.md` — edge-tts pipeline, voice calibration, audio-mix verification
- `references/chapter-generator.md` — gen_chapter.py architecture (rebuildable from this spec)
- `templates/tts_batch.py` — working batch-TTS script (copy + adjust paths)
