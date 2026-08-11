# YouTube channel research without the browser (validated Aug 9, 2026)

Purpose: pull subscriber counts, video counts, total views, join date, video-length distributions, recent video titles, and creator tool/process disclosures via plain urllib/curl — no browser, no API key. Used to reverse-engineer 12 faceless-documentary channels in one session.

## 1. Channel About page (identity + stats)

- URL: `https://www.youtube.com/@<handle>/about` — handles work; legacy `/user/...` URLs often 404 (e.g. `youtube.com/user/coldfusiontv` → 404).
- Headers: Chrome desktop UA + `Accept-Language: en-US,en;q=0.9`.
- Parse: find `var ytInitialData = `, brace-match to the closing `}`, `json.loads` (same trick used for watch pages).
- **Channel's OWN stats** — walk `aboutChannelViewModel` (first occurrence):
  - `subscriberCountText` — now a **plain string** ("5.2M subscribers"), NOT `{"simpleText":...}` and NOT the accessibility-wrapped form used on related-channel nodes.
  - `videoCountText` (runs), `viewCountText`, `joinedDateText`.
- **Channel's OWN identity** — walk `channelMetadataRenderer`: `title`, `description` (full text — tool disclosures can live here, e.g. Infographics Show's "Software that we use: Adobe Audition… Illustrator… After Effects…"), `externalId` (the channel's own UC-… ID), `vanityChannelUrl`.
- Trap: the FIRST `"channelId":"UC..."` regex hit in an about page is usually a **related/recommended channel** (this session: grabbed "ColdFusion Music" and a squatter instead of the real channels). Always use `externalId` from `channelMetadataRenderer`.

## 2. Handle squatters — verify identity, never trust a handle

Found Aug 2026:
- `@fern` = 41-sub squatter; the real 5.2M-sub documentary Fern is **`@fern-tv`** ("Armchair documentaries, almost weekly. Made by @Simplicissimus").
- `@ColdFusionTV` = squatter selling the handle ("Only selling it to coldfusion officials"); the real channel is **`@ColdFusion`** (Dagogo Altraide, 5.23M).

Procedure: (a) about-page title+description must match expectations; (b) if not, find the real channel via YouTube search: fetch `https://www.youtube.com/results?search_query=<terms>` and walk `channelRenderer` (title + subscriberCountText). Note the search page can itself be a lazy shell — if `channelRenderer` is absent, fall back to `browser_navigate` on the same URL.

## 3. Video lists + lengths via the innertube browse API (still works Aug 2026)

- The `/videos` tab HTML is a **lazy shell**: ytInitialData contains NO `videoRenderer`/`lengthText` (only tab stubs + a ~30KB JSON). Do NOT regex the page for durations.
- POST `https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8` (the web-client key, still valid) with:
  ```json
  {"context":{"client":{"clientName":"WEB","clientVersion":"2.20240701.00.00","hl":"en","gl":"US"}},"browseId":"<UC...>","params":"EgZ2aWRlb3PyBgQKAjoA"}
  ```
  `params` = the Videos tab. `browseId` = the channel's `externalId` from §1.
- Response items are now **`lockupViewModel`**, NOT `videoRenderer`:
  - `contentId` = videoId; keep only `contentType == "LOCKUP_CONTENT_TYPE_VIDEO"` (filters Shorts/etc.).
  - Title: `metadata.lockupMetadataViewModel.title.content`.
  - Duration: `rendererContext.accessibilityContext.label` — e.g. "Exposing a $1,900,000,000 Pharma Company 44 minutes". Parse with `(\d+) hour[s]?(?: (\d+) minute[s]?)?` / `(\d+) minute[s]?` / `(\d+) second[s]?`.
  - Views / published-ago: walk `metadataRows` texts.
- Returns the ~30 most recent long-form videos → compute min/median/max lengths for a channel (these became the playbook's length tables).

## 4. Innertube search (creator interviews, process videos)

POST `https://www.youtube.com/youtubei/v1/search?key=<same key>` with `{"context":{...same...},"query":"<q>"}`. Search results STILL use `videoRenderer` (title, `ownerText`/`longBylineText`, `videoId`, `lengthText`, `viewCountText`, `publishedTimeText`). Queries that work: "<channel> how I make my videos", "<channel> interview podcast", "<channel> behind the scenes". This surfaced David Perell's Johnny Harris interview, ColdFusion's "My Story", Dhruv Rathee's career video, editing-breakdown tutorials, etc. — better recall than news SERPs for creator-tools questions.

## 5. Watch pages: description mining = tool disclosures

- `https://www.youtube.com/watch?v=<id>` still returns `"shortDescription":"..."` inside ytInitialPlayerResponse — regex it, then `.encode().decode("unicode_escape")` to fix \u0026 etc.
- Verified examples (Aug 2026):
  - Johnny Harris "How I Got My Start in Video": *"I make maps using this AE Plugin: https://aescripts.com/geolay"* + "Tom Fox makes my music" — direct tool proof.
  - Fern "Hansa: The Infiltration of the Dark Web": credits **Artlist** tracks + Google-Docs source document + cited press (WIRED).
  - MagnatesMedia descriptions: "MagnatesMedia editing software: https://magnates.media/editing" + whop.com/editingcourse + magnatesmedia.com "YouTube Millionaire System".
  - Nexpo "The Internet's Deepest Rabbit Hole": *"Researched and written by Nexpo and Laura Holliday"* + pastebin sources + soundtrack playlist.
  - Dhruv Rathee "How to Start a YouTube Channel": chapters "My Setup / Filming Videos / Scripting for Videos / Editing Videos" — process disclosure in the description itself.
- Transcripts: **don't rely on third-party transcript services** — youtubetranscript.com returned "YouTube is currently blocking us from fetching subtitles" for every video this session, and caption baseUrls from watch pages came back empty. Descriptions + third-party breakdown videos are the reliable evidence channel.

## 6. Supporting web-search ladder (used when DDG/Bing HTML blocked)

- Bing News RSS: `https://www.bing.com/news/search?q=<q>&format=rss` — reliable curl backend; item `<link>` is `bing.com/news/apiclick.aspx?...&url=<urlencoded>` → `urllib.parse.unquote` the `url=` param = canonical publisher URL; fetching it with redirect-follow gets the article (mid-day interview resolved this way).
- Google News RSS: discovery only. Token links: `browser_navigate` the FULL token once, then `browser_console` → `window.location.href` — one of two resolved to the canonical (vox.com oral history); the other went `about:blank` (dead, don't retry).
- WordPress REST API for article URLs when `?s=` fails: `https://<site>/wp-json/wp/v2/search?search=<q>&per_page=5` — returned the exact Deadline URL (`deadline.com/?s=...` had given 0 links).
- Direct-slug guessing + Wayback fallback for old articles: Digiday slug guessed first-try; `http://archive.org/wayback/available?url=<slug>` as backup.

## 7. Environment notes

- Watch disk space: about/videos HTML probes are ~0.7–1.5 MB each — process in-memory (don't persist to scratch) or delete after extracting; a 100%-full C: drive breaks `write_file` with "No space left on device".
- Session outcome example: 12 channels fully profiled (subs/videos/views/joined + 30-video length stats) in ~6 API batches — see `faceless-documentary-playbook-2026.md`.
