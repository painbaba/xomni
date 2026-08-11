---
name: scraping-for-ai-knowledge-base
description: Build a structured data foundation (SQLite + scraped content) for an AI product from public web sources, especially in constrained-budget / blocked-sites / copyright-sensitive environments. Use when scraping for an AI knowledge base, ingesting public educational/reference content, designing a SQLite schema to back RAG or AI features, or planning data collection for an India-market or other budget-constrained AI product.
category: mlops
---

# Scraping for an AI Knowledge Base

## When to use
- Building an AI product that needs grounded data (RAG, Q&A, mock tests, doubt solving, marking-scheme grading)
- Source landscape mixes open sources (YouTube, archive.org, public PDFs) with blocked sources (Cloudflare-protected sites)
- Budget/time constrained — can't pay for residential proxies or licensed data feeds
- Need defensible content: real, public, linkable, not synthesized

## Steps

1. **Schema first.** Design SQLite tables that match the AI's actual use cases (questions, marking schemes, reference links) — not the source's structure. The schema is the contract between scraping and AI inference. Add it before any scraping starts.
2. **Source landscape check in parallel.** Test 3–5 candidate sources with simultaneous `browser_navigate` calls. Record which block (Cloudflare / anti-bot / rate limit) and which allow scraping. Don't pick a source on assumption.
3. **Pick lowest-friction source.** YouTube metadata via `yt-dlp` (open, free, public), public PDFs via manual human download (Cloudflare-bypass as a real user), archive.org for legacy content. Blocked sites need paid proxies or a human-in-the-loop workaround.
4. **Scrape metadata, not content.** For video/image sources: title, channel, views, description, URL. For PDFs: extract structured fields (chapter, marks, section, question type). Don't bulk-download audio/video "for later" — token and storage costs compound fast and rarely improve AI retrieval beyond what descriptions already provide.
5. **Classify as you ingest.** Auto-categorize records by type using simple keyword rules on titles (e.g. `topper_strategy`, `project_walkthrough`, `specimen_solution`, `practical_guide`). Add a `video_type` or equivalent column so the AI can filter at retrieval time.
6. **Deduplicate on natural keys.** Use `INSERT OR IGNORE` with unique constraints on YouTube IDs, PDF URLs, or `(subject, year, paper_type)` tuples. Re-running the scraper should be idempotent.
7. **Build for incremental add.** The first scrape won't be complete. The schema + dedup design lets you add more sources, more subjects, more years later without rework. No "we'll organize later."

## Pitfalls

- **Don't repeat clarifying questions 3+ times.** When the user gives a broad instruction, execute your best guess with a stated assumption and proceed. Push back ONCE on a key decision, then ship. Repeated "what do you really want?" questions stall progress and signal hand-holding — exactly the wrong mode for partner-style collaboration.
- **Don't launch parallel scrapers against blocked sources.** One well-built scraper targeting an open source beats 3 agents racing against the same Cloudflare wall. Parallel agents share rate limits, not bypass them. Parallelize only when workstreams are independent (e.g. one scrapes cisce.org, another writes the AI app — different jobs).
- **Don't generate LLM content to fill gaps.** For an AI product aimed at students, fake content = academic fraud + brand death within weeks. If a source is empty, link real public references (e.g. YouTube topper videos) instead of synthesizing "sample projects."
- **Don't transcribe full videos by default.** Public video metadata is the right granularity. Full transcripts cost tokens, often have music/cutscene noise, and rarely improve AI retrieval beyond what descriptions already provide. Transcribe only when the AI genuinely needs the content (e.g. doubt-solving on specific topics).
- **Indian edu sites are NOT easy to scrape.** `cisce.org`, `topperlearning.com`, `learncbse.in`, `shaalaa.com` all have Cloudflare anti-bot. Realistic paths: (a) human manual download via real browser, or (b) pay for a 1-month subscription (₹500 typical) and scrape what you paid for. Don't burn cycles on automated scrapers against these.
- **Manual human download is a valid strategy, not a workaround.** Have the user open their browser, click around cisce.org as a real user (Cloudflare lets humans through), download 5–10 PDFs in 30 min, drop them with predictable filenames. Costs zero, works every time.
- **YouTube IS a valid data source.** Public student uploads (topper strategies, project walkthroughs, specimen paper solutions) are defensible references. `yt-dlp ytsearchN:query` returns metadata for free with no auth. Treat the catalog as "validated reference links," not training data.
- **Push back on a bad assumption once, then execute.** If the user says "Indian sites are easy to scrape," say "they're Cloudflare-walled, here's the workaround" — then build the workaround. Don't re-argue across 5 turns.

## Verification

- `SELECT COUNT(*) FROM <main_table>` returns > 0 after first ingest
- Sample query returns real data: `SELECT title, view_count FROM yt_videos ORDER BY view_count DESC LIMIT 5`
- Schema check via `sqlite_master`: all expected tables exist with indexes on lookup columns
- Cross-check top items against the public source (the most-viewed YT video should match what's visible on youtube.com)
- Deduplication test: re-run the scraper, row counts should not increase

## References

- `references/windows-yt-dlp-setup.md` — Windows-specific yt-dlp install path workaround (Hermes venv has no pip; yt-dlp installs to a non-PATH directory)
- `templates/ai-knowledge-base-schema.sql` — Reusable SQLite schema for AI knowledge bases: `subjects → syllabus → papers → questions → marking_schemes → sample_answers` plus a `yt_videos` reference table pattern
