# Bulk page fetch + per-name fact-check dossiers (verified Aug 2026)

Two proven patterns from a live Epstein-files fact-check: (a) fetching many large pages without blowing context, (b) per-name "what IS / what is NOT established" dossiers with a URL manifest. Helper scripts: `scripts/fetch_page.py`, `scripts/grep_windows.py`, `scripts/ddg_search.py`.

## Pattern A — dump-to-file + window-grep pipeline (context control)
Wikipedia articles and news pages are 70–160 KB of text; printing them into context destroys the session budget. Instead:
1. Fetch with urllib + a browser User-Agent — this alone works on Wikipedia AND mainstream news (Guardian, BBC, CNN, TIME, The Verge, Newsweek, Independent, Yahoo news reprints). NYT paywalls (skip or use browser). No curl/browser needed for these.
2. Strip HTML: drop `<script>/<style>/<head>/<nav>/<footer>` blocks, strip remaining tags, `html.unescape`, collapse whitespace → the page becomes ONE long line.
3. Dump the full text to a local file (`fetch_page.py URL dump out.txt`).
4. A single-line dump defeats `grep -C` / line-based tools → use a **window-grep** script that prints ±450–500 chars around each match, capped at ~4 windows per name (`grep_windows.py file.txt Name1 Name2 ...`). Grep several names per run.
5. Iterate: dump the 3–6 backbone pages, window-grep all target names, then fetch only the news articles you'll actually quote.

## Pattern B — DuckDuckGo HTML endpoint (nuance: rate-limited, not blocked)
- `https://html.duckduckgo.com/html/?q=<urlencoded>` returns usable results for the FIRST 2–4 queries (links in `class="result__a"`, hrefs are `//duckduckgo.com/l/?uddg=<urlencoded>` redirects → URL-decode `uddg=`; snippets in `class="result__snippet"`).
- Then it starts failing with connection resets (WinError 10054) or silently empty result sets. This is rate limiting, NOT a hard block.
- Mitigation: wrap in a retry loop (`for i in 1 2 3; do ... && break; sleep 4; done`). After repeated empties, switch to: direct URL guesses (Wikipedia article titles, slugs seen in earlier results), Google News RSS, or Bing News RSS (see `live-news-and-blocked-sites.md`). Do not architect the whole task around DDG.

## Pattern C — per-name fact-check dossiers (person/scandal research)
- **Backbone: Wikipedia.** Articles fetch cleanly and their footnotes name the news-org articles (title + date + outlet) to fetch next for quotable confirmation. Pitfall: guessed article titles 404 (`Jeffrey_Epstein_flight_logs` did); use Wikipedia search or the main person article instead. Content note: the wikitext/infobox JSON leaks into stripped text as `{"wt":"..."}` noise — window-grep past it.
- For each person, classify evidence into explicit categories: (1) named in flight logs, (2) contact book/emails, (3) depositions/testimony, (4) accused by victims in lawsuits, (5) convicted. Then state explicitly what is NOT established: no charge, no victim accusation, lawsuit settled without admission of liability, denial, death before trial, docs "mention in passing with no suggestion of wrongdoing".
- Quote short phrases verbatim with the full URL; never paraphrase a URL you didn't fetch.
- Final deliverable carries a `LIVE-VERIFIED FACTS` manifest: every URL actually fetched, grouped "read OK" vs "blocked/empty" with the mechanism (404, paywall, rate-limit). If a name couldn't be live-verified, omit it or mark unverified — do NOT assert from training memory (e.g. Prince Albert of Monaco and Leon Black were dropped from the Epstein dossier because no fetched source confirmed them).
- Category framing is powerful for "is X connected to Y" questions: a flight-log or contact-book entry is NOT an accusation; say so per name.

## Person-fact-check worked example (Epstein files, Feb–Mar 2025 releases)
Reference data point: Phase 1 (Feb 27, 2025) contained flight logs + address book, "no significant new information"; DOJ July 2025 memo: no "client list" existed. Verified per-name categories: Clinton (flight logs; deposition/email mentions; no accusation), Trump (flight manifests + contact book; no standing accusation), Prince Andrew (flight logs, contact book, depositions; Giuffre suit settled Feb 2022 "no admission of liability"), Ghislaine Maxwell (convicted Dec 2021, 20 yrs), Marvin Minsky (flight logs; Giuffre 2016 sworn deposition; died 2016, never charged), Les Wexner (contact book; financial patron 1987–2007; FBI "potential co-conspirator" listing in 2026 releases; denied), Robert Maxwell (Ghislaine's father/employer until 1991; no flight-log/contact-book entry found), Stephen Hawking (2015 Epstein email re "reward" — the email is Epstein trying to DISPROVE an allegation; no wrongdoing evidence), Michael Jackson & David Copperfield (deposition mentions only). Full sources in the session manifest: Guardian/BBC/CNN/TIME/Verge/Newsweek/Independent-Yahoo articles + 6 Wikipedia pages.
