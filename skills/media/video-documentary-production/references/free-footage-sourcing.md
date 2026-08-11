# Free Footage Sourcing — No-Key Recipe (verified 2026-08-09, UPI demo build)

Used successfully to source real footage for the UPI trial documentary (videos/upi-demo).
All sources free + monetization-safe (public domain / free licenses).

## Wikimedia Commons API (no key — best for real + archival footage)

- Endpoint: `https://commons.wikimedia.org/w/api.php`
- ⚠️ REQUIRED: send a browser User-Agent header. Default urllib UA → **HTTP 403 Forbidden**.
  `UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 HermesResearch/1.0"}`
- Search query:
  `action=query&format=json&generator=search&gsrsearch=filetype:video <topic>&gsrnamespace=6&gsrlimit=8&prop=videoinfo&viprop=url|size|duration`
  (`viurlwidth=640` returns a small preview URL; for the ORIGINAL file omit viurlwidth)
- The returned `url` carries a `?utm_source=commons...&utm_content=original` suffix —
  **strip everything from the first `?`** before downloading.
- File URL pattern: `https://upload.wikimedia.org/wikipedia/commons/<h1>/<h2>/<filename>`
- ⚠️ RATE LIMIT: ~3-4 rapid API calls → **HTTP 429 Too Many Requests**. Backoff: sleep
  15-20s and retry (up to 3 attempts per title), and space successive calls ~8s apart.
  Batch the picks into one script with retry loops; fetch URLs in one pass, download after.

### Verified useful clips (India / UPI documentary, Aug 2026)
| slug | clip | dur | size |
|---|---|---|---|
| mumbai-aerial | Aerial view of Mumbai (4/43/…) | 66.7s | 17MB |
| mumbai-dest | Destination - Mumbai - India (7/76/…) | 62s | 55MB |
| mumbai-street1 | Street in Mumbai (video) 01 (b/bc/…) | 22s | 9MB |
| mumbai-street3 | Street in Mumbai (video) 03 (9/96/…) | 211s | 90MB |
| bombay1929 | Street Scenes in Bombay, India (real sound), Jan 1929 (e/e9/…) | 817s | 135MB |
| market | Video of lockdown period Sakerbazar market (9/99/…) | 10s | tiny |

`bombay1929` is archival gold for before/after arcs (1929 Bombay street sound footage).
Search topics that worked: "Mumbai street", "India market", "Aerial view of Mumbai".
Topics that FAILED: "UPI", "Indian rupee notes", "digital payment" (returned irrelevant
results — the commons search matches titles poorly for payment-system topics).

### SEMANTIC-MATCH FALLBACK: bitmap search → Ken Burns stills (v3, validated)
User correction (2026-08-09): footage that doesn't match the narration beat kills immersion
("lots of clip don't match"). Rule: every scene's visual must SEMANTICALLY match its beat.
When `filetype:video` search fails for a topic (payments/currency/QR all fail), switch to
**`filetype:bitmap` search and Ken-Burns the still** — a matching still beats mismatched
video every time:

- Query: same API but `gsrsearch=filetype:bitmap <topic>` + `prop=imageinfo&iiprop=url|size`.
- Download thumbs (much lighter than originals): insert `/thumb/<h1>/<h2>/<filename>/1920px-<filename>`
  into the upload URL (portrait originals → 1920px width; 455-700KB each vs 9-135MB video).
- Verified stills that fixed the UPI scenes (all Wikimedia, monetization-safe):
  `qr-scan.jpg` (Digital Payments QR-Code Scanning by BMTC Bengaluru), `cashless-atm.jpg`,
  `smartphone-pay.jpg` (businesswoman paying with cash + smartphone),
  `rs2000-note.jpg` (₹2000 banknote, 5032x2000 wide).
- `videoinfo` sometimes returns EMPTY for a valid file (market clip) — recover via
  `Special:FilePath/<exact filename>` redirect, or search `intitle:` for the exact title;
  truncated title guesses 404 (the real name was ~20 chars longer).
- Still layer in the composition — DIFFERENT lint contract than video (imgs are NOT timed
  media, so nesting is allowed): `<img>` INSIDE a timed `.clip` (track 0) with the scrim as
  an UNTIMED child (visible only during the clip window). Ken Burns tween targets the img
  the same way as video (`#vid-<sid>` id works for both). Generator: scene-level
  `"still": "assets/footage/<slug>.jpg"` field in the project-local gen_chapter.py.

## archive.org (no key — CC0 audio + Prelinger archival footage)

- Advanced search: `https://archive.org/advancedsearch.php?q=<query>&fl[]=identifier&fl[]=title&rows=8&output=json`
- Direct download: `https://archive.org/download/<identifier>/<file>`
- `collection:prelinger` = public-domain archival; keyword searches (india/market) skew
  to telecom-era films — broaden queries or browse the collection.

## Pexels / Pixabay (need free API keys — optional upgrade)

- Pexels: `api.pexels.com/v1/videos/search`, 200 req/hr + 20K req/mo, link-back attribution.
- Pixabay: `pixabay.com/api/videos/`, 100 req/60s, 24h result caching required.
- No keys in .env as of Aug 2026 → the Commons/archive.org keyless path is the default.

## Download + transcode for the HyperFrames pipeline

```bash
curl -sL --max-time 240 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HermesResearch/1.0" -o slug.webm "<clean-url>"
# transcode to 16:9 1920 h264 silent, keep 10-20s segments → assets/footage/
ffmpeg -i slug.webm -t 15 -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080" -c:v libx264 -preset fast -an assets/footage/slug.mp4
```

## Render cost reality (measured Aug 2026)
54s @ high quality: text-only ~5 min; 8 video scenes ~17 min (video decode per frame at 30fps
× 1634 frames dominates); 4 stills + 4 video ~8-10 min. For long-form: PRE-TRIM every clip to
its scene length (or shorter, with `loop`) before rendering — don't feed 817s/211s originals
into the renderer; also crop to the exact 16:9 1920x1080 target so `object-fit:cover` isn't
decoding extra pixels.

## Footage layer pattern in a composition (the "overlays" look) — VALIDATED structure

Verified working track layout (UPI v2 render, 2026-08-09 — the lint contract is strict):

- **Timed `<video class="clip">` on track 0** (full-bleed, `object-fit:cover`), **timed scrim
  div on track 1**, **scene text on track 2** — video BELOW scrim BELOW text.
- The wrapper around video+scrim must be a **plain UNTIMED container** (e.g.
  `<div style="position:absolute;inset:0;overflow:hidden">` with NO data-* attributes).

Two lint errors that WILL fire otherwise (both hit and fixed during the UPI build):

1. `media_missing_data_start` — the `<video>` element itself needs `data-start` and
   `data-duration` (the framework owns media timing on the element; a timed wrapper alone
   is not enough).
2. `video_nested_in_timed_element` — a `<video>` with data-start must NOT be nested inside
   ANY other element that also has data-start ("video will be FROZEN in renders"). If you
   put video+scrim in one timed `.clip` div, every scene fails. Make video and scrim timed
   SIBLINGS inside an untimed wrapper.

```html
<div style="position:absolute;inset:0;overflow:hidden;">
  <video id="vid-u1" class="clip" data-start="0.00" data-duration="6.14" data-track-index="0"
         src="assets/footage/mumbai-aerial.webm" muted loop playsinline
         style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"></video>
  <div id="scrim-u1" class="clip" data-start="0.00" data-duration="6.14" data-track-index="1"
       style="position:absolute;inset:0;background:linear-gradient(180deg, rgba(10,13,18,0.62) 0%, rgba(10,13,18,0.22) 38%, rgba(10,13,18,0.30) 62%, rgba(10,13,18,0.88) 100%);"></div>
</div>
```

- Ken Burns: `tl.fromTo("#vid-u1", { scale: 1.06, transformOrigin: "50% 50%" }, { scale: 1.22, duration: sceneDur, ease: "none" }, sceneStart)` — scale is an allow-listed property, deterministic, seek-safe.
- `loop` + `muted` on the video: clips loop to fill their window; narration/music tracks are unaffected.
- `duplicate_media_discovery_risk` warning fires when the SAME source file is used in two scenes — non-fatal ⚠, ignore.
- `timeline_track_too_dense` ⚠ fires on 8+ timed elements per track — informational.
- Generator: the project-local `tools/gen_chapter.py` (videos/upi-demo) implements this
  via a scene-level `"footage": "assets/footage/<slug>.webm"` field (auto video+scrim+Ken
  Burns, skips the global gradient bg when any scene has footage). Copy that file for new
  projects; the skill-dir copy predates footage support.
- Media srcs stay PROJECT-ROOT-relative (`assets/footage/...`) even from `compositions/`.
- webm (VP8/VP9) plays fine in the Chromium renderer; final MP4 mux is h264+aac regardless.
- Kinetic type / stat count-ups stay ON TOP of footage (Johnny Harris / Fern style).

## Monetization rule (repeated from the research)

Stock + public-domain + local Wan 2.2 (Apache-2.0) = monetization-safe. Cloud AI free
tiers (Veo/Kling/Pika/Runway) = watermarked + explicitly non-commercial — never in a
monetized video.
