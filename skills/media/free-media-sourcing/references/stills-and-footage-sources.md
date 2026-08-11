# Stills & footage sourcing — provider recipes + worked example

Verified 2026-08 while upgrading a UPI India documentary trailer (scenes: digital payments, QR payment close-up, currency, Mumbai street/aerial, Indian market). All URLs below were HTTP 200/206-verified at hunt time; re-verify before reuse (hosts rotate).

## Provider recipes

### Wikimedia Commons — API-first search (dimensions + license, zero downloads)

```python
params = {
  'action': 'query', 'format': 'json',
  'generator': 'search',
  'gsrsearch': query + (' filetype:video' if want_video else ''),
  'gsrnamespace': '6', 'gsrlimit': '12',
  'prop': 'imageinfo',
  'iiprop': 'url|size|mime|extmetadata',
  'iiurlwidth': '1920',
}
# URL: https://commons.wikimedia.org/w/api.php?<urlencode(params)>
# Each page: title, imageinfo[0].width/.height/.mime/.url + extmetadata.LicenseShortName.value
```
- Videos: `prop=videoinfo&viprop=url|size|mime|derivatives|extmetadata`. Derivatives often report `url: None`; the ORIGINAL `url` is a direct download regardless.
- Noise control: plain `UPI` matched an airline tail number (`EI-UPI MD11F`), Philippine town flags, festival photos. Use `intitle:UPI`, quoted phrases, or `filetype:video`.
- Query terms that worked well per scene: `"500 rupee" banknote`, `"2000 rupee" note` (huge single-note photos), `QR code payment India shop`, `street vendor QR code`, `Mumbai Marine Drive`, `Chandni Chowk market`, `Mumbai aerial view`, `Indian railway station`.

### Verification ladder for upload.wikimedia.org (throttle-safe)

upload.wikimedia.org throttles burst HEADs per IP (429; even a real browser gets 403 during the window). Order of evidence, cheapest first:

1. **API metadata** — returns real width/height/mime/license for existing files; works under throttle.
2. **`Special:FilePath` redirect** — `curl -sI "https://commons.wikimedia.org/wiki/Special:FilePath/<File name with spaces and commas>"` → **302** = file exists. Different host (commons.wikimedia.org), not throttled.
3. **Ranged GET after cooldown** — `curl -r 0-2047 -L -o /dev/null -w "%{http_code} %{content_type}"` → **206 + video/webm|image/jpeg|application/ogg** = serves actual media. Wait ~1–4 min for the window to clear, space 9–15 s apart.

### Pexels — search pages carry the payload

- `https://www.pexels.com/search/videos/<query>/` (URL-encode spaces). HTML contains:
  - Direct files: `https://videos.pexels.com/video-files/<id>/<id>-hd_1080_1920_30fps.mp4` (and `-hd_720_1280`, `-sd_360_640`, `-sd_540_960` variants; landscape is `hd_1920_1080`).
  - Titles: regex `"id":(\d{6,7}),[^}]{0,400}?"title":"([^"]{0,100})"`.
- Video pages `/video/<id>/` get Cloudflare-blocked after a few requests; search pages tolerate more. If a page 403s, back off 5–10 s or re-parse a saved copy.
- CDN answers `Range` (206 + Content-Range) — good for cheap verification.

### Pixabay — `_tiny` → `_large` swap

- Search page (`https://pixabay.com/videos/search/<query>/`) contains thumbnails `https://cdn.pixabay.com/video/YYYY/MM/DD/<id>-<ts>_tiny.mp4|.jpg`.
- Big file = same path with `_large.mp4` (200, 13–48 MB, ~1080p). `_hd.mp4` variants 403 — don't exist; don't chase.
- Titles: `"name":"..."` fields interleaved with brand entries; title of i-th video = `names[2*i+1]`.
- Rate-limits hard after 2–3 fetches — ≥10 s spacing, expect failures after a burst, retry minutes later.

### archive.org (footage)
- `advancedsearch.php` without `AND mediatype:movies` returns garbage. With the filter, no usable modern footage found for an India documentary (2026-08). Last resort for footage.

## License ladder for footage (report this to the user)

| License | Attribution? | Notes |
|---|---|---|
| CC0 / Public domain | No | Best. e.g. BMTC QR-scan still, Marine Drive CC0 stills, Bombay 1929 archival film |
| Pexels / Pixabay license | No | Free commercial, no attribution; not CC0 |
| CC BY 3.0/4.0 | Yes (author + link) | e.g. Mumbai Timelapse, Destination-Mumbai |
| CC BY-SA 3.0/4.0 | Yes + share-alike | e.g. ₹2000 note photos, Chandni Chowk, Marine Drive 8K, CST station |

- Commons footage is WebM/OGG only; transcode: `ffmpeg -i in.webm -c:v libx264 -crf 18 out.mp4`.

## Worked example — UPI India documentary trailer (scene-by-scene)

| Scene | Asset | URL | Res | License |
|---|---|---|---|---|
| QR payment close-up | BMTC Bengaluru QR-scan still | `https://upload.wikimedia.org/wikipedia/commons/9/90/Digital_Payments_initiative_-QR_Code_Scanning_by_BMTC_Bengaluru_in_Corona_Times_2020.jpg` | 3120×4160 | CC0 |
| QR on phone (video) | Pexels 8384432 "QR Code on a Smartphone" | `https://videos.pexels.com/video-files/8384432/8384432-hd_1080_1920_30fps.mp4` | 1080×1920 | Pexels |
| Digital payment (video) | Pexels 6763343 "Bill Payment for Dental Care" | `https://videos.pexels.com/video-files/6763343/6763343-hd_1080_1920_25fps.mp4` | 1080×1920 | Pexels |
| Currency ₹2000 | "A 2000 rupee note.jpg" | `https://upload.wikimedia.org/wikipedia/commons/4/47/A_2000_rupee_note.jpg` | 4608×2592 | CC BY-SA 4.0 |
| Mumbai aerial | "Timelapse at Marine Drive Mumbai.webm" | `https://upload.wikimedia.org/wikipedia/commons/5/5b/Timelapse_at_Marine_Drive_Mumbai.webm` | 1920×1080 | CC BY-SA 4.0 |
| Mumbai street (video) | Pixabay 139848 Mumbai road traffic | `https://cdn.pixabay.com/video/2022/11/21/139848-773444714_large.mp4` | ~1080p, 44 MB | Pixabay |
| Mumbai still | Marine Drive CC0 | `https://upload.wikimedia.org/wikipedia/commons/6/69/Marine_Drive_Mumbai_%281%29.jpg` | 3060×4080 | CC0 |
| Indian market (video) | Narayantala Bazaar, Bengal | `https://upload.wikimedia.org/wikipedia/commons/4/4b/Narayantala_Bazaar_Area_-_Basanti-Malancha_Highway_-_SH_3_-_Kultali_-_South_24_Parganas_2016-07-10_4670.ogv` | 1920×1080 | CC BY-SA 3.0 |
| Indian market (still) | Chandni Chowk bazaar | `https://upload.wikimedia.org/wikipedia/commons/3/32/A_bazaar_in_Chandni_Chowk%2C_Delhi.JPG` | 5184×2912 | CC BY-SA 4.0 |
| Train station | Mumbai CST station | `https://upload.wikimedia.org/wikipedia/commons/0/08/Chhatrapati_Shivaji_Maharaj_Terminus_2022_Dec.webm` | 1280×720 | CC BY 4.0 |
| Train station 4K alt | Ghum, Darjeeling | `https://upload.wikimedia.org/wikipedia/commons/c/c1/Ghum_Railway_Station%2C_Darjeeling_01.webm` | 3840×2160 | CC BY 3.0 |
| Archival beat | Street Scenes in Bombay 1929 (real sound) | `https://upload.wikimedia.org/wikipedia/commons/e/e9/Street_Scenes_in_Bombay%2C_India_%28real_sound%29%2C_Jan_1929.webm` | 1280×720 | PD |

Not found (as of 2026-08): usable "street vendor with QR" or "hands paying by phone" footage on free sources; Pexels QR clips are portrait-only; Pixabay "qr code" search 403'd during the hunt.
