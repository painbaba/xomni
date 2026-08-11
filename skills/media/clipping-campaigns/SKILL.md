---
name: clipping-campaigns
description: "Use for paid clipping campaigns or the auto-clip pipeline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [clipping, content-rewards, whop, shorts, youtube, automation, creator-economy, faster-whisper, ffmpeg]
---

# Clipping Campaigns (paid per-view content) + Automation

The "clipping" economy: cut long-form content (podcasts, streams, trailers) into
vertical Shorts/Reels, post on your accounts, submit links to campaigns, get paid
per 1,000 VERIFIED views. This skill covers (a) the real platform economics vs the
guru hype, (b) how to evaluate campaigns, and (c) the working automation pipeline
on this machine (C:\Users\HP\clipper\clipper.py + yt_upload.py).

## Trigger conditions
- User says "clipping", "content rewards", "whop", "make shorts from videos", "clip long youtube videos"
- User wants to earn from posting Shorts/Reels clips
- User needs the auto-clipper or YouTube uploader run
- User asks whether clipping income claims are real / what the actual payment path is

## The real economics (verified live Aug 2026 — see references/content-rewards-economics.md)
- **Content Rewards (contentrewards.com)** is the main platform. Free signup via Google
  ("Continue with Google" — full registration, no forms). Pays through Whop → bank/UPI.
  Platform takes a **7% fee** from clipper payouts. Payouts every 7 days, minimum payout
  set per campaign, per-video MAX payout caps earnings on a single clip (~$200-430 typical).
- **CPM reality: $0.50–$2.50 per 1K verified views** (most campaigns $1–$2; rare premium
  programs e.g. Dreamina AI $10/1K are application-based "View Program", not open-join).
  A 100K-view clip ≈ $100-250 gross before the 7% fee.
- **Tier-1 GEO requirement is the real gate**: campaigns require the account's audience to
  be ~40-60%+ US/UK/CA (Blitz brief: "at least 60% of its audience in US/UK/CA"). Indian
  views are tier-2/3 and dilute the payout %. This is THE constraint — not clip volume.
- **Reaching tier-1 audience from India is possible WITHOUT VPN**: YouTube Shorts and
  Instagram Reels distribute by CONTENT, not creator location. English clips of US podcasts
  naturally pull 70-90% US/UK audiences. Post at US peak times (IST 8:30pm-12:30am = US
  morning; IST 5:30-9:30am = US evening), English captions only, no India-trending hashtags.
  TikTok is BANNED in India → needs VPN → ToS risk + "unusual activity" flags → skip
  TikTok-only campaigns or treat TikTok as a bonus on a non-critical account.
- **View verification is strict**: "appears botted" = rejection; "unusual activity signals
  (spikes in views)" = flagged + manual review; campaigns ban botting with instant bans.
  Never use VPN-view-inflation or bought views — that is how clippers get banned and lose
  the balance they earned.
- **Budgets get FILLED fast**: big campaigns (CoD $120K, Roobet $250K) show 99%+ filled —
  racing for crumbs. Prefer campaigns with budget <30% used, fresh (hours-days old), $2/1K+,
  verified agency, high approval rate (e.g. 76%+).

## The guru funnel (how to spot the lie)
Every "I made ₹50K/₹1L clipping" video has affiliate/referral links in the description
(contentrewards.com/r/<name>, whop links, toolkits, Discord communities, VPN affiliates).
The video creator's real income is referral commissions + course/toolkit sales, not clipping.
Proof of the real rate is IN the videos: one showed ~3,000 views ≈ ₹133 (~$0.5-1/1K).
The actual path is: join campaigns → clip from provided assets → post → submit → verified
views counted → weekly payout. Beginner-realistic: ₹0-15K/month for the first 1-3 months;
six figures/month is top ~1% (usually US/UK-based clippers). The 10-account/100-clips/day
plan is wrong scale: the constraint is tier-1 audience + viral probability, not volume.
Also: 10 auto-posted accounts screaming automation → reused-content/spam risk.

## Evaluating a campaign (open the campaign page)
Check in order: CPM ($/1K) → budget used % → max payout per video → approval rate →
platforms allowed (YT Shorts/IG Reels work from India; TikTok-only = skip) → GEO rule →
DON'TS list (auto-reject: gambling framing, "free money/glitch/guaranteed win" language,
banned topics, competitor bashing) → "Every video must" checklist (name the app, tag the
official account, campaign hashtag, promo code, trending music added IN-PLATFORM at publish).
Read the full brief (Notion/Docs) before clipping — rule misses = rejected clips = no payout.
Campaigns marked "Verified Agency" pay reliably; unverified ones often don't.

## The automation pipeline (built + verified Aug 2026)
Files at C:\Users\HP\clipper\:
- `clipper.py` — download → transcribe → auto-pick best windows → render 9:16 captioned
  clips. Usage: `python clipper.py <url|local.mp4> --clips N --window 40 --min-score 2.5
  [--upload]`. Scoring: speech density + keyword hits + energy words over sliding windows.
  Output: clips/clip_XX_start-end.mp4 (1080x1920, burned-in ASS captions).
- `yt_upload.py` — YouTube Data API v3 upload (Shorts). Needs one-time Google Cloud setup:
  project → enable YouTube Data API → OAuth consent (External, self as test user) → Desktop
  app client → save JSON as client_secret.json → first run opens browser consent → token.json
  cached. `--dry-run` validates auth; `--privacy unlisted` for testing.
- The uploader's OAuth flow is the ONLY manual step; everything else runs headless.
- Windows pitfall: yt_dlp/faster-whisper live on Python 3.14 — invoke explicitly:
  `C:\Users\HP\AppData\Local\Programs\Python\Python314\python.exe clipper.py ...`
  (`python` = 3.11, `python3` = 3.13 — neither has the libs).

## Pipeline pitfalls (all hit + fixed this session)
- **faster-whisper CUDA**: ctranslate2 reports CUDA device present but cublas64_12.dll is
  missing → crash at ENCODE time, not load time. Fix baked in: try cuda, catch Exception
  around the transcribe call, fall back to cpu/int8. Do NOT install 1.2GB nvidia wheels to
  "fix" it — CPU int8 transcribes fine (24s for a 40s clip).
- **ffmpeg subtitles filter + Windows path**: `subtitles=C:\path\cap.ass` fails with
  "Error applying option 'original_size'" — drive-colon escaping breaks it. Fix: chdir to
  workdir and use a RELATIVE ass filename (`subtitles=cap_01.ass`), pass cwd=WORKDIR to
  subprocess.
- **yt-dlp YouTube bot check** ("Sign in to confirm you're not a bot"): needs cookies.
  --cookies-from-browser chrome fails while Chrome is running (DB locked); edge fails with
  DPAPI decrypt error from this session. Workaround: run downloads with Chrome CLOSED, or
  download the source in the user's browser, or test the pipeline on local files (clipper.py
  accepts local paths).
- **Dropbox shared-folder downloads truncate**: `curl ...&dl=1` stops mid-file at timeout
  (exit 28) and the zip has no central directory. Resume (-C -) fails; re-download with a
  generous timeout (~300s) + --retry 2 completes it (790MB, 31 files was the real size).
  Verify with `python -c "import zipfile; zipfile.ZipFile(f)"` before unzip.

## Workflow
1. Research the platform/campaign landscape live (browser; discover page shows CPM, budget,
   fill %, per-campaign). Never quote guru claims — quote the platform page.
2. Pick campaigns: $2/1K+, budget <30% used, verified agency, YT/IG-eligible, English/US content.
3. Read the campaign brief (Notion link usually in the campaign page resources).
4. Prefer "post ready creatives" (provided finished videos) for a new account — zero editing,
   pre-approved content, builds Trust Score. Switch to own edits once approved clips exist.
5. For own edits: clipper.py on the source; verify clips against the brief's DON'TS before
   posting (e.g. "blur all women", "no AI-generated clips" — some campaigns forbid AI clips).
6. Captions: follow the brief's checklist verbatim (app name, @tag, campaign hashtag, promo
   code, trending music added in-platform at publish, no banned language).
7. Submit video URLs on the campaign page; expect 7-day verification → weekly payout.

## Support files
- `references/content-rewards-economics.md` — live campaign data, fee/payout mechanics,
  campaign-evaluation checklist, Blitz brief structure, the guru-funnel evidence.

## Verification
- Before telling the user a campaign pays X: state CPM, budget fill %, approval rate from the
  live campaign page.
- After running clipper.py: confirm output exists in clips/ and is 1080x1920 via ffprobe.
- Never claim projected earnings without the tier-1-audience caveat.
