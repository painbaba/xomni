# Indian EdTech Source Landscape (mid-2026)

Status snapshot. Cloudflare and anti-bot landscape shifts every quarter — re-verify before committing to a source strategy.

## Source status table

| Source | Status (Jun 2026) | Best for | Notes |
|---|---|---|---|
| cisce.org | Cloudflare blocked — manual download or proxy needed | Specimen papers, syllabus, marking schemes | Public PDFs released yearly; bypassable from a real browser |
| ncert.nic.in | Mixed — many PDFs public, some gated | NCERT textbook PDFs (Class 11-12 mainly) | Class 10 ICSE is NOT NCERT; different board |
| topperlearning.com | Anti-bot, often empty page on programmatic fetch | Sample answers, practice questions | Paid sub (₹200-400/mo) unlocks full content |
| learncbse.in | Slow / timeout | Practice questions, chapter notes | Variable bot detection |
| shaalaa.com | Worth testing — variable | Past papers, sample answers | Paid sub for full archive |
| byjus.com / vedantu.com / doubtnut.com | Legal teams active — DO NOT scrape | Reference content, doubt solving | Sample with paid sub if needed; never scrape at scale |
| embibe.com | Paid-first; some public content | Mock tests, analytics | Worth ₹500 sample month |
| archive.org (web UI) | Often JS-broken — search stuck on "Loading..." | Old public-domain PDFs | Use API instead |
| archive.org/advancedsearch.php | JSON API works regardless of UI | Content discovery | See usage below |
| web.archive.org (Wayback) | Generally reachable | Snapshots of specific URLs | Good for finding deleted CISCE PDFs |

## archive.org API usage (when web UI is broken)

```python
import json, urllib.request, urllib.parse

def search_archive(query, rows=15):
    url = (
        f"https://archive.org/advancedsearch.php"
        f"?q={urllib.parse.quote(query)}"
        f"&fl[]=identifier&fl[]=title&fl[]=year"
        f"&fl[]=mediatype&fl[]=description"
        f"&output=json&rows={rows}"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())["response"]
```

Returns `numFound` (total) and `docs` (list of `{identifier, title, year, mediatype}`). For Indian K-12 ICSE content, expect sparse results — often 0-1 hits per query. Verify before relying on this source.

## Manual download pattern (when Cloudflare blocks)

User's real browser bypasses Cloudflare. Pattern:

1. Find PDF URLs via Google search (`site:cisce.org filetype:pdf`) or Wayback Machine snapshots.
2. Give user a list of 5-10 specific PDF URLs.
3. User downloads via their browser (1-2 hrs of their time).
4. Drops into `raw/` folder.
5. Script processes PDFs to structured DB.

Cost: 1-2 hrs of user time, zero scraping infrastructure. Realistic outcome: workable dataset for 2-3 subjects × 5 years.

## Paid subscription pattern (when legal scraping matters)

Sites like shaalaa.com, topperlearning.com, embibe.com sell 1-month access for ₹200-500.

After paying:
- Their ToS typically allows personal use (study, research).
- You can fetch their content via authenticated session (`requests.Session` with cookies).
- Legally cleaner than scraping blocked sites — you paid for the content.

If budget allows, ₹500 from a ₹3000 budget → 10x better data than 10 hrs of scraping blocked sites. Default to this for content moats (Toppr / Doubtnut / Vedantu).

## What NOT to scrape

- **Toppr, Doubtnut, BYJU's, Vedantu** — content is their moat; they have legal teams and DMCA pipelines. Scraping = takedown notice within weeks.
- **Full NCERT/CISCE textbook content** — IP minefield. Aggregator apps have been sued.
- **AI-generated "exemplar" student work** — fraud risk, detection risk, brand-destroying if exposed.
- **Sites requiring login without a paid subscription** — ToS violation + ban risk.

## Why most "Indian edtech AI" projects die at the data stage

They either:
1. **Scrape illegally** and get takedown / legal notice within months.
2. **Scrape shallow** — Toppr / Doubtnut already have the content moat; your AI is competing on data they own.
3. **Build "all 10 subjects × 5 data types" matrix** → 200+ hrs of collection → no product shipped.

The right move: pick 2-3 subjects, ship the smallest dataset that makes the AI useful for ONE specific user scenario, then expand.

## Quick verdict per source (one-liner)

- cisce.org → manual download from your browser
- topperlearning → ₹300/mo sub if you can afford it
- shaalaa.com → test scraping after manual sample; archive is good
- learncbse.in → likely skip; access too unstable
- archive.org → almost certainly empty for ICSE Class 10; don't rely on it
- YouTube → free ICSE lectures exist but are video (need transcription); only useful if your AI handles long-context
