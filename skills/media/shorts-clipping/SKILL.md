---
name: shorts-clipping
description: "Use for auto video clipping or clipping-income research."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [clipping, youtube-shorts, tiktok, content-rewards, whop, faster-whisper, ffmpeg, yt-dlp, side-hustle, video-automation]
---

# Shorts Clipping (automation + gig economy)

Two things in one umbrella: (1) the AUTOMATION — turning long YouTube videos
(podcasts/streams) into captioned 9:16 Shorts automatically, and (2) the
ECONOMY — how clippers actually get paid (Content Rewards / Whop campaigns)
and how to evaluate the "clipping earns lakhs" claims honestly.

## Trigger conditions
- User asks to clip long videos into Shorts/TikTok/Reels ("clipping setup", "auto clipper")
- User asks how clippers make money / "why does everyone say clippers earn boatloads"
- User wants a pipeline: download → transcribe → pick moments → render captioned vertical clips → (auto-upload)
- User proposes scaling clipping (N accounts × M clips/day) and wants projections
- User mentions Content Rewards, Whop, Vyro, "clipping campaigns", CPM per 1K views

## PART 1 — The automation pipeline (working, verified Aug 2026)

Working code lives at `scripts/clipper.py` (copy to `~/clipper/clipper.py`).
Run with the Python that has yt_dlp (on this machine that is Python 3.14,
NOT the `python` on PATH which is 3.11):
```
/c/Users/HP/AppData/Local/Programs/Python/Python314/python.exe clipper.py <url|local.mp4> --clips 3 --window 45 --min-score 2.5
```
Pipeline: yt-dlp bestaudio → faster-whisper (word timestamps) → sliding-window
scoring (speech density + keywords + energy words) → pick top N with min-gap
dedup → ASS captions burned in → 9:16 1080x1920 mp4 in `~/clipper/clips/`.
Accepts a LOCAL FILE path as input too (skips download) — great for testing
without hitting YouTube.

Install once:
```
python -m pip install faster-whisper   # Python 3.14
# ffmpeg + yt-dlp already present on this machine
```

### Pitfalls (each one cost a debug cycle — read before running)
1. **faster-whisper CUDA fails at ENCODE time, not load time.** On this
   machine `ctranslate2.get_cuda_device_count()` returns >0 (driver present)
   but `cublas64_12.dll` is missing → WhisperModel('cuda') builds fine, then
   transcribe() raises RuntimeError. The script therefore wraps the whole
   transcribe call in try/except with ['cuda','cpu'] device list and falls
   back to cpu/int8 automatically. Never assume GPU works because the driver
   is present; the DLLs are a separate install (nvidia-cublas-cu12 etc.,
   ~1.2GB — not worth it for short videos; CPU int8 on 'small' model does a
   40s clip in ~20s total).
2. **ffmpeg subtitles filter + Windows drive-colon path = parse failure**
   ("Error parsing 'original_size' option value ... as image size"). Fix:
   write the .ass with a RELATIVE filename and run ffmpeg with `cwd=WORKDIR`.
   Never pass `C:\...` paths into `subtitles=` (the `:` and `\` escaping
   breaks).
3. **yt-dlp YouTube downloads bot-check** ("Sign in to confirm you're not a
   bot"). Needs cookies: `--cookies-from-browser chrome` fails while Chrome is
   RUNNING (DB locked); `edge` fails with "Failed to decrypt with DPAPI"
   from the agent shell. OpenCLI's browser is JxBrowser (no exportable
   cookie file). Practical paths: run download with Chrome closed, or use
   `opencli youtube` only for metadata/transcripts (that session works) and
   get source video from the campaign's own resource link instead of YouTube.
4. Verification of output: `ffprobe -v error -select_streams v:0 -show_entries
   stream=width,height,duration -of csv=p=0 clips/clip_XX.mp4` must show
   1080,1920. Captions: extract a frame (`ffmpeg -ss 5 -i clip.mp4 -vframes 1
   f.jpg`) and check bright-pixel % in bottom third via PIL (>1% = text
   present).

### Auto-upload (YouTube Data API v3)
`yt_upload.py` skeleton (from this session): OAuth desktop-app flow
(client_secret.json from console.cloud.google.com → enable YouTube Data API
v3 → OAuth client ID desktop → download JSON), token saved to token.json,
`videos().insert` with resumable MediaFileUpload, categoryId '22', Shorts
titles ≤100 chars, `--dry-run` validates auth without uploading. User must
create the Google Cloud project themselves (their login); agent drives the
setup, cannot consent for them.

## PART 2 — The clipping economy (verified live Aug 2026, see references/clipping-economy-2026.md)

- **Content Rewards (contentrewards.com) is the real payment rail**: campaign
  owners pay clippers PER VERIFIED VIEW of clips posted to TikTok/IG/YT/X.
  Live CPMs seen: $0.15-$2.50/1K for open-join campaigns, $10/1K for
  application-based programs (e.g. Dreamina AI via Propaganda agency).
  Typical max payout per video $200-430. Platform takes 7% fee, pays weekly,
  campaign sets min payout.
- **Campaign anatomy**: budget ($/filled), CPM, min/max payout per video,
  approval rate (76% = pays; low = rejects), platforms allowed, content
  rules (blur women, no AI clips, no stolen content, engagement-rate
  minimums), geo restrictions, top earners' view counts (proof it pays).
- **Tier-1 audience is the payout lever**: many campaigns need ~40% US/UK
  views to count fully. IMPORTANT (user corrected me): YT Shorts + IG Reels
  distribute by CONTENT not creator location — an English US-podcast clip
  posted from Bhopal organically pulls 70-90% US/UK viewers. No VPN needed
  for YT/IG. TikTok is banned in India (VPN = ToS risk + "unusual activity"
  flags) — skip TikTok-only campaigns; most allow IG/YT as alternatives.
- **Campaign selection for a Bhopal-based clipper**: English US content,
  open budget (>30% remaining), $1.50+/1K, verified agency, IG+YT eligible,
  low clipper count (the "N" under the campaign = how many already joined;
  INDEPENDENT VOTER NEWS at 300 clippers / $15K budget was the pick).
- **Scam-funnel detection (the "gurus")**: every "I made ₹50K/₹1L clipping"
  video has referral links in description (contentrewards.com/r/XXX, Whop
  courses, VPN/elevenlabs/opus affiliates). The teacher's real income is
  referral commissions + courses, NOT clipping. The 7% fee + per-video caps
  + view verification make "boatloads" a survivorship story. State this
  plainly; the video descriptions ARE the evidence.
- **Verification is strict**: "appears botted" = rejection, view spikes =
  manual review, "BOTTING WILL NOT BE TOLERATED, INSTANT BAN" in rules.
  Never suggest VPN-view inflation or bot traffic.
- **YouTube Shorts monetization gate (own channel path)**: 1,000 subs + 10M
  valid Shorts views in 90 days (verified from support.google.com/youtube/
  answer/72851, still current Aug 2026) — ~111K views/day for 3 months per
  account before ANY ad revenue. India Shorts RPM ~Rs 2-6/1K. 10-account
  scaling plans: ~60-70% probability of Rs 0 after 3 months; reused-content
  rejection risk is the silent killer (clipping others' podcasts without
  license = demonetization at review). Commentary/voiceover over clips =
  transformative = survivable.

## Honest projection framework (for "how much will I make" asks)
- Views/short distribution: ~75% under 1K, ~15-20% 1-50K, ~3-5% 50-500K,
  ~0.5-1% 500K+. Avg 3-15K for decent content.
- Income = verified_views × CPM. Rs 0 for months 1-3 is the base case on
  Content Rewards; Rs 10-20K/month is a good month after learning which
  campaigns convert. Six figures = top ~1% (usually US/UK-based clippers).
- Never project from a guru's screenshot; project from the campaign's
  min/max payout and your realistic per-clip view range.

## Support files
- `scripts/clipper.py` — the working auto-clipper (download/transcribe/score/render, CPU-safe, local-file input).
- `references/clipping-economy-2026.md` — live campaign data, platform mechanics, tier-1 audience notes, scam-funnel evidence.

## Verification
- After building: run on a LOCAL test video first (TTS a script → ffmpeg
  color+audio → clipper.py file.mp4), confirm 1080x1920 output + captions.
- After economy research: report real campaign numbers (budget, CPM, filled
  %, approval rate, top-earner views), never guru claims.
