---
name: india-ecommerce-research
description: "Use when researching products/prices on Indian e-commerce."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [ecommerce, india, amazon, flipkart, olx, refurbished, price-research, shopping]
---

# India E-commerce Product Research

How to research products and prices across Indian marketplaces: Amazon.in,
Flipkart, OLX (used), and refurbished/renewed routes. Covers the URL
techniques that make searches work, which "hidden" storefronts actually
exist, and the category-knowledge rules for honest verdicts (ANC, etc.).

## Stack (works, verified Aug 2026)

- Amazon.in and Flipkart search + product pages load cleanly through Camofox
  (Hermes browser tools). No captcha handling needed. OLX also loads.
- Quick text extraction fallback: `curl -s https://r.jina.ai/URL` (did NOT
  work on 2gud.com — timeout; some SPAs need the real browser).
- Read the full snapshot from `cache/web/browser-snapshot-*.txt` via
  read_file instead of re-scrolling the browser.

## Amazon.in URL techniques

Price filter (values are paise, i.e. rupees x 100):
```
/s?k=<query>&rh=p_36%3A100000-150000        # Rs 1,000 - 1,500
/s?k=<query>&rh=p_36%3A150000-260000        # Rs 1,500 - 2,600
```
Renewed condition filter (real Renewed stock, not keyword search):
```
/s?k=<query>&rh=p_n_condition-type%3A6790255031
/s?k=<query>&rh=p_n_condition-type%3A6790255031&s=price-asc-rank
```
- Renewed store node: `rh=n:91144288031` (amazon.in/renewed redirects here;
  it shows generic products, so always combine with a keyword).
- Warehouse Deals (US open-box hub): 404s on amazon.in — NOT offered in
  India. Don't waste a navigation on it.
- KEYWORD "refurbished" DOES NOT filter condition — it returns normal new
  products whose titles mention refurbished/renewed. Always use the
  condition-type filter to see actual Renewed stock.
- Sort ascending: `&s=price-asc-rank`.

## Flipkart

- Search: `/search?q=<query>` — loads fine, results include price/ratings.
- Refurbished program is DEAD: `/refurbished` and `/refurbished-store` both
  return "page moved or deleted". Do not try them.
- "Refurbished" keyword search returns junk brands (GUGGU/YAROH/FRONY at
  Rs 441-626) with fake ANC claims — treat as garbage.
- Exchange offer ("Upto Rs X off on Exchange") is the only legit way to
  undercut a listing price.

## Refurbished / used market map (India, Aug 2026)

| Route | Status | Audio inventory |
|-------|--------|-----------------|
| Amazon Renewed | storefront exists | ZERO headphones in all of amazon.in (verified with condition filter, no price cap) |
| Amazon Warehouse Deals | 404 / not in India | n/a |
| Flipkart Refurbished | dead | n/a |
| 2Gud (Tata) | down / flaky | n/a |
| Cashify | alive | no headphones (phones/laptops only) |
| OLX | alive, 68+ ANC listings | real used Sony/JBL/Bose, ~Rs 2,600+; no buyer protection |

Bottom line to tell users: refurbished premium audio under ~Rs 2,500 does
NOT exist in India on any platform. US-market "Renewed deals" videos do not
apply. The real used market is OLX (peer-to-peer, meet-and-test, scam risk).

## Price history (Amazon.in)

- **Smartprix (smartprix.com) is the working tracker** for Amazon.in: find the
  product via site search (`/products/?q=<name>`), open its page — it states
  "price dropped X% in last month", "price last changed <date>", and the
  lowest-price store. That summary text is the price history; the chart data
  API (`/api/prices?pid=...`) 404s from the console, so use the page text.
- CamelCamelCamel does NOT cover amazon.in (hostname fails / no India support).
- Keepa: needs login + anti-bot check — not worth it for one-off checks.
- Wayback Machine: rarely has captures of amazon.in ASIN pages (CDX returns
  empty for most /dp/ URLs) — don't rely on it.
- Smartprix also shows sibling-model prices side by side (useful for "is the
  cheap variant a different model?" checks) and flags which store is cheapest.

## YouTube review cross-check

Use OpenCLI (channel adapter, needs Chrome+extension per anti-block-browsing):
```
opencli youtube search "<product> review" --limit 8
opencli youtube video <url>          # metadata: title, description, publish date
opencli youtube transcript <url>     # full content
```
- Transcript fails with "Caption URL returned empty response" when the video
  has NO captions — that is a content gap, not a tool error. Fall back to
  `youtube video` metadata (description + keywords confirm exact model/price).
- Grep transcripts for the verdict section (tail of comparison videos) rather
  than reading the whole thing.
- Compare review age vs price-change date: a review published right after a
  sale-price drop is the most relevant signal.

## Pitfalls

1. **Color-variant trap (important)**: Amazon product pages list color
   variants at DIFFERENT prices — the cheap variants are often a DIFFERENT
   model with fewer features. Verified: pTron Studio Urban V2 page showed
   "Black Rs 795 / Beige Rs 849" but those ASINs are the Studio Evo (no
   ANC). Always open each variant's ASIN (from the colour radio links) and
   check its title/specs before claiming a price. Title says it all.
2. **Budget-ANC reality rules** (category knowledge, not vendor claims):
   - Under ~Rs 2,600 new: no real ANC exists from reputable brands.
   - Under Rs 1,000: "ANC" is fake/ENC (mic filtering, not ear blocking).
   - A ~40dB ANC claim is marketing; budget ANC delivers real-world
     15-25dB: kills low-freq drone (fan/AC/traffic), NOT voices/sudden
     loud sounds. Music + ANC = masking = perceived near-silence.
   - For pure blocking with no audio: certified ear muffs (NRR 26dB/SNR
     33dB, ~Rs 1,200) out-block any sub-Rs 2,500 headphone.
   - Proper seal (cups fully around ears) matters as much as ANC; broken
     seal kills isolation instantly.
3. **Ratings vs price**: check both platforms — same product can have
   70K ratings on Amazon and 10 on Flipkart; buy where the trusted listing
   is, even at a Rs 50 premium.
4. **Delivery location**: results show "Delivering to <city>" — OLX deals
   are local-pickup; a cheap used listing in another city is not
   purchasable.

## Workflow

1. Price-filtered searches on Amazon.in first (fast, structured).
2. Cross-check the shortlist on Flipkart (same product, different ratings).
3. Open product pages of finalists: verify ANC claim, warranty, seller
   ("Sold by Amazon" > third-party), buy-box price.
4. Verify every color variant ASIN separately (trap #1).
5. If user asks for refurbished: run the condition filter + check OLX,
   then give the honest "doesn't exist / here's the cheapest real option"
   verdict with proof. Don't keep scraping dead storefronts.
6. Price history: check Smartprix page for % drop / last-changed date.
   Report "at tracked all-time low" when the drop is recent — that tells
   the user whether the sale price will last.
7. YouTube cross-check: opencli youtube search → video metadata → transcript;
   extract reviewer verdict + QC warnings (e.g. "take open-box delivery,
   test both speakers").
8. Deliver verdict tiers (top / budget / avoid) with live prices from ≥2
   platforms and honest ceiling statements.

Session detail (verified prices, pTron trap, OLX listings): see
`references/india-audio-market-2026.md`.
