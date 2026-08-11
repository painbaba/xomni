---
name: video-content-analysis
description: Determine what a video shows without watching (reels, X).
---

# Video Content Analysis (read a video you can't watch)

Goal: reconstruct what a video actually shows AND says, then answer the user's
question (often "is this possible/real?" = a realism/feasibility verdict).
Proven end-to-end on Instagram reels on this host (2026-08).

## Pipeline (validated order)

1. **Metadata first — no download needed.** Caption/title/uploader often answer
   the question by themselves:
   `yt-dlp --skip-download --print "%(title)s ||| %(uploader)s ||| %(description)s" URL`
   Instagram works without login. Alt: `curl -sL -A "<browser UA>" URL/embed/captioned/`
   returns caption HTML.
2. **Download**: `yt-dlp -f "best[ext=mp4]/best" -o out.mp4 URL` (reels are small,
   seconds).
3. **Keyframes**: `ffmpeg -y -i out.mp4 -vf "fps=1/4" -q:v 3 frames/fr_%02d.jpg`
   (~1 frame per 4s; for a 43s clip that's ~11 frames). For vision, sample 4–8
   spread evenly across the clip.
4. **Audio**: `ffmpeg -y -i out.mp4 -ar 16000 -ac 1 audio.mp3`.
5. **Vision** (what's on screen, visible text verbatim): send frames to a
   vision-capable model. On this host the working route is the opencode-go
   gateway with `minimax-m3` — see `references/opencode-go-vision.md` for the
   key, the mandatory User-Agent header, and which models have vision.
6. **Transcription** (what's said): faster-whisper under `python` (3.11):
   `WhisperModel("small", device="cpu", compute_type="int8")` + `vad_filter=True`.
   Plenty accurate for short clips; no GPU needed.
7. **Cross-check & verdict**: whisper mishears domain terms ("Tor networking" →
   "core networking"). Combine caption + vision + transcript to identify the
   scene/claim, then answer claim-by-claim (what's real, what's dramatized).

## Pitfalls (all hit on this host)

- **MSYS /tmp trap**: native Windows ffmpeg/curl do NOT see git-bash's `/tmp`
  (they write to `C:\tmp`). Always use real paths (`~/Downloads/...`) for
  ffmpeg outputs and curl -o targets.
- **.env OPENAI_API_KEY is a stub** (`sk-fake-...`) on this host — 401s on
  api.openai.com. The real provider key is `OPENCODE_GO_API_KEY`.
- **opencode-go gateway returns Cloudflare 403 "error code: 1010"** on direct
  script calls unless a browser `User-Agent` header is sent. Always include one.
- **`uv pip install --system` targets Python 3.14** on this host, but `python`
  is 3.11 — run whisper/transcription with `python`, not `python3`.
- Whisper transcribes scene dialogue with its own capitalization; strip timestamps
  and re-read for accuracy before quoting lines in a verdict.
- Don't trust a single frame sample: a montage reel cuts scenes — spread frames.

## Verification

- Vision description should match the transcript's scene (same characters/action).
- If the user's "is this possible" is about realism (hacking, stunts, AI tricks),
  structure the verdict claim-by-claim: what's technically real, what's
  compressed/dramatized. Name the specific scene/line so the user can confirm
  you watched the right thing.
- Save artifacts at a known path and tell the user (e.g. the mp4) so they can
  spot-check.

## Support files

- `scripts/analyze_video.py` — one-shot: download → frames → audio → vision →
  transcription for any URL. Run with `python` (3.11).
- `references/opencode-go-vision.md` — gateway endpoint, key, UA requirement,
  model list, per-model vision capability results.
