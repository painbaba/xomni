---
name: free-media-sourcing
description: Use when sourcing free media and verifying URLs + licenses.
---

# free-media-sourcing

Class of task: **"HUNT: best FREE <media> for <use> — verify direct download URLs + exact licenses (CC0/PD/CC-BY)"**. Typical asks: cinematic trailer music bed with a specific arc (tense build → hopeful release), SFX packs (boom/riser/whoosh/tick), stock images, fonts, footage, **AI-generated images from free no-key generators** (avatars, host cards, thumbnails, b-roll, presenter portraits). By extension applies to any "free asset + license proof" request.

## Core principle

Never ship unverified claims. Every candidate gets:
1. a **direct download URL** (not a page link),
2. **HTTP 200 proof** (HEAD check: status + Content-Length),
3. **duration** for audio (exact seconds),
4. the **EXACT license text quoted** (license field, not vibes),
5. **caveats flagged** (license-field vs description contradictions, NC/ND/SA terms, per-file 403s).

Deliverable format: ranked candidates, each with verified URL, license, duration, and one-line fit rationale. State the verification method in the report.

## Workflow (5 steps)

### 1. Discovery — archive.org APIs (curl/python with a real UA header)
- Search: `https://archive.org/advancedsearch.php?q=<Q> AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=downloads&fl[]=creator&fl[]=licenseurl&sort[]=downloads+desc&rows=25&output=json`
- Proven query shapes: `(cinematic trailer) AND mediatype:audio` · `(whoosh OR "whoosh sound effect") AND mediatype:audio` · `SSE_Library AND mediatype:audio` · `(red library) AND mediatype:audio` · `creator:"Kevin MacLeod"` · `(impact OR boom) AND (sfx OR "sound effects") AND mediatype:audio`
- Filter OUT: `by-nc` / `by-nd` licenses (fail commercial/no-derivative), Two Steps From Hell / Audiomachine / Thomas Bergersen / Zack Hemsey items (copyrighted even though hosted on archive), radio/podcast noise, meme sound items with no license.

### 2. Metadata + durations
`https://archive.org/metadata/<identifier>` → `files[]`, each with `length` (seconds) and `licenseurl`/`rights`. Filter audio to the target window (e.g. 40–140s for a 60s bed). For huge libraries (3k+ files), grep filenames by keyword: `tension|rise|hope|trailer|epic|cinematic|hero|dark|countdown|tick|metronom` — and look for **"60 sec" trailer cuts** and **stem variants** (No Riser / No Drums / Underscore Mix) which editors need for clean mixing.

### 3. Direct-URL patterns (verified working)
- archive.org: `https://archive.org/download/<id>/<folder>/<file>` — URL-encode: spaces `%20`, semicolons `%3B`, `&` `%26`, quotes. HEAD returns `audio/mpeg`.
- incompetech: `https://incompetech.com/music/royalty-free/mp3-royaltyfree/<Track%20Name>.mp3` — CC BY 4.0. The JSON index (`/JSON/index.json`) is 404 — don't try it; measure durations by downloading + ffprobe.
- Kenney (CC0): extract `href="([^"]+\.zip)"` from `https://kenney.nl/assets/<slug>` → `https://kenney.nl/media/pages/assets/<slug>/<hash>/kenney_<slug>.zip`. Some asset pages are JS shells (no zip in raw HTML) — if regex finds nothing, pick a different pack, don't guess hashes.
- Mixkit (free, NOT CC0): full file `https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav`, preview `<id>-preview.mp3`. Some IDs 403 — verify per file.

### 4. Verify EVERY final URL
HEAD check (status, Content-Length, Content-Type). For durations missing from metadata: download then `ffprobe -v error -show_entries format=duration -of csv=p=0 <file>` (mutagen pip-installs as fallback). `application/octet-stream` is fine for mp3 — trust Content-Length, not MIME.

### 5. Extract and quote the EXACT license
Read item `licenseurl`, `rights`, and the item description. **Flag contradictions verbatim** — e.g. license field says CC BY 4.0 but description says "free for personal use" (commercial-use ambiguity; offer a zero-caveat alternate). Skip items with no licenseurl unless the item page text states terms (e.g. Serge Quadrado items have none on archive).

## Footage & stills (photo / stock video) sourcing

For "HUNT: upgrade my trailer's assets — best free 1920px+ stills + 1080p videos per scene" asks. Provider priority: Wikimedia Commons → Pexels → Pixabay → archive.org (footage-wise archive.org has almost nothing modern; don't burn time there first).

### Wikimedia Commons (API-first: dimensions + license with zero downloads)
- Search recipe: `https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=<QUERY>%20filetype:video&gsrnamespace=6&gsrlimit=12&prop=imageinfo&iiprop=url|size|mime|extmetadata&iiurlwidth=1920`
  - `filetype:video` filters to footage; `intitle:<term>` narrows (plain `UPI` searches get polluted by unrelated matches — use `intitle:` or quoted phrases); `gsrnamespace=6` = File namespace.
  - `imageinfo` gives width/height/mime + `extmetadata.LicenseShortName` → pre-screen resolution + license without a single download.
  - For videos use `prop=videoinfo&viprop=url|size|mime|derivatives` — but derivative `url` fields often come back None; the ORIGINAL `url` is a direct download regardless. Commons ships WebM/OGG only (no mp4 transcodes) — transcode locally with ffmpeg.
  - Strip the trailing `?utm_source=...` params the API appends before shipping URLs.
- **Rate-limit ladder (upload.wikimedia.org 429s burst HEADs — that's throttling, NOT a dead link):** ① existence still provable via API metadata (works under throttle), ② `curl -sI https://commons.wikimedia.org/wiki/Special:FilePath/<File name>` → **302 = file exists** (different endpoint, not throttled), ③ after the throttle clears (~1–4 min), ranged GET `curl -r 0-2047 -L` → **206 + media Content-Type** = verified downloadable. Space requests 8–12 s apart. The 429 window is IP-wide — even a real browser gets 403 during it.
- License ladder for footage: CC0 (no attribution) > CC BY > CC BY-SA; genuine Public-domain archival clips exist (e.g. "Street Scenes in Bombay, India 1929" 720p PD).

### Pexels (scrape SEARCH pages, not video pages)
- `https://www.pexels.com/search/videos/<query>/` HTML embeds direct CDN links `https://videos.pexels.com/video-files/<id>/<id>-hd_1080_1920_30fps.mp4` plus titles as `"id":...,"title":"..."` JSON — parse both in one pass.
- Filename encodes orientation/resolution: `hd_1080_1920` = portrait 1080p, `hd_1920_1080` = landscape. Phone/QR close-ups are usually portrait-only — plan for vertical crops or pair with a landscape still.
- Video *pages* (`/video/<id>/`) get Cloudflare-blocked after a few hits; search pages tolerate more. Treat 403s as transient: back off 5–10 s, retry, or re-parse a saved copy of the search page.
- CDN supports Range (206 + Content-Range). Pexels License = free, no attribution.

### Pixabay
- Search page HTML contains thumbnails `https://cdn.pixabay.com/video/YYYY/MM/DD/<id>-<ts>_tiny.mp4` (also `_tiny.jpg`); swap `_tiny` → `_large` for the big file (13–48 MB, ~1080p). `_hd` variants 403 — they don't exist; don't chase them.
- Titles arrive as interleaved `"name":"..."` JSON (a brand "Pixabay" entry between each title) — map by index: title = `names[2*i+1]` for the i-th video.
- **Hard rate-limits after 2–3 page fetches** — space searches ≥10 s apart; expect failures after a burst and retry minutes later.
- Pixabay License = free, no attribution.

### archive.org (footage)
- advancedsearch WITHOUT `AND mediatype:movies` returns junk (this bit a session in 2026-08). With the filter it exists but yielded no usable modern footage for an India documentary — Commons/Pexels/Pixabay first, archive.org as last resort for footage.

Full per-provider recipes, the verification ladder, and a worked example (verified UPI documentary asset table) in `references/stills-and-footage-sources.md`. For bulk verification of throttled hosts use `scripts/verify_media_urls.py` (HEAD → ranged-GET fallback, per-URL sleep).

## Free AI image generation (no API key)

For "synthetic face / portrait / avatar from a free generator" asks, the verified 2026-08 recipe:

1. **Generate** from the no-key endpoints catalogued in `references/no-key-ai-image-generation.md`. Top picks: official HF model Spaces via their open Gradio API (e.g. `black-forest-labs/FLUX.1-schnell` → true 1024–2048px output, photoreal) and Pollinations (`image.pollinations.ai` URL API — zero setup, but every model hard-caps at 768×768). Random-face fallback: this-person-does-not-exist.com (has Indian/ethnicity selectors).
2. **Verify EVERY image** with `scripts/verify_image.py` (JPEG magic bytes + SOF-marker dimension parse, PIL, OpenCV Haar face detection + coverage, Laplacian sharpness). cv2 import is optional in the script; if installing fresh, pin `opencv-python-headless==4.10.0.84` — 5.x dropped `CascadeClassifier`.
3. **Mirror session-scoped URLs**: HF Gradio file URLs (`/gradio_api/file=...`) expire on space restart. Upload finals to catbox.moe (anonymous, no account: `curl -F "reqtype=fileupload" -F "fileToUpload=@x.jpg" https://catbox.moe/user/api.php` → returns direct URL), then ship BOTH original + mirror in the report.
4. **Rank** by resolution > Laplacian sharpness > face coverage > generator reputation. State the verification method in the report; give exact download commands.

## Pitfalls
- **FreePD.com is CLOSED** — homepage literally says "Site Closed" (verified 2026-08). Don't test its `/music/` pattern or list it as a source.
- **HF Spaces run on ZeroGPU with an anonymous quota (~1–2 min GPU per IP)**, then `POST /gradio_api/call/infer` errors with "You have exceeded your ZeroGPU quota" (some spaces emit a bare `event: error / data: null` instead — same cause). Error signature + retry-loop recipe in the reference; a free HF token removes the cap.
- **HF space hostnames aren't always the naive `owner-name.hf.space`** — derive the real host from `https://huggingface.co/api/spaces/<owner>/<name>` (runtime stage) or the space page's iframe src (e.g. the BFL flux space is `black-forest-labs-flux-1-schnell.hf.space`, hyphenated; naive guess 404s). Check `/gradio_api/info` before POSTing.
- **Pollinations caps EVERY model (flux, flux-realism, turbo, sdxl, kandinsky, sana) at 768×768** — requesting 1024+ silently returns 768; `/models` currently lists only `sana`.
- **Gradio outputs are often WEBP/PNG, not JPEG** — verify with magic bytes, never the extension.
- **thispersondoesnotexist.com is DEAD** (domain for sale, 2026-08). Use this-person-does-not-exist.com instead.
- archive.org license field can contradict the description — quote both and flag.
- `by-sa` = share-alike (ok only if acceptable to the user); `by-nc`/`by-nd` fail commercial filters.
- 403 on one Mixkit ID ≠ whole host down — check each file; drop the 403s, keep the 200s.
- When the top candidate has a license caveat, still rank it #1 but pair it with a verified zero-caveat alternate (incompetech CC BY 4.0 tracks work well for this).
- **`upload.wikimedia.org` 429 ≠ dead URL** — it's a per-IP burst throttle (even a real browser gets 403 during the window). Verify existence via API + `Special:FilePath` 302, then re-verify 206 with spaced ranged GETs after the throttle clears. Never drop a candidate on 429 alone.
- **Strip `?utm_source=commons.wikimedia.org&...` params** from Wikimedia API URLs before shipping them — they're tracking noise.
- **Pexels/Pixabay 403s are burst-rate, not permanent blocks** — back off and retry; if the search page worked once, save it for re-parsing rather than re-fetching.
- Commons plain-term searches get polluted (e.g. `UPI` returns an airline tail number and flags) — use `intitle:` / quoted phrases / `filetype:video` to cut noise.

## Support files
- `references/verified-sources.md` — verified catalog (SSE CC0 SFX packs + direct file URLs, Frank Schlimbach CC-BY 4.0 library, incompetech track list with measured durations, Kenney/Mixkit patterns, exact license texts).
- `references/no-key-ai-image-generation.md` — verified no-key image-gen endpoints (Pollinations URL API, HF Spaces Gradio API flow with sample payloads, this-person-does-not-exist.com, catbox mirroring), ZeroGPU quota error signatures + retry loop, dead ends with dates.
- `scripts/verify_direct_urls.py` — re-runnable HEAD checker for a list of URLs (+ optional ffprobe duration probe).
- `references/stills-and-footage-sources.md` — full footage/stills provider recipes (Commons API query strings, Pexels/Pixabay CDN patterns + title extraction) and a worked example: verified scene-by-scene asset table for the UPI India documentary trailer.
- `scripts/verify_media_urls.py` — HEAD → ranged-GET (206) fallback verifier with per-URL sleep, for Wikimedia/Pexels/Pixabay hosts that throttle burst HEADs.
- `scripts/verify_image.py` — re-runnable image verifier (JPEG magic + SOF dims, PIL open, OpenCV Haar face detection + coverage, Laplacian sharpness) for AI-generated image candidates.
