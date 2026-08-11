# Coinglass scraping notes (verified Aug 2026)

## Routing
- Direct deep links 404: `/LiquidationData`, `/LiquidationHeatMap`, `/liquidations`
  (plain GET). The SPA only mounts the route when the nav "Liquidation" link is
  clicked from `https://www.coinglass.com/`. After navigating, `window.location.href`
  reads `https://www.coinglass.com/liquidations` but a fresh GET still 404s.
- Workflow: navigate to homepage → click nav link → snapshot/page state is live.

## Auth-gated APIs (return `{"code":"0","msg":"success","success":true}` with NO data key)
Even a same-origin browser `fetch()` with session cookies returns no data:
- `https://capi.coinglass.com/api/coin/liquidation`
- `https://capi.coinglass.com/api/coin/liq/heatmap?time=h1&type=coin`
- `https://capi.coinglass.com/api/futures/liquidation/order?volUsd=&symbol=&exName=&pageNum=1&pageSize=1000`
- `https://capi.coinglass.com/api/futures/liquidation/maxOrder`
- `https://capi.coinglass.com/api/futures/liquidation/ex/info?time=h4&symbol=`
- `https://capi.coinglass.com/api/futures/liquidation/chart?symbol=&timeType=4&range=90d`
Do not chase these; scrape the rendered page instead.

## What the rendered page exposes (all verified extractable)
- `document.body.innerText` slices (page text is dense; slice around markers):
  - `"Liquidation Heatmap"` → per-coin 1h/4h/12h/24h liquidation totals list
    (top coins show `$` values, e.g. `BTC $24.24M`; coins below display
    threshold show no value — those are small, treat as <$50K for the 1h tab).
  - `"24h Rekt"` → window totals: `$168.31M` / `Long $55.42M` / `Short $112.89M`
    (order: total, Long, Short — same for 1h/4h/12h).
  - `"According to CoinGlass data, In the past 24 hours, N traders were liquidated"`
    → trader count; next line = largest single order (exchange + symbol + $).
  - `"Exchange Liquidations"` → per-exchange 4h breakdown (Binance usually
    ~60% of total; the Rate column is share-of-total, Long% is long share).
  - Live liquidation-order feed rows: symbol, price, qty, notional $, HH:MM:SS
    time (browser-local timezone — compare against the server `Date` header to
    convert to UTC).
- Homepage (`/`) gives global aggregates in the banner: 24h Volume, OI,
  **24h Liquidation $ + % change**, 24h Long/Short %, Fear & Greed, BTC
  dominance, CME OI, funding rates per exchange, top-trader L/S widgets.

## UI interaction
- Window tabs ("1 hour / 4 hour / 12 hour / 24 hour") are MUI tabs: click the
  element with `[role=tab]` whose text matches. Clicking leaf `<div>`s does
  nothing. After switching, re-read `innerText` (values refresh).
- The SPA can hard-crash under rapid JS-driven clicks (title/body go empty).
  Recover by navigating to the homepage and re-clicking the nav link.
- Price-level liquidation heatmap (canvas) is a PRO feature — no data in DOM,
  no ECharts instance attribute (`_echarts_instance_`), no iframes. Not
  extractable on the free tier. Cite news-reported cluster levels instead,
  labeled as documented levels rather than verified heatmap data.

## Known-adjacent blocks
- `coinalyze.net/bitcoin/liquidation-heatmap/` — Cloudflare "You have been blocked".
- Decrypt article bodies — Cloudflare challenge ("Just a moment...").
