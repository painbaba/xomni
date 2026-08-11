# India E-Commerce Platform Notes (verified Aug 2026)

Per-platform state for price research. URL patterns that work, filters, and refurbished reality.

## Amazon.in
- Search with price filter (paise, i.e. rupees x 100): `https://www.amazon.in/s?k=<query>&rh=p_36%3A<min>-<max>`
  - Rs 1,000-1,500 = `p_36%3A100000-150000`
- Sort by price ascending: add `&s=price-asc-rank`
- Product page: `https://www.amazon.in/dp/<ASIN>` (works, redirects to `?th=1`)
- Sale events: Great Freedom Sale (Aug), Prime Day — prices change intra-day; Smartprix "last changed" date confirms live drops.
- Free delivery + COD widely available; open-box delivery option exists at checkout for some sellers — recommend it for QC-risk brands (test both speakers/ANC on the spot).

## Flipkart
- Search: `https://www.flipkart.com/search?q=<query>` — results render in accessibility tree fine via Camofox.
- Price filter via URL facets is fiddly — easier to filter in-page or just scan results.
- Exchange offers ("Up to Rs 500 off on Exchange") can drop price below both platforms' listing price if user has old electronics — the ONLY legit way under the market floor.
- Refurbished program: DEAD. `/refurbished` and `/refurbished-store` both return "page moved or deleted" (verified). "Refurbished" keyword search returns only junk brands (GUGGU/YAROH/FRONY at Rs 441-626) with fake ANC claims.

## Amazon Renewed / Warehouse (India)
- Renewed storefront exists at `amazon.in/renewed` (node 91144288031) but headphone inventory is ZERO. Even unfiltered search with condition filter `p_n_condition-type%3A6790255031` returns "No results" for headphones. Phones/laptops only.
- Warehouse Deals (open-box hub): `amazon.in/gp/warehouse-deals/` = 404. Not offered in India.
- Conclusion: refurbished premium audio (Sony/JBL/Bose) effectively does not exist on Indian marketplaces. US YouTube "renewed deals" content does not apply.

## Other platforms (for the "compare top 5" sweep)
- **Meesho**: `meesho.com/search?q=<exact model>` — fuzzy search returns irrelevant junk for niche products; check the heading matches the model name.
- **Snapdeal**: `snapdeal.com/search?keyword=<q>` — mostly dead; generic white-label brands only (VERONIC etc.). Branded audio rarely present.
- **Myntra**: `myntra.com/<brand>?rawQuery=<q>` — no pTron-style budget audio; mostly fashion/stationery. Quick 404/"no results" check suffices.
- **Tata CLiQ**: search often renders empty (JS) — treat as "not sold" unless product page URL known.
- **Reliance Digital**: `reliancedigital.in/search?q=<q>` can 404 on search; check `/sections/audio` instead.
- **Croma**: blocks curl (403). Use browser; location popup needs pincode entry (type + Continue). Brand search (`/searchB?q=<brand>%3Arelevance&text=<brand>`) works but budget brands often absent.
- **Brand's own site** (e.g. ptron.in): Shopify-based; search URL `ptron.in/search?q=<q>&type=product` may render empty; many budget brands are marketplace-exclusive (V2 not on ptron.in). Check but don't expect it.

## Used market (only real one)
- **OLX**: `olx.in/items/q-<query>` — works, real second-hand premium ANC (JBL Tune 770NC used Rs 2,600-3,300; Sony WH-CH720N used Rs 6.5-7.8K). No buyer protection, local pickup, scam risk — present as risk call, not shopping call. Sub-1.5K OLX "ANC" listings are junk brands.

## Price history trackers (India)
- **Smartprix** (`smartprix.com`) — THE tool. Product pages (e.g. `/mobile_headphones/<slug>-ppd1pr1cygov`) show: current price, % drop, rupee drop in last month, last-changed date, lowest-price store, "NEW (1) From" offers. Search: `smartprix.com/products/?q=<query>`.
- CamelCamelCamel: does NOT support amazon.in (domain doesn't resolve / fails). Skip.
- Keepa: supports Amazon.in but requires login + anti-bot. Skip for quick checks.
- Wayback Machine: almost never has captures of Indian product listings (checked: empty).
- Smartprix graph data loads via JS; summary text on the page is the reliable extractable data.

## Opening a page in the user's Chrome (Windows / git-bash)
- `cmd //c start "" "<url>"` silently fails (returns to prompt, nothing opens).
- Use: `"/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window "<url>"` — prints "Opening in existing browser session", detaches on its own. No `&` needed.
- Edge fallback: `/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`.
