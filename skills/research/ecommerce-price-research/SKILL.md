---
name: ecommerce-price-research
description: "Best/cheapest product research across Indian e-commerce."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [ecommerce, price-research, amazon, flipkart, cashify, refurbished, india, shopping]
---

# E-commerce Price Research (India)

Use when the user asks to find the best/cheapest product available in India
("find best cheapest headphones", "scrape Amazon/Flipkart for X", "go deeper,
scrape more websites", price-band comparisons, refurbished/second-hand hunting).
The user is budget-conscious and expects multi-platform scraping, not a single
search. "find best" + a hard budget cap = always filter by price first.

## Prereqs: browsing stack
Amazon.in and Flipkart block plain bots. Route through Camofox:
- Camofox server :9377 + Gemini rotation proxy :8790 (see `anti-block-browsing`
  skill for start commands and health checks).
- Hermes browser_* tools route via Camofox automatically (CAMOFOX_URL set).
- Both Amazon.in and Flipkart load clean through Camoufox (verified Aug 2026).

## Workflow
1. **Amazon.in with price filter**:
   `https://www.amazon.in/s?k=<query>&rh=p_36%3A<min>00-<max>00`
   NOTE: p_36 values are in PAISE — Rs 1,000-1,500 = `p_36:100000-150000`.
   Example that worked: `k=noise+cancelling+headphones&rh=p_36%3A100000-150000`.
2. **Flipkart**: `https://www.flipkart.com/search?q=<query>` — no reliable URL
   price param; use sidebar filters or just scan results (prices shown inline).
3. **Read full results**: browser_navigate returns a TRUNCATED snapshot. The
   full one is saved at
   `C:\Users\HP\AppData\Local\hermes\cache\web\browser-snapshot-<hash>.txt` —
   read_file it in chunks (offset/limit) to get all listings.
4. **Cross-check the same model on both platforms** — prices and ratings differ
   (e.g. JBL Tune 770NC was Rs 4,999 on both, but soundcore Q20i had 70K ratings
   on Amazon vs 10 on Flipkart → buy Amazon).
5. **Refurbished hunting** (verified Aug 2026 — India's refurb audio market is
   effectively DEAD; set expectations honestly, don't promise US-style
   "renewed at half price"):
   - Amazon Renewed condition filter: `rh=p_n_condition-type%3A6790255031`
     (combine with p_36 for a price cap). "Refurbished" as a KEYWORD search
     returns NEW items — you must use the condition filter. Verified: Renewed
     has ~ZERO headphone inventory in India (even with no price cap, and even
     for "Sony WH-CH720N renewed"). Amazon Warehouse Deals
     (`/gp/warehouse-deals/`) 404s on amazon.in — not available in India.
   - Flipkart refurbished program is DISCONTINUED — `/refurbished` and
     `/refurbished-store` are both dead pages. "Refurbished" keyword search
     = Rs 400-700 junk brands (GUGGU/YAROH/FRONY), not real stock. Do not
     trust it.
   - Cashify has NO headphones — `/refurbished-headphones` 404s; phones/
     laptops only. 2Gud (Tata's refurb marketplace) was flaky/down entirely.
   - The ONE working used market: **OLX** (`olx.in/items/q-<query>`). Real
     branded ANC at 40-60% of new (e.g. used JBL Tune 770NC Rs 2,600-3,300 vs
     Rs 4,999 new). No buyer protection, city-bound pickup, scam risk — meet
     and test before paying. Mention it only when the user is willing to
     gamble; flag it as a risk call, not a shopping call.
   - **Flipkart exchange** ("Up to Rs X OFF on Exchange") is the only
     legitimate way BELOW the tracked low — trade old electronics, can beat
     shelf price by 20-40%.
6. **Track price history** (see `references/india-price-tools.md`):
   - **Smartprix is the working tracker for Amazon.in.** Product page shows
     current price, % drop in last month, and "price last changed on <date>".
     The last-changed date is the sale-timing signal (e.g. dropped Rs 348/27%
     on Freedom Sale day itself → all-time low, buy now).
   - CamelCamelCamel does NOT support Amazon.in (India not in coverage) —
     don't waste time there. Keepa covers Amazon.in but is login+anti-bot
     walled. Wayback usually has no captures of fresh marketplace listings.
7. **Cross-check YouTube reviews** (via OpenCLI, see
   `references/india-price-tools.md` for exact commands):
   `opencli youtube search "<product> review" --limit 8`, then
   `opencli youtube transcript <url>` for the verdict. Transcripts fail on
   no-caption videos ("Caption URL returned empty response") — fall back to
   `opencli youtube video <url>` whose description/keywords confirm model,
   price and claims. Multi-product comparison videos ("I tested 7 budget X
   under Rs Y") give relative verdicts that single reviews don't.
8. **Verify before recommending**: open the product page (dp/<ASIN>) and confirm
   the headline claim (real ANC vs ENC, dB spec, battery, warranty, seller,
   rating count). Check COLOR VARIANTS on the same page — same family,
   different SKUs often have wildly different prices/specs (e.g. pTron Urban V2
   Onyx Rs 1,299 vs older Urban Black Rs 795 — the cheap variant is a
   DIFFERENT model with no ANC; open each variant's ASIN and read its title).
9. Deliver a verdict table-style in plain text: top pick, runner-up, cheapest,
   step-up tier, and an explicit "avoid / fake" list.

## Pitfalls
- **ENC ≠ ANC.** "ENC"/"ENx" = microphone noise filtering for CALLS; it does
  NOT block sound reaching your ears. boAt, Noise, JBL budget, and pTron all
  label ENC products "noise cancelling". Filter these out when the goal is
  blocking loud surroundings.
- **Under ~Rs 2,000 real ANC effectively doesn't exist in India.** Claims at
  Rs 400-1,500 (JPGC/GUGGU/YAROH/FRONY/SGM) are fake/marketing. Cheap TWS
  "ANC" under Rs 2K is also weak — over-ear + real ANC is the only reliable
  answer for loud environments.
- **Passive isolation beats cheap ANC**: over-ear closed-back with thick pads,
  or certified ear muffs (NRR/SNR rated, e.g. NRR 26dB at Rs 1,200) block more
  loud sound than any sub-2K ANC headphone — at the cost of no audio.
- **Sales shift prices daily** (Freedom Sale, Big Billion Days). Live-scrape
  every session; never quote yesterday's price as today's.
- **"Top 5 platforms" reality check (India)**: Amazon.in + Flipkart carry
  nearly all budget electronics. Meesho/Snapdeal/Myntra/Tata CLiQ/Reliance
  Digital/Croma mostly DON'T stock D2C budget models (searched live: all
  returned nothing or irrelevant categories for a Rs 1,299 pTron). Don't
  platform-hop for show — check Amazon+Flipkart first, then verify the rest
  only if the user insists.
- **D2C brand official sites can't be assumed**: marketplace-exclusive models
  (e.g. pTron Studio Urban V2) are often NOT on the brand's own site
  (ptron.in search returned only old wired stock). Verify before promising
  "check the official store".
- **Opening a page in the user's Windows browser**: `cmd //c start "" "<url>"`
  can silently do nothing. Working pattern:
  `"/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window "<url>"`
  (prints "Opening in existing browser session"). Do NOT append `&` — the
  terminal tool blocks shell backgrounding; Chrome detaches on its own.
- **Camofox intermittent 500 on `/tabs`** after many navigations: check
  `/health` (server fine, tabs accumulate), then retry the navigate once.
- **Croma/Reliance Digital block curl** (403 / 404 search URLs) and often
  don't stock budget brands anyway — browser-only, low priority.
- **Sponsored results pollute page 1** on both platforms — read past the first
  few items; "Only few left" on unknown brands = junk listing signature.
- If a user interrupts mid-scrape, don't treat it as failure — they usually
  want to add a constraint (budget, condition). Resume with the new filter.

## References
- `references/headphones-india-2026.md` — full headphone market snapshot
  (models, live prices, ratings, verdicts, avoid list) from Aug 2026 research.
- `references/india-price-tools.md` — platform map (which sites carry budget
  stock), Amazon URL/filter patterns, price-history tools (Smartprix works,
  CamelCamelCamel doesn't cover India), YouTube review command recipes.
