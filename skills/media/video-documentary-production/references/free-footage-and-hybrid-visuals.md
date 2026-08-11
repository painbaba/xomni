# Free Footage, Stills & Hybrid Visuals (HyperFrames compositions)

Session-verified 2026-08-10 (UPI 1-min trailer v2/v3 builds). All sources FREE and
monetization-safe.

## The rule the user enforced (semantic matching)
Mismatched footage kills immersion — the user rejected v2 ("lots of clip don't match").
Every scene's visual MUST match its narration subject. When a good VIDEO doesn't exist,
use a matching STILL with Ken Burns (classic documentary technique) — a matching still
beats mismatched video. Stock-footage-everywhere is NOT the goal; mix per the pro formula.

## Wikimedia Commons = the no-key footage/stills source
- API always needs a real browser UA header, else 403.
- Search videos: `action=query&generator=search&gsrsearch=filetype:video <topic>&gsrnamespace=6&prop=videoinfo&viprop=url|size|duration`
- Search images: same with `filetype:bitmap` + `prop=imageinfo&iiprop=url|size`
- Full file URL: `ii.get("url").split("?")[0]` (strip utm_* suffix).
- Thumbnails (much lighter for render): `.../commons/thumb/<h1>/<h2>/<file>/1920px-<file>`
- TRAP: search results truncate filenames at ~55 chars — the exact title is longer;
  resolving a truncated title via imageinfo returns nothing. Re-search with `intitle:<unique words>`
  or use the exact title from a second query.
- TRAP: videoinfo can return empty for some webm files; retry via `prop=imageinfo` or
  `https://commons.wikimedia.org/wiki/Special:FilePath/<exact filename>` redirect.
- Rate limits: 429 after ~4-6 rapid calls — sleep 15-25s between queries; retry loop
  with 3 attempts + 15s backoff works.
- India/Upi-relevant finds: "Digital Payments initiative -QR Code Scanning by BMTC",
  "Cashless ATM.jpg", "₹2000 Indian Rupee Banknote.jpg", "Aerial view of Mumbai",
  "Street in Mumbai (video) 0X.webm", "Street Scenes in Bombay, India (real sound), Jan 1929".

## Synthetic faces (avatar sources / presenter stills) — ethics + free
NEVER lip-sync a real identifiable person's face to your narration (deepfake optics,
blocks monetization). Generate a synthetic face:
- Pollinations: `curl "https://image.pollinations.ai/prompt/<prompt>?width=1024&height=576"`
  — returns JPEG bytes even when asked for JSON; VERIFY with PIL (size/mode) and check
  the file is not empty/HTML.
- thispersondoesnotexist.com returns an HTML block page from curl — fallback only.

## HyperFrames timed-media layer rules (lint-verified)
- `<video>` with `data-start` must be a TOP-LEVEL timed element — nesting it inside
  another timed element (`class="clip"` + data-start) fails lint
  `video_nested_in_timed_element` ("video will be FROZEN").
- `<img>` is NOT timed media — it CAN live inside a timed clip wrapper; the scrim can
  be an untimed child of that clip (visible only during the clip window).
- Video layout that passes lint: untimed wrapper div → inside it a timed `<video
  class="clip" data-start data-duration data-track-index="0">` + a timed scrim div on
  track 1; scene text moves to track 2 (z-order: footage < scrim < text).
- Ken Burns: `tl.fromTo("#vid-X", {scale:1.06},{scale:1.22, duration: sceneDur,
  ease:"none"}, start)` on video OR img (same id) — deterministic.
- Scrim gradient for readability: `linear-gradient(180deg, rgba(10,13,18,.50) 0%,
  rgba(10,13,18,.16) 38%, rgba(10,13,18,.24) 62%, rgba(10,13,18,.80) 100%)` (lightened
  after user said footage barely showed).

## Coverage gate + h264 (render-critical)
- HyperFrames render aborts if a video clip's frame coverage < 95%
  (`HF_VIDEO_COVERAGE_THRESHOLD` env can disable the gate — don't, it catches real
  problems). Webm/VP9 footage DROPS frames in headless Chromium (measured: 56.9%
  coverage → abort).
- FIX: transcode ALL footage to h264 MP4 first:
  `ffmpeg -y -v error -i in.webm -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -an -movflags +faststart out.mp4`
  Bonus: render 3.4x faster (17min → 5min for 54s).
- "File ended prematurely" webm warnings during transcode are container notes — files
  still decode fine; verify with ffprobe duration.

## Kinetic captions from the SCRIPT (no Whisper needed)
We already have the narration text — captions generate directly from it. Per scene:
- caption bar = timed clip (track 3, above text), spans per word (`class="w"`), gold
  `.active` class on the current word.
- word i at `cap0 + i*step`, `cap0 = st+0.6`, `step = max((dur-1.4)/nWords, 0.18)`.
- GSAP: `tl.fromTo(word,{autoAlpha:0,y:10},{autoAlpha:1,y:0,duration:0.14},t)` +
  `tl.call(() => {words.forEach(w=>w.classList.remove("active")); words[i].classList.add("active")}, null, t)`.
- Source chip ("NPCI · As reported") = static div inside the caption clip, bottom-left.
- Count-up scenes: add tick.wav (0.08s) at ~6 offsets 0.3s apart on their own audio
  track (15) — same-track overlap is a lint error, keep ticks non-overlapping.

## Short-form "fast" mode (trailers / ≤90s)
Project-local `tools/gen_chapter.py` (mundhe-documentary + upi-demo) supports
`"fast": true` in the chapter spec: scene dur = `max(3.0, narration + 1.2)` instead of
long-form's `max(40.0, narration + 10)`. 8 scenes ≈ 54s. The skill's bundled
scripts/gen_chapter.py is the long-form variant only — copy the project version for
trailers.
