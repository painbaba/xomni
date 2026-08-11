# India Price-Research Tool Map (verified Aug 2026)

Per-platform status, URL patterns, price-history tools, and review recipes.
All verified live during the "best ANC headphones under Rs 1,500" research run.

## Platforms — what actually carries budget electronics

| Platform | Carries budget D2C audio? | Notes |
|---|---|---|
| Amazon.in | YES | Primary. Open-box delivery + 10-day replacement options; biggest rating volumes. |
| Flipkart | YES | Same price usually; "Up to Rs X OFF on Exchange" = the only legit way below shelf price. Fewer reviews. |
| Meesho | No | Fuzzy search returns unrelated junk for branded models. |
| Snapdeal | No | Effectively dead for branded electronics; only generic brands (VERONIC etc.). |
| Myntra | No | No pTron-class budget audio catalog. |
| Tata CLiQ | No | Search renders nothing for budget models. |
| Reliance Digital | No | Search URL pattern often 404s; premium brands only. |
| Croma | No | Blocks curl (403); JS search returns irrelevant categories for budget brands. |
| Brand's own site | Sometimes | Marketplace-exclusive models often absent (ptron.in: only old wired stock). Verify. |
| OLX | Used market | Real branded used gear at 40-60% of new. No protection; meet-and-test; city-bound. |

## Amazon.in URL patterns

- Price-filtered search (p_36 is in PAISE — Rs X-Y = `X00`-`Y00`):
  `https://www.amazon.in/s?k=<query>&rh=p_36%3A<min>00-<max>00`
  e.g. Rs 1,000-1,500 → `rh=p_36%3A100000-150000`
- Cheapest-first sort: append `&s=price-asc-rank`
- Renewed-only condition filter:
  `https://www.amazon.in/s?k=<query>&rh=p_n_condition-type%3A6790255031`
  (keyword "refurbished" ≠ Renewed filter — keyword returns NEW items)
- Warehouse Deals (`/gp/warehouse-deals/`): NOT available in India (404).
- Snapshot truncation: full browser snapshot saved at
  `C:\Users\HP\AppData\Local\hermes\cache\web\browser-snapshot-<hash>.txt` —
  read_file it in chunks.

## Price-history tools for Amazon.in

- **Smartprix** (smartprix.com) — WORKS. Search `/products/?q=<query>`; product
  page shows: current price, "% dropped by Rs X in one month", and
  "price last changed on <date>". The last-changed date is the sale-timing
  tell (e.g. pTron Studio Urban V2: Rs 1,647 → Rs 1,299, 27% drop, changed on
  the Freedom Sale day itself = all-time low).
- CamelCamelCamel: does NOT support Amazon.in (India outside coverage). Skip.
- Keepa: covers Amazon.in but login + anti-bot wall. Skip for quick checks.
- Wayback Machine: no captures of fresh marketplace listings. Skip.

## YouTube review cross-check (via OpenCLI)

```bash
opencli youtube search "<product> review" --limit 8
opencli youtube transcript "https://www.youtube.com/watch?v=<id>" --format plain
opencli youtube video "https://www.youtube.com/watch?v=<id>" --format plain
```

- Transcript fails on no-caption videos with
  `Caption URL returned empty response` — fall back to `video` (description +
  keywords confirm model/price/claims).
- Search for multi-product comparisons ("I tested 7 budget X under Rs Y") —
  they give relative verdicts single reviews can't.
- Reviewers buying at the sale price name the price in description/title —
  use it to confirm the tracked low, not as a price source by itself.

## Session example (Aug 2026)

pTron Studio Urban V2 (40dB ANC, BT 6.0): Rs 1,299 all-time low on Amazon.in +
Flipkart (tracked via Smartprix, dropped Rs 348/27% that week). No
refurbished path exists in India for it. Color-variant trap verified: the
Rs 795 "Black" variant on the same listing family is the Studio Evo — no ANC.
