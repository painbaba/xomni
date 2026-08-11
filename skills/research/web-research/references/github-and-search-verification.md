# GitHub & Web-Search Verification Recipes (tested Aug 2026)

Exact commands and rate-limit facts from real research sessions. All unauthenticated.

## GitHub API — rate pools (unauthenticated)
- **Core API** (`api.github.com/repos/OWNER/REPO`): 60 req/hour. Dies fast when batching ~30+ repo checks. Check remaining: `curl -s https://api.github.com/rate_limit` (fields: `resources.core`, `resources.search`).
- **Search API** (`api.github.com/search/repositories?q=...`): SEPARATE pool, 10 req/min. Use for finding correct repos when a guessed path 404s. Batch multiple candidate queries with `sleep 3` between.

## Batch repo check (API)
```bash
for repo in owner1/repo1 owner2/repo2; do
  curl -s "https://api.github.com/repos/$repo" | python -c "import json,sys; d=json.load(sys.stdin); print(json.dumps({k: d.get(k) for k in ['full_name','stargazers_count','license','pushed_at','archived','description','fork']}, default=str))"
  sleep 1
done
```
`license` → null when missing/unlicensed; `pushed_at` is the last-commit signal ("last push" ≈ activity recency); `archived: true` matters.

## HTML scrape fallback (when core API exhausted)
GitHub HTML pages carry structured data — no API needed. Patterns that work:
```python
stars = re.search(r'aria-label="(\d[\d,]*)\s*users? starred this repository"', html) \
        or re.search(r'id="repo-stars-counter-star"[^>]*title="([\d,]+)"', html)
license = re.search(r'([A-Za-z0-9.+-]+) license<', html)
description = re.search(r'<meta name="description" content="([^"]+)"', html)
```
Use a browser UA. A repo that 404s returns the generic GitHub homepage description ("GitHub is where people build software...") — that IS the 404 signal. Org pages (no trailing repo path) render a description line like "OrgName has N repositories available."

## arXiv API — encoding pitfall (critical)
`search_query=all:WORD1+WORD2` — spaces MUST be `+`. If you URL-encode with `urllib.parse.quote` you get `%20`, and the API silently returns irrelevant recent junk instead of an error. Symptom: relevance-sorted results that have nothing to do with the query.
- Keyword hunting: `sortBy=relevance` (NOT submittedDate — that surfaces random new papers).
- Title-only: `search_query=ti:"exact+phrase"` is much more precise than `all:`.
- Verify remembered IDs: `curl "https://export.arxiv.org/api/query?id_list=2402.03300,2410.04258"` — print title+date; wrong IDs resolve to unrelated papers (happened 3x in one session: 2410.04258 was NOT DisTrO, 2409.11241 was NOT Merlin, 2404.17201 was NOT PowerInfer).

## Web search fallback ladder (tested Aug 2026 — news/status research)
Failure modes observed: DDG html (`html.duckduckgo.com`) either silently returns empty lists after a few queries OR serves a ~14KB challenge/anomaly page; Bing web HTML (`bing.com/search`) returns `bing.com/ck/a` redirect links with unrelated titles. **Full-outage case (Aug 2026, fresh Indian IP):** DDG html AND lite both TIMED OUT (curl exit 28), Bing web HTML served a hard captcha ('Please solve the challenge below'), Bing web RSS returned the SAME generic-AI boilerplate for 4 unrelated queries (query-ignoring), Google News RSS served a 'Sorry...' bot-block page, Mojeek + Reddit `search.json` served captcha/HTML walls — every direct curl backend down at once. That's the signal to escalate to the r.jina.ai ladder below. The working ladder:

1. **Bing News RSS — the workhorse** (dated items, real titles/links/descriptions; EN + CN queries):
```
https://www.bing.com/news/search?q=<urlencoded>&format=rss
```
Parse with python:
```python
import re, html as htmllib
items = re.findall(r'<item>(.*?)</item>', t, re.S)
for it in items:
    ti = re.search(r'<title>(.*?)</title>', it, re.S)     # title
    li = re.search(r'<link>(.*?)</link>', it, re.S)       # real news URL (bing news/apiclick.aspx redirects decode to the outlet URL)
    de = re.search(r'<description>(.*?)</description>', it, re.S)  # snippet
    pub = re.search(r'<pubDate>(.*?)</pubDate>', it, re.S)
```
Best on single-purpose topical queries ("Moonshot Kimi K3", "Anthropic Moonshot Claude data"). Use `-A 'Mozilla/5.0'`. Batch 4-6 queries per execute_code call and print `[date] title\n url\n snippet` compactly. One query returned zero items when it contained `"..."` OR syntax — keep queries simple, split complex ones.

2. **Bing web RSS** (`https://www.bing.com/search?format=rss&q=<urlencoded>`): works ONLY for simple/unique terms (e.g. `"Kimi K3"`, "Moonshot AI valuation") — returns clean `<item>` XML with description snippets. Goes fuzzy on multi-word/named-entity queries ("Yang Zhilin AGI quote" → yin-yang/YANG-language pages; "Kratsios Kimi K3" → Visual Studio). Verify results actually relate to the query before trusting them. Worst case: IDENTICAL query-ignoring boilerplate (OpenAI/Gemini/ChatGPT/Wikipedia/Perplexity...) for every query including Chinese ones — bot-degradation signal; stop retrying and escalate to the r.jina.ai ladder below.

3. **Browser DDG** (`browser_navigate` to `https://duckduckgo.com/?q=...`): last resort; one search at a time.

4. **Chinese-language queries = free amplification for China topics.** Same Bing News RSS endpoint, query in Chinese (e.g. `朱啸虎 杨植麟 循环智能 月之暗面`). Surfaced: funding-round mechanics (35亿美元 F轮 at 350亿美元 post, $50B pre-IPO target, Goldman/CICC sponsors), founder internal letters ("短期不着急上市"), and direct founder quotes — none of which English queries returned. Sohu/36Kr/QQ/ifeng/Sina Finance are the heavy hitters; their pages fetch cleanly via curl + tag-strip. Corroborate headline numbers across 2+ outlets; flag discrepancies inline (e.g. $35B post-money vs $45.2B reported elsewhere) rather than picking one.

## r.jina.ai full-SERP proxy — when every curl backend bot-blocks (tested Aug 2026)
The reader proxy fetches search-engine HTML and returns markdown. Works from IPs where the engines themselves captcha/time-out direct curl:
```
curl -s -m 60 "https://r.jina.ai/https://duckduckgo.com/?q=<urlencoded>&ia=web"
```
- **DDG via jina = the reliable full-SERP path** (EN + CN queries). Parse recipe:
  1. Drop ad entries — their links start `https://duckduckgo.com/y.js?ad_domain=`; strip with `re.sub(r'Report Ad.*?y\.js\?ad_domain=[^)]*\)', ' ', data, flags=re.S)` (ads carry click_metadata garbage that pollutes everything).
  2. Drop `![Image N](...)` markers.
  3. Split on `\n(?=\d+\.\s)` — each chunk is `N. domain [icon] TITLE/snippet`; organic results also appear as `## [Title](url)` after the icon links.
- **Google via jina: anonymous tier is abuse-blocked** — `{"code":403,"name":"AbuseAlleviationError","status":40305,"message":"...blocked until <UTC>..."}`; don't waste calls (the cited reason is often a bogus 'local network' check).
- **Bing via jina: relevance degrades to garbage** ('work to survive' → Rihanna 'Work' lyrics; 'Chinese developer AI' → VS Code docs) — only for dead-simple queries; prefer DDG.
- Rate-limit: sequential calls only; the anonymous tier rate-blocks domains after ~a dozen requests (same behavior as `news.google.com` — see the redirect-resolution pitfall in SKILL.md).
- Once the SERP yields real URLs, fetch article bodies from the publisher domain directly via jina (`https://r.jina.ai/<article-url>`) — returns `URL Source:`, `Published Time:`, markdown body.

## Viral-claim fact-check: skip the SERP, go primary-repo first
For a claim anchored to a project/company ("a 20-year-old built an AI that..."), the GitHub org API + raw README beats every search engine:
```
curl -s "https://api.github.com/users/<Org>/repos?per_page=10&sort=updated"   # names + descriptions
curl -s "https://raw.githubusercontent.com/<Org>/<Repo>/main/README.md"      # try main, then master
```
The README is the authoritative spec — the Aug 2026 'AI that dies if it doesn't earn money' claim was fully verified from the automaton repo README ('If it cannot pay, it stops existing', survival tiers, constitution) with zero news coverage. Then use 1-2 secondary sources only for the human-angle facts (creator identity/age — English and Chinese media often disagree; query Chinese for the '00后华人'-style framing). If the repo path guesses 404, use the GitHub search API (`/search/repositories?q=<name>+in:name`) before any web search.

## Wikipedia REST API — base timelines for companies/models
Fastest way to get a verified chronology before touching news:
```
https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles=<Title>
```
- Returns plaintext article (no markup); print `extract` (works for Moonshot AI, Kimi (AI), DeepSeek, Qwen, Z.ai, Doubao, etc.).
- Long articles: fetch once, slice the extract string by character offsets for continuation (don't re-fetch).
- **Absence is a finding**: e.g. "DeepSeek R2" has no mention on the DeepSeek page and no release news — the model never shipped; cross-check with news before stating it in a dossier.
- Cross-check specific claims (release dates, license clauses) against the official blog/GitHub raw README (`raw.githubusercontent.com/<org>/<repo>/main/README.md`), which carries the spec table and license terms.

## HN threads (adoption/community evidence)
Algolia API — reliable JSON, no auth:
```
https://hn.algolia.com/api/v1/search?query=EXO+distributed&tags=story&hitsPerPage=5
```
Fields: `points`, `num_comments`, `created_at`, `title`, `objectID` → `https://news.ycombinator.com/item?id=<objectID>`. Add `-A "<UA>"`. Perfect for: launch threads, "resurfaced on HN" activity signals, and Show HN items.

## Funding/status verification
- Primary: PR Newswire (`prnewswire.com`), company blog, official announcements.
- Trackers for cross-check: Tracxn, Sacra, Messari, Crunchbase News, DePIN Hub (decentralized compute).
- Rule: two independent sources or one primary + one tracker → cite. Otherwise write 'unverified'.

## Disambiguation pattern
For names that could be several things ("Infernet", "HearthNet", "imece"):
1. GitHub search API `q=name+in:name` — list ALL matches with descriptions.
2. Web search `"<name>" + topic keyword` — find which one the topic points to.
3. Write up the right one; note the collision in one line (the wrong project exists, don't merge them).
