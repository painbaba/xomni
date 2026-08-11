# E-commerce price research (Amazon.in / Flipkart)

Verified Aug 2026 on this machine via Camofox — both platforms render search
results with ZERO bot-block, no login needed. Fastest route for "find me the
best/cheapest X in India" questions.

## URL patterns

- Amazon.in search: `https://www.amazon.in/s?k=<urlencoded+query>`
- Flipkart search:  `https://www.flipkart.com/search?q=<query>`

## Workflow

1. `browser_navigate` to the search URL. The returned snapshot already carries
   price, MRP, star rating, rating count, and "N+ bought in past month" inline
   per product — enough for a first pass without opening product pages.
2. **Snapshot truncation**: large result pages are cut at ~15K chars and the
   FULL snapshot is saved to
   `C:\Users\HP\AppData\Local\hermes\cache\web\browser-snapshot-<hash>.txt`.
   Do NOT re-navigate — `read_file` the cache file with offset to page through
   the rest of the results.
3. **Cross-check the same model on both platforms** — prices and listing
   quality diverge. Example: soundcore Q20i was Rs 4,749 on Amazon with 70,660
   ratings vs Rs 4,753 on Flipkart with 10 ratings (buy Amazon). JBL Tune 770NC
   was Rs 4,999 on both.
4. **Flipkart noise**: search results are polluted with fake-brand duplicates
   (JPGC, GUGGU, FRONY, YAROH, SGM) and multiple seller listings of the same
   model. Filter on rating count + "Only few left" flags, not just stars.
5. **Amazon color variants = separate ASINs** (`cs_sr_dp` links). Price shown
   for one color may differ per variant; check the variant you actually want.

## Domain filter: "noise cancelling" claims (headphones)

- ENC ≠ ANC. ENC is mic noise filtering (your VOICE in calls); ANC blocks
  sound reaching your EARS. Sub-Rs 2,000 "ANC" headphones (JPGC/GUGGU/FRONY
  class, Rs 441-726) are fake/ENC marketing — do not recommend for noise
  blocking.
- Loud-ambient blocking needs over-ear closed-back + real ANC. In-ear ANC
  cannot seal loud low-frequency noise (construction, traffic, generators).
- MRP strike-through is inflated (50-67% "off" is the norm at sale time);
  compare actual selling price, and weigh "bought in past month" volume over
  star rating for reliability.

## Operational notes

- Terminal on this host is git-bash: use `/c/Users/HP/...` paths, never
  `C:\Users\HP\...` (backslashes eaten → cd fails).
- Clean up Camofox sessions afterward (`DELETE /sessions/{userId}`) per the
  main skill's session-hygiene rules.
