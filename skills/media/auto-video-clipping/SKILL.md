---
name: auto-video-clipping
description: "Use for auto-clipping long videos into Shorts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [video, clipping, shorts, youtube, whisper, ffmpeg, podcast, automation]
---

# Auto Video Clipping (Long Video -> Shorts)

Automatically turn long videos (podcasts, streams, interviews) into vertical
9:16 Shorts with burned-in captions: download -> transcribe -> score windows ->
pick best moments -> render captioned clips. Built and verified end-to-end Aug 2026.

## Trigger conditions
- User asks to "clip" long YouTube videos / podcasts into Shorts or Reels
- User asks about "clipping setups" / "automatic clipping" / "clipping gig" (Whop/Content Rewards)
- User wants a GitHub repo / tool for long-video-to-shorts automation

## What "clipping" is (context for user convos)
- Clipping = cutting 15-60s moments from long content, posting to YT Shorts/IG/TikTok
- Platforms: Content Rewards (Whop), Clipping Capital, ClipHaus, Clippedin — campaign-based:
  join a campaign, download the podcast resource, edit, post with tags, submit link, earn per-view
- Earnings reality: ~$0.5-2 per 1000 views (a 3K-view clip ≈ Rs 133). "Rs 50K in 15 days"
  claims in tutorials are affiliate-funnel marketing (their referral links are in the description) —
  survivorship bias, not typical. Set honest expectations.
- Best-earning campaign types: gaming, podcasts, music. Verified campaigns pay; unverified may not.

## Monetization reality (verified from YouTube support page, Aug 2026)
- **YPP gate**: an account earns only after 1,000 subscribers AND 10M valid public Shorts
  views in 90 days (or 4,000 watch hours). That's ~111K views/day sustained for 3 months
  PER ACCOUNT. Run plan math through this gate before promising income.
- **India Shorts RPM**: Rs 2-6 per 1,000 views (Shorts pay ~10-20% of long-form RPM; India
  is a low-RPM market). At Rs 4/1K and 1M views/day ≈ Rs 4,000/day — and only after the gate.
- **Multi-account schemes** (e.g. 10 accounts x 10 clips/day = 100/day): honest probability
  math — mediocre output = below gate = Rs 0 (~60-70% chance); meaningful income within
  6 months ≈ 10-15%; getting flagged for spam/reused content ≈ 40-50% (10 auto-posting
  accounts screams automation). The constraint is viral probability + tier-1 audience, NOT
  clip volume — scaling volume doesn't fix it.
- **Reused-content rejection**: clipping third-party podcasts without license = "reused
  content" under YPP; channels get rejected/demonetized even past 10M views. Adding your own
  commentary/voiceover moves it toward "transformative" and survives review — the single
  highest-leverage edit for monetizability.
- **Content Rewards tier-1 trap**: campaign payouts need ~40% US/UK/CA audience. From India,
  organic views are tier-2/3 (paid a fraction or nothing); the "USA Views VPN" fix gurus sell
  is against platform ToS and the VPN link is itself an affiliate.
- **Guru tell (fast fact-check)**: every "I made Rs 50K clipping" video description is ~40%
  affiliate/referral links (contentrewards.com/r/<name>, Opus/11Labs/VPN links, paid toolkits,
  Discord/WhatsApp coaching). That's where their income actually is — from other clippers,
  not from clipping. Real clipping income: campaign per-view payouts (Rs 0-5K/mo for months
  1-3) or agency retainers (Rs 30K-1.5L/mo) that only come after proven viral clips.

## Working pipeline (scripts/clipper.py — copy to machine, run with Python 3.14)
```
python clipper.py <url> --clips 3 --window 45 --min-score 2.5 [--keywords "money,tax,crash"]
```
Flow: yt-dlp audio -> faster-whisper transcription (word timestamps) -> sliding-window
scoring (speech density + keyword hits + energy words) -> top-N non-overlapping clips ->
ffmpeg render 9:16 (1080x1920) with ASS captions burned in. Output in ~/clipper/clips/.

## Key pitfalls (all hit and fixed in practice)
1. **faster-whisper CUDA failure is at ENCODE time, not model load** — `WhisperModel('cuda')`
   succeeds, then `model.transcribe()` raises `RuntimeError: Library cublas64_12.dll is not
   found`. So the try/except must wrap the transcribe() call, not just model construction,
   and fall back to `device='cpu', compute_type='int8'`. GPU detection via
   `ctranslate2.get_cuda_device_count()` can return >0 while DLLs are missing (torch is a
   CPU-only build). Robust pattern: devices=['cuda','cpu'], try each in a loop.
2. **Python version trap on this machine**: `python` = 3.11 (no yt_dlp), yt_dlp/faster-whisper
   live on Python 3.14 at `/c/Users/HP/AppData/Local/Programs/Python/Python314/python.exe`.
   Always invoke that interpreter for this script (`python -m pip install faster-whisper` first).
3. **yt-dlp YouTube bot-check**: "Sign in to confirm you're not a bot" from datacenter IPs.
   `--cookies-from-browser chrome` fails with "Could not copy Chrome cookie database" (DB locked
   while Chrome is open); edge fails with DPAPI decrypt error. Real fix: user logs into YouTube
   in Chrome, closes Chrome, then run with `--cookies-from-browser chrome`. Local-file input
   (`clipper.py somefile.mp4`) bypasses download entirely — use for tests.
4. **ffmpeg subtitles filter on Windows**: drive-colon in ASS path breaks the filter graph
   ("Unable to parse original_size option value C:\..."). Fix: write `cap_N.ass` in WORKDIR and
   use a RELATIVE filename in the filter (`subtitles=cap_01.ass`) with `cwd=WORKDIR` in
   subprocess.run. Never absolute Windows paths inside -vf.
5. **9:16 conversion chain** (works): `crop=iw*9/16:ih,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`
6. **Verification**: ffprobe the output (expect 1080x1920), extract a frame at ~40% height,
   check bottom-third bright-pixel ratio >1% (white caption text present).

## GitHub repos in this space (checked Aug 2026 — mostly small/unmaintained)
- Tahactw/AI-YOUTUBE-SHORTS (12★) — closest to "download YT video -> Whisper -> best moments -> Shorts"
- Joyal1B/clipping-factory — faster-whisper + karaoke subs + YOLO face reframe (0★, fresh)
- Thesopan/auto-clipper — adds auto-publish via YouTube Data API (the one real gap vs our script)
- SamurAIGPT/ai-clipping-generator (59★) — production Next.js SaaS scaffold, overkill
- Anil-matcha/ai-clipping-comfyui (14★) — ComfyUI node version
Honest take: the repo space is hype-heavy; our clipper.py already does the core. The two features
repos add that matter: (a) face-tracking reframe, (b) auto-upload (YouTube Data API v3, OAuth,
free tier ~100 uploads/day).

## Auto-upload (BUILT — scripts/yt_upload.py)
YouTube Data API v3 `videos.insert` via OAuth. Script: `python yt_upload.py clip.mp4 "Title #shorts"`.
- First run does the OAuth consent dance (`run_local_server`) and saves `token.json` in ~/clipper.
- Prereqs (one-time, user's Google account): Cloud Console project -> enable "YouTube Data API
  v3" -> OAuth consent screen (External, add user as test user) -> OAuth client ID type
  "Desktop app" -> save JSON as ~/clipper/client_secret.json. Free tier ~100 uploads/day.
- `--dry-run` validates auth without uploading; `--privacy unlisted` for test uploads.
- Wire into clipper.py as a post-render step (--upload flag) for the full URL->published flow.
  Install deps: `python -m pip install google-api-python-client google-auth-oauthlib` (Python 3.14).

## Support files
- `scripts/clipper.py` — the complete working pipeline (copy, install faster-whisper, run).
- `scripts/yt_upload.py` — YouTube Data API v3 uploader with OAuth flow + --dry-run (needs client_secret.json first).

## Verification
- After building, ALWAYS test on a local file (TTS-generated speech + ffmpeg color video is a
  fast offline fixture: `ffmpeg -f lavfi -i color=c=black:s=1280x720:d=40 -i speech.mp3 -shortest test.mp4`)
  before pointing at real YouTube URLs (bot-check will block downloads in the agent env).
