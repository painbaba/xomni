# Crypto token deep-dive: tokenomics, unlocks, revenue, perp specs (verified Aug 2026)

For live-verified token dossiers (fundamentals + tokenomics + trade setup) — PUMP/Pump.fun session. Complements `binance-futures-research.md` (fapi endpoints) and `live-news-and-blocked-sites.md` (news/RSS). Every number must carry a URL; never assert from training memory.

## Source ladder (in order)

1. **Disambiguate the token** — CoinGecko search API:
   `curl -s -A "Mozilla/5.0" "https://api.coingecko.com/api/v3/search?query=<name>"`
   → pick id, symbol, contract address, platform, rank. **PITFALL: bare curl (no browser UA) gets "Throttled" or 10-byte error files — always send a full UA.** CoinGecko OHLC/status endpoints are key-gated (401); the coins/{id} endpoint works with a UA.
2. **Aggregator market data** — `https://api.coingecko.com/api/v3/coins/<id>?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false` → price, mcap, FDV, total/max/circulating supply, ATH/ATL + dates, 24h/7d/30d/60d/200d/1y %-changes, contract + platforms. Then the CoinMarketCap coin page in the **browser** (curl-blocked): rank, holders count, watchlist, CertiK, its own ATH/ATL.
   **PITFALL: CMC and CoinGecko routinely DISAGREE on ATH/ATL price and date** (different pairs/methodology — e.g. PUMP ATH $0.01214 Jul 13 2025 on CMC vs $0.008819 Sep 14 2025 on CG; ATL dates differ too). Report BOTH side-by-side with URLs; never silently pick one. User-context numbers usually come from one of them — say which.
3. **Tokenomics & unlock schedule — Tokenomist** (`tokenomist.ai/<slug>`, successor to token.unlocks.app):
   - curl returns only the SSR shell → **use the browser**. Snapshot yields: allocation table (% + tokens per bucket, sums to 100%), released progress %, float %, burn/buyback stats, raise amount, listing history (Updates tab), fundraising rounds.
   - **FAQ accordion = gold**: expand with a console click-all on `h5`s / `[role=button]`, then read the region — answers "next unlock?", "cliff or linear?", "fully unlocked?", FDV, allocation breakdown. Also carries a per-page "Updated: <date>" — quote it.
   - Sub-pages per tab: `/<slug>/buyback`, `/burn`, `/fundraising`, `/updates`, `/unlock-events`. Detail tables (buyback txs, funding rounds, unlock charts) are **Pro-gated** — record the headline stats, don't fight the paywall.
   - **CRITICAL PITFALL: Tokenomist's "Unlock Events" tracks notable CLIFF events only.** "No Upcoming Events" / "fully unlocked" can be true while monthly LINEAR vesting tranches still exist (found only via news — e.g. Crypto Briefing documented an Aug-12 6.875B tranche Tokenomist didn't show). **Always cross-check unlock dates against news** (Google News RSS / Crypto Briefing WP search).
   - **NEW-LISTING PITFALL (TGE < ~1 month): Tokenomist 404s entirely** (GRVT, TGE Jul 30 2026 → tokenomist.ai/grvt AND token.unlocks.app/grvt both 404). Don't burn turns — the authoritative vesting terms live in the project's OWN docs:
     (a) **Litepaper** (often hosted in the help center — GRVT's gave per-bucket lockups verbatim: "Investors/Team 0% at TGE, 12-month lockup then 36-month vesting; Ecosystem: partial TGE unlock, then 6-month lockup + 42-month vesting");
     (b) **TGE/launch blog post** (airdrop pool + tranche split — GRVT: 280M airdrop, 40% at TGE / 20% at months 4/8/12; multiplier plans defer tranches to M4/M8);
     (c) help-center TGE FAQ.
     **Consistency check: circulating ≈ first-tranche % × airdrop pool** (GRVT: 114.3M circ ≈ 40% × 280M — when it matches, the schedule read is right).
   - **Intercom help centers** (help.<brand>.io) are client-rendered: open in the browser; **clicking article links opens a modal instead of navigating — extract hrefs via browser_console JS** (`Array.from(document.querySelectorAll('a')).map(a=>({t:a.textContent.trim(),h:a.href}))` filtered on keywords), then navigate to the `/articles/<id>-slug` URL directly.
4. **Revenue/fees — DefiLlama** (curl, no key):
   - `https://api.llama.fi/protocols` (grep slug), `https://api.llama.fi/protocol/<slug>` (chains, TVL)
   - `https://api.llama.fi/overview/fees?excludeListed=true` → entries expose `total24h/total7d/total30d` = **FEES, not revenue**.
   - **PITFALL: fees ≠ revenue.** News claims like "X surpassed Hyperliquid in 30-day revenue" use the revenue dataset; the same two protocols may invert on fees or on a different window (PUMP: $33.73M/30d revenue > HL $32.73M, but HL $44.7M > PUMP $30.1M on 30d fees). Verify BOTH metrics and state which one each claim uses.
5. **Perp specs — Binance Futures public API** (curl, no auth): see `binance-futures-research.md` for ticker/OI-hist/funding/position-ratio; add `fapi/v1/openInterest?symbol=` (current OI in base tokens; $ = × markPrice) and `fapi/v1/exchangeInfo` (per-symbol `onboardDate` = futures listing date, `requiredMarginPercent` ≈ 1/max leverage, `maintMarginPercent`, precisions). For "200-day EMA breakout" claims: compute EMA-200 yourself from **spot** daily klines `https://api.binance.com/api/v3/klines?symbol=<SYMBOL>USDT&interval=1d&limit=320` (python EMA, report price/EMA ratio) — CoinGecko OHLC needs a key; Binance klines don't.
6. **News timeline** — Google News RSS (see `live-news-and-blocked-sites.md`; wrapper links 400 to curl AND sometimes the browser — cite title+source+pubDate, then find the body at the source site). **WordPress REST search is the site-search bypass**: `https://<site>/wp-json/wp/v2/search?search=<terms>&per_page=20` → full article catalog with URLs (worked on cryptobriefing.com when its own search/feeds failed; try on any WP outlet, e.g. protos.com). Article text: fetch with browser-UA curl, strip `<script>/<style>`/tags, `html.unescape`, body slice — or `scripts/extract_article_context.py`.
7. **On-chain holders & supply (works when Etherscan/solscan/arkm are bot-gated)** — three no-key ladders, all curl-friendly; Etherscan itself is Cloudflare "Just a moment", skip it:
   - **Raw RPC**: `eth_call` on the token contract — totalSupply `0x18160ddd`, balanceOf `0x70a08231` + 24-hex zero-padded address, decimals `0x313ce567`. RPC fallback order (llamarpc gave HTTP 521): `ethereum-rpc.publicnode.com`, `rpc.ankr.com/eth`, `1rpc.io/eth`, `eth.drpc.org`, `cloudflare-eth.com`.
   - **Ethplorer API**: `https://api.ethplorer.io/getTopTokenHolders/<contract>?apiKey=freekey` (curl, no signup). PITFALL: `share` field is in **basis points** (2910 = 29.1%) and balances are raw wei (÷1e18).
   - **Blockscout API**: `https://eth.blockscout.com/api/v2/addresses/{addr}` → `is_contract`, `name` (proxy implementation name, e.g. "GRVTVesting"), `is_verified`. Proves holder is a vesting/treasury contract vs an EOA.
   - **Concentration ≠ dump risk**: top-4 holding ~88% is NOT a red flag if every top holder is a verified vesting/treasury proxy contract — it means supply is programmatically locked (GRVT: top-5 = 91.4%, all contracts, one impl-named GRVTVesting). Check contract-vs-EOA BEFORE calling concentration a red flag; unlock dates then come from the vesting terms (item 3), not wallet labels.

8. **Exchange-listing verification ("X listed on Y", e.g. Upbit) — three-way proof, no search engines needed**:
   (a) the exchange's market is LIVE in CoinGecko `/coins/{id}/tickers` with real 24h volume (Upbit KRW-GRVT $3.5M — the listing happened AND it brought measurable volume; compare against dominant venues, e.g. OKX $48.6M, before claiming the listing "changed" volume);
   (b) a news article quoting the exchange's own notice verbatim (crypto.news quoted Upbit's full notice: date 17:00 KST, markets, contract address, trading restrictions, "GRVT ≠ Gravity/G" clarification);
   (c) price chart around the date (`/coins/{id}/market_chart?vs_currency=usd&days=14`) to see pump → fade → base.
   **PITFALL: news outlets make factual errors on new tokens** (coinalertnews called GRVT "the native token of the Gravity blockchain" — wrong; the exchange's own quoted notice disambiguates). Listing date for the CEX perp: `fundingRate?symbol=X&startTime=0` first entry (see crypto-futures-market-data traps).
## Unlock-schedule framing for leveraged trades
- **Cliff unlocks (big, dated) vs linear tranches (monthly drips)** — check both sources; one tracker may only see cliffs.
- $ value of an unlock = tokens × CURRENT price (recompute; news ranges like "$10–16M" go stale within days).
- Net pressure ≈ unlock $/mo − buyback $/mo (buyback ≈ revenue × allocation %). Report both sides.
- "Danger dates" = next cliff/tranche dates (be flat/reduced through them). Template for what's likely: was the PRIOR (often 10x larger) tranche absorbed? If price rose after it, the market has capacity.
- **Leverage sanity check**: stop distance % × leverage = account risk %; a 12% stop is ~120% risk at 10x, ~240% at 20x — say so plainly and suggest 3–5x or a tighter stop.

## Environment pitfalls (this class of research)
- **CoinGecko `/coins/{id}/tickers` rate-limits after 1-2 successes** (later calls return empty) — fetch tickers EARLY, cache the JSON, don't re-request.
- **DDG lite (`lite.duckduckgo.com/lite/?q=`) works ~once per session then rate-limits**; Bing/Brave/Yahoo/Startpage/SearXNG/Google-News-RSS are commonly blocked on restricted networks → go DIRECT to sources (project blog/help center, news sites that load in the browser) and spend the one DDG-lite query on the single highest-value discovery search.
- **MSYS `/tmp` mismatch**: `curl -o /tmp/x` succeeds but native python `open('/tmp/x')` fails (git-bash /tmp ≠ Windows temp). Write scratch files under `$HOME` (e.g. `C:/Users/<user>/<task>_research/`).
- **Intercom downloads** (article images/charts, `downloads.intercomcdn.com/...?expires=...&signature=...`) are fetchable via curl even when the help page itself is JS-only — grab chart PNGs for the record; OCR may not be available, so capture the surrounding article text as the machine-readable source of the same facts.

## Dossier format for this class (user expectation)
Lead with verdict + danger dates; then business, tokenomics, unlock table, catalysts, red flags. End with **LIVE-VERIFIED FACTS** (every URL fetched, one line per fact → URL, classified fetched-OK / headline-only / blocked-with-mechanism) and a **BLOCKED/UNREACHABLE** list naming each page and how it blocked (403 via curl, timeout, captcha, key-gated, Pro-gated, JS-shell-only). Quote exact numbers verbatim; label disagreements between sources explicitly.
