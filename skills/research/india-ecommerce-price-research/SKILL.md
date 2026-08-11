---
name: india-ecommerce-price-research
description: "Use when comparing Indian e-commerce prices or history."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [india, ecommerce, amazon, flipkart, price-research, smartprix, refurbished, price-history, shopping]
---

# India E-Commerce Price Research

Find the cheapest legitimate price for a product in India, verify it across platforms,
track price history, and separate real deals from traps (fake ANC, same-listing-different-model).

## Trigger conditions
- User asks for cheapest/best price of a product in India ("find best cheapest", "compare prices across platforms")
- User wants price history / "track the pricing" of an Indian product
- User asks about refurbished/renewed/second-hand options on Indian platforms
- User is about to buy and wants verification of a "lowest price" claim

## User workflow expectations (learned)
- User does NOT accept Amazon+Flipkart as "compared" — they will ask "compare prices along top 5 ecommerce platform". Always sweep the full landscape before claiming cheapest.
- User expects three research layers bundled: live prices, YouTube review mining, AND price history.
- User expects refurbished/renewed channels to be checked and reported on, even when the answer is "doesn't exist in India" — state it with evidence, don't skip.
- Budget range is often tight (e.g. Rs 1,000-1,500) — set expectations honestly about what that budget can and cannot buy before recommending.

## Core workflow
1. **Clarify budget + must-have feature first** (e.g. "fully block loud sounds" = real ANC, not ENC). Without the feature definition, scraping is aimless.
2. **Baseline on Amazon.in + Flipkart** — these two carry 95% of budget/niche products in India. Same product is often price-locked at the same price on both.
3. **Sweep the full landscape** (this is what user explicitly demands):
   - Meesho, Snapdeal, Myntra, Tata CLiQ, Reliance Digital, Croma, brand's own site
   - Expect: most niche/budget products are Amazon+Flipkart ONLY. Report "not sold" per platform with what the search actually returned — user values the evidence.
4. **Refurbished/renewed reality check** — see references/india-platforms.md for the verified state: Amazon Renewed has ~zero audio inventory in India, Warehouse Deals doesn't exist in India, Flipkart refurbished storefront is dead, Cashify sells no audio, 2Gud unreliable. OLX is the only real used market.
5. **Price history**: use Smartprix (smartprix.com) — the only reliable India price tracker. CamelCamelCamel does NOT support amazon.in; Keepa needs login; Wayback rarely has captures of Indian listings. Smartprix product pages show current price, % drop, rupee drop in last month, last-changed date, and which store has the lowest price. "Last changed today" during a sale = the drop is live.
6. **YouTube reviews**: `opencli youtube search "<product> review" --limit 8`, then `opencli youtube transcript <url> --format plain` (some videos have no captions — fall back to `opencli youtube video <url>` for title/description metadata). Prioritize videos with big view counts and recent publish dates.
7. **Verify the trap variants**: a listing's color/variant options often mix DIFFERENT MODELS at lower prices (e.g. pTron Studio Urban V2 at Rs 1,299 with a "Black Rs 795" variant that is actually the no-ANC Studio Evo). Open each cheap variant's product page and check the title claims ANC or not. MRP difference is the tell (Rs 3,199 vs Rs 5,999 = different product).

## Honest expectations to set
- **No real ANC exists under ~Rs 2,000 in India** — sub-2K "ANC" is ENC (mic filtering, not ear blocking). Budget-brand ANC dB claims (40dB) are marketing; real-world attenuation ~15-25dB, kills low-frequency drone but not voices.
- ANC + music at moderate volume = perceived near-silence (masking does the final 30%). ANC alone never "fully blocks" — not even flagship Sony/Bose.
- Passive isolation cheat code for pure silence: certified hearing-protection ear muffs (NRR 26dB+) block MORE than any budget headphone — but no audio.
- "Double in days" stock claims are scams — do not entertain; pivot to index-fund SIP guidance (see references/india-market-data.md for live market data pull).

## Pitfalls
- **ENC ≠ ANC**: "Noise Cancelling" in titles of budget products is frequently mic-ENC. Check for "Active Noise Cancellation" or dB spec.
- **Same-listing variant trap** (see step 7) — always open the cheap variant, never assume.
- **Refurbished in India is a phantom market for audio**: verified Aug 2026 — Amazon Renewed returned ZERO headphones even unfiltered; Flipkart refurbished URLs are dead; don't promise "renewed Sony at half price" (US YouTube content does not apply to India).
- **Croma/Reliance/Tata CLiQ block curl** (403) — use the browser for those; Meesho search is fuzzy, use the exact model name.
- **Opening pages in user's Chrome**: `cmd //c start "" <url>` silently fails in git-bash. Use the direct executable: `"/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window "<url>"` (chrome.exe returns "Opening in existing browser session" and detaches on its own — no `&` needed).

## Support files
- `references/india-platforms.md` — verified per-platform state (Aug 2026): URL patterns, price-filter syntax, refurbished status, what works/doesn't.
- `references/india-market-data.md` — live NIFTY/market data pull via Yahoo Finance chart API (works with plain curl, no auth), plus index-fund savings guidance structure.

## Verification
- After research, deliver a per-platform price table (platform, price, in-stock, ratings count, warranty) and name the single pick.
- If claiming "lowest price ever", cite the Smartprix drop data; if claiming "not sold anywhere else", list the platforms checked and what they returned.
