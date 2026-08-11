# YouTube Video Hunt — verified recipe (Aug 2026)

Use when the user asks to "hunt YouTube for X" (e.g. how Claude Code makes
videos). Verified live 2026-08-09: one agent collected 71 verified videos
across 12 searches + 6 channel grids; every URL confirmed via oEmbed.

## The technique
1. RENDER search pages in a real browser: `https://www.youtube.com/results?search_query=<q>`
   — YouTube search pages DO load in a real browser (no login wall for top results;
   plain curl gets JS-shielded HTML). The Camoufox server (:9377) works; so does the
   standard browser toolset. Extract structured data from the page's `ytInitialData`
   JSON (videoRenderer entries: title, channel, videoId, viewCount, publishedTimeText).
2. CHANNEL PAGES use a different schema: newer pages expose `lockupViewModel`, not
   `videoRenderer` — write a second extractor for channel grids (youtube.com/@channel/videos).
3. VERIFY EVERY CANDIDATE via YouTube's oEmbed: `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>`
   — returns title+author JSON. This is the live-verification gate; every listed video
   must pass it. Some IDs return "Unauthorized" (region/embed restrictions) — verify
   those by rendering their watch pages directly. Never list an unverified URL.
4. Note: one oEmbed call per ~1s to avoid rate-limit "Unauthorized" responses.

## Query set that worked (Claude Code / agent-video topic)
`claude code video`, `claude code make video`, `claude code documentary`,
`claude code video generation`, `claude code after effects`, `claude code remotion`,
`claude code manim`, `claude code ffmpeg`, `AI agent creates youtube video`,
`claude code animation`, `faceless channel AI agent`, `claude code edit video`.
Known agent-content channels worth grid-scraping: Cole Medin, IndyDevDan, AI Jason,
David Ondrej, Theo (t3dotgg), Fireship.

## Deliverable shape
Ranked top-N list: exact title, channel, URL (youtube.com/watch?v=...), view count,
1-2 line workflow summary. Group into tiers (end-to-end pipelines / motion engines /
ffmpeg engineering / faceless-channel context). End with LIVE-VERIFIED FACTS
(every URL + how it was verified). Top finds Aug 2026: David Ondrej
"Claude Code can now make videos, here's how" (fOY0_WCR3eY), Jason Cooperson
"How I Fully Automated My Video Editing" (XeTAlZiIWHE — uses the HyperFrames
pipeline), Chronixel Remotion tutorial (oWkUwno6b0E).

## Pitfalls
- Browser backend may be unreachable at first — confirm the local Camofox server
  (:9377) is healthy and retry before declaring failure.
- Shorts shelves appear in search pages; filter or include explicitly per the ask.
- oEmbed is the source of truth for "is this video real" — search-page DOM alone can
  include promoted/duplicate entries.
