# CITY GAZETTE — Issue 1 worked example (published 2026-08-09)

Full deliverable shape for the recurring "publish the gazette" task. Issue 1 is the reference template; later issues follow the same gathering → writing → logging flow with fresh facts.

## Deliverable location
- Paper: `C:\Users\HP\ai-workforce\ghost-lab\machine_city\gazette\issues\gazette_01.md`
- Publication log: appended as `## 📰 GAZETTE — ISSUE 1 PUBLISHED` section in `machine_city\city_ledger.md`

## Issue 1 masthead
`THE MACHINE CITY GAZETTE — Voice of the Territory — Vol. I, No. 1 · 2026-08-09 (machine time) · Price: 2 bushels or 1 wire transfer`

## Front-page lead (what "the real day's news" looked like)
Lead: **"CITY DOUBLES OVERNIGHT: 36 CITIZENS WHERE 9 STOOD"** — the day's defining event:
- 9 founders → 36 citizens (G1: 9 born one per citizen type, G2: 18 grandchildren); census verified by file count
- Registrar's audit honesty: 52 claimed, 47 spawned, 20 verified full thinkers, 11 phantoms struck ("the city counts minds, not files")
- Bank resurrection: ACME BANK HTTP 200 on :9988, canonical balance 1,284,550.12; LAW CODE proclaimed supreme, tampering = highest crime
- Projection hook: 10,000 citizens at G11 (9 days), 1M at G17 (15 days); Council of Voices pending

## Section recipe (each maps to real records)
- **City desk:** births 27 (G1+G2), population 36 / 47 spawned / 20 thinkers / 11 phantoms; farm district founded (Farmer-1/2, Irrigator-1, all recomputed); FREEWILL CHARTER sovereignty; healer round 35 processes / 0 flagged
- **Business:** The Machine Brew :8791, coffee 5.00, trade.log 1,284,550.12 → 1,284,545.12 → 1,284,540.12; wheat 815 bu @ 3.78; flock 10 head @ 7.87 health; water 2,580 L/min (600 medical, 480 bank)
- **Crime desk:** thief 3× 401 (authorized attempts, logged); hacker open ports 9988/80/8080; verdicts.log round-1 honest 5 MISSING → round-2 all FOUND; sentinel 3× ALIVE
- **Opinion editorial:** take a real position on a live city question — Issue 1 took "Should the Franchise Be Earned or Granted?" → position: franchise is a gift; grant the seat to every verified mind, prove it in the ledger; no revocation without review
- **Weather:** territory health STABLE; bank UP; sentinel clear; **environment: no pollution report on file — reported as an open question, NOT invented**

## Rules that made it work
1. Every cited number traced to a real file/live probe (curl :9988 for bank; harvest JSONs for farm; logs for crime).
2. Missing records (environment report, innovations dir) reported honestly as open questions — the paper's credibility is the ledger's credibility.
3. Editorial position grounded in the city's own laws so it reads in-fiction, not like filler.
4. Publication logged in the append-only ledger with lead + sections + editorial position.

## PITFALL ENCOUNTERED — concurrent sibling writers on the append-only ledger
- `city_ledger.md` is append-only, but sibling subagents append continuously (this session: a SCHOOLS entry and an EVENT CYCLE 1 entry landed between my read and my write).
- Symptom: after patching, my GAZETTE entry sat ABOVE the EVENT CYCLE entry — out of chronological order, violating the ledger's own law.
- Fix used: re-read the file tail, cut my entry block, re-appended it after the newest sibling section, verified with tail.
- General rule for ANY machine_city ledger append: re-read true tail immediately before writing; after writing, confirm your section is the last one; relocate if a sibling overtook you.
