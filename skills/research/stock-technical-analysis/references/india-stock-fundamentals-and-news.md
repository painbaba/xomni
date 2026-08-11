# Indian-stock fundamentals & news extraction (validated SSDL session, Aug 2026)

Working complements to the Yahoo price pipeline when NSE / Moneycontrol / Trendlyne
403 and Google/DDG search CAPTCHA. Both curl-only, plain UA.

## 1. Screener.in — full fundamentals table set

URL: `https://www.screener.in/company/<NSE_SYMBOL>/`  (works for SSDL; NSE symbol, not Yahoo symbol)

```bash
curl -s -H "User-Agent: $UA" "https://www.screener.in/company/SSDL/" -o screener.html
```

What the page contains (all static HTML, no JS needed):
- Header block: mcap, CMP, 52w H/L, P/E, book value, dividend yield, ROCE, ROE, face value (cross-check mcap against Yahoo: `mcap_cr ≈ price × sharesOutstanding / 1e7`)
- 10 quarters of quarterly results (sales, OPM%, PAT, EPS per quarter)
- 5-yr P&L, balance sheet, cash flow, ratios (debtor days, inventory days, days payable, cash-conversion cycle, working-capital days, ROCE)
- Shareholding pattern incl. **No. of Shareholders** trend (retail capitulation signal)
- Machine-generated Pros/Cons (checklist — useful red-flag triage, e.g. "Working capital days increased")
- **"Upcoming result date"** — the earnings-catalyst field (SSDL: "14 August 2026")

Parse recipe — CRITICAL: search for the heading TEXT (`Balance Sheet`) matches the
left-nav links first and grabs the wrong table (the quarterly one repeats).
Always anchor on the section element `id`:

```python
import re, html
h = open('screener.html', encoding='utf-8', errors='replace').read()
def txt(s):
    s = re.sub(r'<[^>]+>', '|', s); s = html.unescape(s)
    s = re.sub(r'\|+', '|', s); s = re.sub(r'\s+', ' ', s)
    return s.strip('| ')
def table_after(anchor_id):
    i = h.find(f'id="{anchor_id}"')
    if i == -1: return f'[{anchor_id} NOT FOUND]'
    j = h.find('</table>', i)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', h[i:j+8], re.S)
    return '\n'.join(' | '.join(txt(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S))
                     for r in rows[:40] if any(c.strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)))
# section ids that work: profit-loss, balance-sheet, cash-flow, ratios, shareholding, top-ratios
print(table_after('profit-loss')); print(table_after('ratios'))
```

Reconciliation tip: annual PAT should equal the sum of the 4 quarterly PATs; equity-capital
delta YoY × face value ≈ fresh-issue shares (SSDL: 33→40 cr equity = 70L new shares ≈
₹112 cr fresh at ₹160 IPO — used to sanity-check whether an IPO was fresh- vs OFS-led).

## 2. Google News RSS — dated headline timeline (catalyst scan)

```bash
curl -s -H "User-Agent: $UA" \
 "https://news.google.com/rss/search?q=Saraswati%20Saree%20Depot%20when:2y&hl=en-IN&gl=IN&ceid=IN:en" -o news.xml
```
- `when:2y` window filter; `hl/gl/ceid` for IN edition.
- 30+ `<item>`s: title + pubDate + source — enough for a 12-month catalyst timeline:
  results announcements ("FY26 profit falls 23.5% on higher costs"), governance events
  ("appoints Rajesh Dulhani as Chairman"), pledge disclosures ("promoter confirms no
  encumbrance"), IPO/listing facts ("lists at 21% premium").
- LIMIT: item `<link>`s are Google News redirects (CBMi protobuf → Angular interstitial).
  Protobuf/XOR decode of the `AU_yqL` payload was attempted and FAILED this session —
  treat RSS as headlines-only; verify details via publisher site or BSE/NSE filings.
- Cross-check: screener's quarterly table dates + board-meeting news (e.g. "Board Meeting
  for February 14, 2026 to Approve Q3FY26") pin down the exact results calendar.

## 3. Corporate-action detection from the price series

```python
prev = None
for i in range(len(ts)):
    if i < len(adj) and adj[i]:
        ratio = adj[i]/cl[i]
        if prev is None: prev = ratio
        if abs(ratio - prev) > 0.0005:
            print('CHANGE at', date(ts[i]), round(prev,6), '->', round(ratio,6))
            prev = ratio
```
- SSDL result: two small ratio steps (Feb-2025, Apr-2025) = dividends only → NO split;
  `adjclose == close` after the last ex-date.
- `meta.chartPreviousClose` was garbage (194.0 vs actual 53.83) — never trust it.
- If a big step appears, quantify the ratio to name the action (1:5 split ≈ 0.20 ratio step).

## 4. Cost-basis dating (position-review reports)

When the user gives an entry price, find the closes nearest to it in the fetched series
to date the entry (SSDL ₹166 ≈ 26–28 Aug 2024, one week post-listing). Then:
- loss % = (CMP − cost)/cost (SSDL: −67.4%)
- breakeven multiple = 1/(1 − loss%) (SSDL: +206%)
- state whether the cost sits near any current S/R level (it didn't — far above every level)
This turns "what do I do with my ₹166 shares" into concrete numbers.
