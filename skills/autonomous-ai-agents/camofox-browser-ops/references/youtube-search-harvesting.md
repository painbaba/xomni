# YouTube Search / Channel Harvesting (verified flow, 2026-08)

Collecting structured video data (title, channel, videoId, views, published, length)
from YouTube search result pages and channel grids, then batch-verifying URLs live.

## Why this exists

Search-page snapshots truncate (~200 lines) and the accessibility tree loses
metadata. The reliable route is extracting from `window.ytInitialData` via
`browser_console` JS, then verifying every URL via oEmbed.

## 1. Extract videos from a search results page

Navigate to `https://www.youtube.com/results?search_query=<url-encoded>` (browser
or curl — `ytInitialData` is embedded in the raw HTML either way; curl fetch of a
search page returns ~1.5MB HTML containing `ytInitialData` and `videoRenderer`).

Run this in `browser_console` (single line — multiline strings get mangled):

```js
(() => { const out = []; const walk = (n) => { if (!n || typeof n !== 'object') return; if (n.videoRenderer) { const v = n.videoRenderer; out.push({t: (v.title?.runs?.map(r=>r.text).join('') || v.title?.simpleText || ''), c: (v.ownerText?.runs?.map(r=>r.text).join('') || ''), id: (v.videoId || ''), v: (v.viewCountText?.simpleText || v.viewCountText?.runs?.map(r=>r.text).join('') || ''), p: (v.publishedTimeText?.simpleText || ''), l: (v.lengthText?.simpleText || '')}); } for (const k in n) { if (k !== 'videoRenderer') walk(n[k]); } }; walk(window.ytInitialData); return JSON.stringify(out); })()
```

Result: JSON array of `{t, c, id, v, p, l}` — URL = `https://www.youtube.com/watch?v=<id>`.
Works for `@channel/search?query=` pages too (they use the same videoRenderer shape).

## 2. Channel videos grid — DIFFERENT SCHEMA (pitfall)

`https://www.youtube.com/@handle/videos` does NOT contain `videoRenderer`.
It uses `lockupViewModel` (`hasVideoRenderer:false`, `hasLockup:true`). Use:

```js
(() => { const out = []; const walk = (n) => { if (!n || typeof n !== 'object') return; if (n.lockupViewModel) { const l = n.lockupViewModel; const title = l.metadata?.lockupMetadataViewModel?.title?.content || ''; const id = l.contentId || ''; const rows = l.metadata?.lockupMetadataViewModel?.metadata?.contentMetadataViewModel?.metadataRows || []; const rowTxt = rows.map(r => r.metadataParts?.map(p => p.text?.content || '').join(' ')).join(' | '); out.push({t: title, id, m: rowTxt}); } for (const k in n) { if (k !== 'lockupViewModel') walk(n[k]); } }; walk(window.ytInitialData); return JSON.stringify(out.slice(0, 30)); })()
```

`m` = "6K views 2 days ago" style metadata row. Diagnostic shortcut: check
`JSON.stringify(window.ytInitialData)` for `videoRenderer` vs `lockupViewModel`
before writing the walker.

## 3. Batch URL verification via oEmbed

```bash
curl -sS "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>&format=json"
```

Batch with Python urllib (add `User-Agent` header, 0.15s sleep). 99/102 IDs
verified this way in one pass. Returns canonical `title` + `author_name` —
both the live-verification proof AND the canonical title (search titles can
carry em-dash suffixes).

**Quirk — oEmbed "Unauthorized"**: some videos (region/embed-restricted) return
`Unauthorized` from oEmbed. That does NOT mean the video is dead — verify those
by rendering the watch page (`browser_navigate` to the watch URL and confirm the
`<h1>` title + channel). Don't drop them from the report. If watch pages are
blocked (429 / captcha), use the exact-title search fallback in §6.

## 4. Pitfalls

- **Browser backend flakiness**: `browser_navigate` can fail with connection
  timeout while curl works. Check Camofox health (`curl :9377/health`) — idle
  shutdown is normal and relaunch takes 5-10s; retry the navigate.
- **Decoy handles**: e.g. `@AIJason` and `@HeyitsJason` are NOT the real "AI
  Jason" (`@AIJasonZ`). Before trusting a channel page, confirm subscriber
  count / description matches, or search the channel name quoted and check the
  channel result block (`@handle` + subs are shown there).
- **Channel search pages** (`@handle/search?query=`) use the search results
  schema (videoRenderer), NOT the grid schema — easy to confuse with /videos.
- **View counts drift** between page renders (e.g. 47,308 → 47,316). Always
  note "as shown at capture time" in the report.
- **Shorts shelves** appear as `reelItemRenderer` on search pages — same walker
  with a second branch if shorts matter.
- **Snapshots truncate**: never parse the accessibility snapshot for data —
  always go through the console JS extractor.

## 5. Python batch-harvest pattern (mega-hunts, 15+ queries)

The JS walker above runs in `browser_console`, but for bulk hunts fetch search
HTML directly with urllib/curl and parse in Python. Proven pipeline (124-video
hunt, 2026-08): `harvest.py` (fetch each query URL with Firefox UA → regex
`var ytInitialData = (\{.*?\});</script>` → json.loads → walk) → relevance filter
+ dedupe by videoId → batch oEmbed → grouped report.

- **CRITICAL Python port bug**: JS `for...in` iterates array indices too, so the
  JS walker recurses into lists. A Python port that only does
  `for k, v in node.items()` silently skips every list value → **0 videos**
  extracted from pages that visibly contain 20. Fix: handle lists first —
  `if isinstance(node, list): for item in node: walk(item); return`.
- **Relevance filter**: raw queries return 20 videos each but only ~30% are
  on-topic. Filter on title+channel matching an ecosystem regex
  (`claude|mcp|model context protocol|agent`) AND a domain regex
  (`video|remotion|ffmpeg|elevenlabs|comfyui|manim|after effects|...`), then
  dedupe by videoId across all queries.
- **Rate-limit asymmetry**: watch pages start 429ing while search pages keep
  returning full HTML on the same IP; stagger fetches 1.5-4s and re-verify
  search pages via curl when browser/urllib routes get throttled.
- Store intermediate JSON at each stage (`search_results.json`,
  `candidates.json`, `final_verified.json`) so a throttled re-run only redoes
  the failed piece.

## 6. Verification fallbacks when watch pages are blocked

Watch-page rendering (the §3 fallback) can itself be blocked: curl gets
`429 Too Many Requests` on `youtube.com/watch` while search pages still work;
the Camoufox browser can land on a `google.com/sorry` captcha wall for watch
URLs. Routes that do NOT rescue you (don't burn turns on them): the
`/embed/<id>` page serves a generic "YouTube" `<title>` with no static metadata;
noembed.com mirrors inherit YouTube's 401; Invidious instances may be
unreachable from the network.

What DOES work — exact-title quoted search re-verification:
1. Fetch `results?search_query="<the full title in quotes>"` (curl works when
   watch pages 429).
2. Confirm the same videoId appears with matching channel + views.
3. Two independent renders = live verification; view-count drift between them
   (e.g. 3,779 → 3,790) is itself a liveness proof.
4. **Dead-ID detection**: if the exact-title search returns a DIFFERENT videoId
   with the same title, the captured ID is likely deleted/private — oEmbed-verify
   the replacement, swap it into the report, and note the swap. (Observed: an
   Andy Diep DaVinci-Resolve ID came back dead; the same title was now held by a
   Jason Cooperson video, oEmbed-verified.)

## 7. Channel discovery & handle correction

- Search results carry `channelRenderer` blocks (`canonicalBaseUrl`) — parse
  them to confirm exact handles instead of guessing (guesses 404: `cole-medin`
  → correct is `@ColeMedin`; `worldofai` → wrong handle entirely).
- `@handle/videos` grids only expose ~30 most-recent uploads (and use the
  `lockupViewModel` schema); for topical content, `@handle/search?query=<topic>`
  (videoRenderer schema) surfaces the relevant back-catalog and is usually more
  fruitful for curation.
