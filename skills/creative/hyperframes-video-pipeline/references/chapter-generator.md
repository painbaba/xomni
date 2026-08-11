# Chapter generator architecture (gen_chapter.py)

A Python generator turns a chapter JSON spec into a standalone HyperFrames composition. Rebuildable from this spec — the full script lives at `C:\Users\HP\videos\mundhe-documentary\tools\gen_chapter.py` as a working reference.

## Input spec (chapters/chXX.json)

```json
{
  "id": "ch01", "title": "ACT ONE", "dur": 300.0, "music": "bed-tense",
  "scenes": [
    {"id":"a1s1","kind":"divider","dur":45,"eyebrow":"Act One","headline":"THE RAID","sub":"...","narration":"a1s1","riser":true},
    {"id":"a1s2","kind":"stat","dur":50,"eyebrow":"...","stat":"1131","statLabel":"inspections","sub":"...","narration":"a1s2","boom":true,"count":true}
  ]
}
```

- Scene `start` is computed by the generator (cumulative); explicit `dur` or auto = narration + 6s (min 30).
- `narration` = scene id whose audio lives in `narration/<id>.mp3` with duration in `narration/durations.json`.

## Scene kinds → markup + choreography

| kind | elements | entrance |
|---|---|---|
| divider | eyebrow, red-gold rule (scaleX), headline, sub | staggered, rule draws |
| title | eyebrow, headline, sub | rise (y 40-48, power4) |
| stat | eyebrow, stat-num (330px gold), stat-label, sub | number rises; optional count-up proxy tween |
| quote | big red quote-mark (back.out), quote-text (86px), attr | staggered |
| timeline | headline + line (fill scaleX) + nodes (dot/time/label) | line draws, nodes pop back.out, staggered 0.5s |
| list | headline + rows (panel, red left border, marker dot) | rows slide in x -34, staggered 0.35s |
| headline | masthead (letterspaced), headline, deck, attr | news-paper style |
| endcard | eyebrow, headline (scale-in), sub, credits | scale 0.94→1 |

Every scene gets an exit: `tl.fromTo("#<id> .scene", {autoAlpha:1},{autoAlpha:0, y:-22, duration:0.6}, start+dur-0.7)` — animating the inner `.scene` wrapper (never the `.clip` element itself; the framework owns clip visibility).

## Determinism rules the generator must respect

- No CSS `transform` on any tweened element (lint: `gsap_css_transform_conflict`) — tween from a fromTo state instead.
- Count-ups: GSAP proxy object `{v:0}` tweened to target with `onUpdate` writing `textContent` — seek-safe. Format with `Math.round(v).toLocaleString("en-IN")` for Indian-style numbers.
- Headline auto-fit (avoid `text_box_overflow`): plain-text length ≤22 → 118px, ≤30 → 96px, ≤40 → 80px, else 68px.
- No `<br>` in body text; block-level + sized elements for transforms.

## Audio elements the generator emits

- Narration: `<audio src="narration/<id>.mp3" data-start="scene.start+0.4" data-duration="dur+0.5" data-track-index="10">`
- Music bed: `<audio src="assets/beds/<music>.wav" data-start="0" data-duration="chapter_dur" data-track-index="11" data-volume="0.22">` + volume fade-in/out tweens on the timeline.
- SFX: whoosh at each scene boundary (track 12, start-0.15), riser at act opens (track 13), boom at stat reveals (track 14). **One track index per SFX type** — shared tracks with overlapping windows fail lint.
- **All srcs are project-root-relative** even though the composition sits in `compositions/`.

## Orchestration

1. `narration.py` injects the written narration script (dict keyed by scene id) into chapter JSONs.
2. `tts_batch.py` → `narration/*.mp3` + `durations.json`.
3. `gen_chapter.py chapters/chXX.json compositions/chXX.html narration/` per chapter.
4. `npx hyperframes check` (project-scoped; scans compositions/*.html automatically).
5. `npx hyperframes render -c compositions/chXX.html --quality high --output renders/chXX.mp4` — run 2-3 chapters in parallel.
6. `ffmpeg` concat (re-encode to identical codec/rate/size, then `-f concat`).
