# India Market Data + Savings Guidance (verified Aug 2026)

## Live NIFTY data via Yahoo Finance chart API (plain curl, no auth)
```bash
curl -s -m 20 -A "Mozilla/5.0" \
  "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1y" \
  | python3 -c "
import json,sys
r=json.load(sys.stdin)['chart']['result'][0]
closes=[x for x in r['indicators']['quote'][0]['close'] if x]
print('now:', round(closes[-1],2))
print('1y change:', round((closes[-1]/closes[0]-1)*100,1),'%')
print('52w high:', r['meta']['fiftyTwoWeekHigh'], 'low:', r['meta']['fiftyTwoWeekLow'])
"
```
- `%5ENSEI` = NIFTY 50 (BSE Sensex would be `%5EBSESN`). Meta also has regularMarketPrice, fiftyTwoWeekHigh/Low.
- NSE's own API (`nseindia.com/api/indices`) returns "Resource not found" to curl (bot-blocked) — Yahoo is the reliable no-auth route.
- Reading: flat year + mid-range = neither top nor floor; fine entry for SIP (don't time, just start).

## Sample read (7 Aug 2026): NIFTY 24,558; 1y change -0.2%; 52w 22,182-26,373

## Index fund guidance structure (for "best way to save" asks)
- Only index funds for a saver; never stock picks, never "double in days" (scam pattern — pump-and-dump Telegram/YouTube groups target young investors; refuse and say why).
- Nifty 50 index funds (Direct plans): Navi (~0.06% TER, SIP from Rs 100), Axis (~0.14%), UTI (~0.20%, OG since 2000), SBI (~0.19%), HDFC/ICICI (~0.18-0.20%).
- Broader: Axis Nifty 500 Index Direct 0.09% TER (verified on Value Research Aug 2026) — higher long-term growth, more volatility.
- CRITICAL: always Direct plan, never Regular (regular = ~0.5-1% extra commission forever; same fund/stocks otherwise).
- Platforms: Groww / Zerodha Coin / Kuvera / ET Money (Direct is default there).
- Minor (Class 12) investor: needs guardian account (Zerodha/Groww minor account) or parent starts SIP in own name. Keep simple.
- Compounding math: Rs 1,000/mo @12% = ~Rs 82K (5y), ~Rs 2.3L (10y), ~Rs 10L (20y). Starting at 17 beats starting at 27 with 5x money.
- Expense ratios drift with SEBI re-regulation — verify on fund page at purchase time.

## Mutual fund NAV history via mfapi.in (no auth, plain curl) — verified Aug 2026
Free Indian MF API (AMFI data). Two calls:
```bash
# 1) find scheme code(s) — note DIRECT vs REGULAR are separate schemes
curl -s "https://api.mfapi.in/mf/search?q=bandhan%20small%20cap"
# -> {"schemeCode": 147946, "schemeName": "BANDHAN SMALL CAP FUND - DIRECT PLAN GROWTH"} (etc.)

# 2) full NAV history (1597 points for small-cap funds)
curl -s "https://api.mfapi.in/mf/147946"
```
- Meta: `scheme_name`, `scheme_category` (e.g. "Equity Scheme - Small Cap Fund").
- **Dates are DD-MM-YYYY** ("31-12-2025") — `datetime.date.fromisoformat` will throw; parse manually `dd,mm,yyyy = row['date'].split('-')`.
- Compute CAGR from NAV at t vs now; compare current NAV vs all-time-high (max over history) to answer "has it recovered?" — `vsATH = now/ATH-1`.
- **Small-cap recovery snapshot (6 Aug 2026)**: most funds back at/near ATH (Bandhan +0.0%, Quant +0.0%, ICICI +0.0%, Axis -0.4%, SBI -1.2%, HDFC -1.1%); laggards still below: Nippon -3.6%, Kotak -4.7%, Tata -10.1%. A fund below ATH with weak 1Y (Tata +0.1%) is underperforming, not "cheap" — don't frame as a recovery bet.
- Nifty Smallcap 250 has NO Yahoo symbol (^NSMCAP250 etc. all 404) — for the small-cap index itself, use NSE's site or infer from fund NAVs.
- Scheme codes change across fund houses; always search by name first, never hardcode.
- Value Research fund-selector URLs redirect to unexpected categories and per-fund pages redirect to unrelated funds — the page text is fine but don't scrape those URLs by pattern; mfapi.in is the reliable structured source.

## Small-cap crash framing (honest, for young investors)
- Small-cap crashes come every ~2-4 years in India (2018, 2022, Mar 2025 ~-25-30%), always recover within 1-2 years historically — pattern, not promise.
- Predictors to watch: small-cap P/E froth vs large caps, FII outflows, SEBI tightening (2024 stress tests), rates/global risk-off.
- Risk-taking capability is learned by SURVIVING a drawdown with a size you can afford to lose (small-cap = "risk bucket" max 20-30% of savings; index fund = base). Nobody knows their real risk appetite before their first crash.
- A fund at all-time high is NOT "low" — never add lumpsum at ATH on a hunch; SIP only.
