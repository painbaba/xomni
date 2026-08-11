---
name: crypto-derivatives-research
description: "Use when researching crypto liquidation pools, OI, funding."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [crypto, derivatives, liquidations, coinglass, binance, whale, research]
    related_skills: [web-research, data-collection-strategy]
---

# Crypto Derivatives & Liquidation Research

Live-verified research on crypto futures markets: liquidation clusters/heatmaps, open interest, funding, long-short positioning (whales vs retail), and recent liquidation events for majors (BTC/ETH/SOL) or any USDT-margined symbol.

## When to use
- "Where are the liquidation pools / what got liquidated / is the market over-leveraged / whale long-short positioning on X"
- Any request citing Coinglass, Binance futures data, or liquidation heatmaps.
- The user requires live-web-verified numbers with URLs (see Deliverable format — non-negotiable for this user).

## Data sources, in order of reliability

### 1. Binance public futures API (no key, curl-able)
Base `https://fapi.binance.com`. Works from most IPs:
- `/fapi/v1/ticker/24hr?symbol=BTCUSDT` — price, 24h range, volume
- `/fapi/v1/openInterest?symbol=X` — OI in coins (× mark price = USD OI)
- `/futures/data/openInterestHist?symbol=X&period=1d&limit=7` — OI trend (leverage building or flushing)
- `/fapi/v1/premiumIndex?symbol=X` — mark/index price + current funding
- `/fapi/v1/fundingRate?symbol=X&limit=15` — funding history (8h intervals)
- `/futures/data/topLongShortPositionRatio?symbol=X&period=1h` — TOP TRADER (whale) account/position split
- `/futures/data/globalLongShortAccountRatio?symbol=X&period=1h` — ALL accounts (retail skew)
- `/futures/data/takerlongshortRatio?symbol=X&period=1h` — aggressive buy vs sell volume

**Geo-block trap:** `/futures/data/allForceOrders` and `/futures/data/forceOrders` frequently return HTTP 404 via CloudFront (geo-blocked). Do NOT burn time retrying — use the WebSocket tap below instead.

### 2. Binance live force-order WebSocket (the liquidation tap)
`wss://fstream.binance.com/ws/!forceOrder@arr` is PUBLIC and usually works even when the REST forceOrders endpoints are blocked. Run `scripts/binance_forceorder_ws.py` (needs `pip install websockets`).
- Filter for your symbols; each message has side, price, qty, notional.
- **Also a live-activity gauge:** 0 prints across all symbols in ~40s = no cascade running right now. State that explicitly ("no liquidation activity observed live").

### 3. Coinglass (heatmap/aggregate data) — page-scrape, don't fight the API
- **Routing quirk:** deep links like `/LiquidationData` and `/LiquidationHeatMap` 404; the real page is `/liquidations`, reachable ONLY by clicking the "Liquidation" nav link from the homepage (SPA client-side routing; direct deep-links fail). Re-navigate via `https://www.coinglass.com/` → click nav.
- **APIs are auth-gated:** `capi.coinglass.com/api/coin/liquidation`, `/api/coin/liq/heatmap`, `/api/futures/liquidation/order`, `/api/futures/liquidation/maxOrder` all return `{"code":"0","msg":"success","success":true}` with NO `data` key without login — even via same-origin browser `fetch()` with cookies. Don't chase them.
- **What the rendered page gives you (verified extractable):** per-window Rekt totals (1h/4h/12h/24h with Long/Short split), trader count, largest single order (exchange + symbol + $), per-coin 24h liquidation totals (list under "Liquidation Heatmap" heading), exchange breakdown, live liquidation-order feed (symbol, price, notional, time). Extract via accessibility snapshot or `document.body.innerText` slices around "24h Rekt" / "Liquidation Heatmap".
- **Price-level heatmap canvas is PRO/paywalled** — the cluster-by-price data is NOT extractable from the free page. Quote documented cluster levels from news analysis instead and LABEL them as "documented reference levels, not verified heatmap data".
- Tab switching: click elements with `[role=tab]` whose text matches (e.g. "24 hour"); clicking leaf divs does nothing. MUI tabs.
- The SPA can crash (body empties) after aggressive JS-driven clicks — re-navigate from homepage and re-snapshot.

### 4. News verification (dated headlines + bodies)
- **Google News RSS** `https://news.google.com/rss/search?q=KEYWORDS+when:7d&hl=en-US&gl=US&ceid=US:en` — dated headlines with source names; gold for liquidation/cluster articles with numbers in the headline (e.g. CryptoRank "$65,763 → $202.6M short liqs"). Redirect links need JS to resolve; cite the headline + source + date + the RSS query URL instead of chasing article bodies.
- Work: Cointelegraph `/rss` + article pages (parse `<p>` tags), AMBCrypto feed + articles, CryptoPotato feed + articles, CryptoRank `/news/feed/<slug>` list + articles.
- Blocked (report, don't fight): Decrypt article bodies (Cloudflare "Just a moment..."), Coinalyze heatmap (Cloudflare), CoinDesk JSON feed (`/arc/outboundfeeds/rss/?outputType=json` returned non-JSON; plain RSS route exists).
- Corroborate exchange API prices against a news recap (spot vs futures basis check).

## Deliverable format (user requirement)
Plain English, exact numbers, and a **LIVE-VERIFIED FACTS** section at the end listing EVERY URL fetched (API endpoints, RSS feeds, article pages). For every blocked page, say so explicitly. NEVER assert market numbers from training memory — if unverified, label it derived/estimated.

## Pitfalls
- **browser_console on Windows mangles shell metacharacters** in expressions: `&`, `|`, `||`, `&&` break parsing (cmd-style errors). Workarounds: build URLs with `String.fromCharCode(38)` instead of `&`; never use `||`/`&&` (chain with separate statements); stage async fetch results on `window.__x` in one call and read them in a second, simple call; keep expressions single-line, avoid parens around single-arg arrows.
- Windows python cannot open MSYS `/tmp/...` paths — write scripts to `C:\Users\<user>\...` via write_file, then run.
- Funding near zero + retail long-heavy (global account ratio ~2.0 on alts) = downside long-liquidation risk skew; 24h vs 4h Rekt Long/Short splits reveal the recent flush direction (short-heavy 24h + long-heavy 4h = rally then pullback).
- OI in coin terms vs USD terms diverge in bear markets — check both (e.g. SOL OI +9% in coins while price falls = leverage building into weakness).
- Liquidation totals vary by exchange; label Binance-only vs Coinglass (all-exchanges) figures.

## Support files
- `scripts/binance_forceorder_ws.py` — live Binance liquidation tap (WS force-order stream; filter by symbol, counts activity).
- `references/coinglass-scraping.md` — Coinglass routing quirks, auth-gated endpoints, and the exact page-strings to slice.
