---
name: bug-bounty-target-research
description: Use when selecting bug-bounty targets or prepping a hunt.
---

# Bug Bounty Target Research

## Why this skill exists
The user (beginner, India, Class 12) is starting bug-bounty hunting.
They ask for "targets", "scrape HackerOne", "best program for me" —
recurring requests as they hunt. This skill is the working method for
target selection and hunt prep.

## Boundary (hard rule, state once, no lecture)
This user hunts ONLY authorized programs: HackerOne/other platform
scopes, CTFs, their own labs. Never help attack systems they don't own
or lack permission to test. HackerOne programs are by definition
authorized — that's the sanctioned surface.

## HackerOne directory scraping (public, no login needed)
- `https://hackerone.com/directory/programs` — JS-heavy: navigate, then
  read via browser_console (compact snapshot shows nothing). The
  `/programs/search` JSON API returns `[]` unauthenticated (curl AND
  in-page fetch) — the RENDERED table is the data source.
- URL sort params are UNRELIABLE (measured 2026-08-07: passed
  order_by/direction/filter, table rendered by default launch-date sort) —
  don't trust them. Scrape instead:
  - Stats: `[...document.querySelectorAll('tr')].map(tr =>
    tr.innerText.replace(/\s+/g,' ').trim())` → Program, Launch date,
    Reports resolved, Bounties min/avg.
  - REAL program handles: `tr a[href]` links (e.g. `/abercrombie_fitch_bbp
    ?type=team`). Guessable short handles 404 — always take from the row
    links.
- Weight by: resolved_reports_count (programs actually paying out volume),
  then on the program page check "Reports received | 90 days" (triage
  VELOCITY) and "Last report resolved" (STALENESS — weeks-to-months old =
  backed-up triage, drop even if resolved count looks good).
- Program pages: `/hackerone.com/<team_slug>` — full snapshot for
  intro, rewards table, scope, test credentials, rules. The table shows
  90-day avg bounty per severity + % of resolved reports at that
  severity.

## What makes a good BEGINNER target (the filter that matters)
1. **Accepts LOW severity** — check the rewards table's % of resolved
   reports at Low. Meesho: 44.9% of payouts are Low (~$100). Most
   programs reject low-sev; the ones that accept it are where beginners
   get first payouts.
2. **Provides test credentials** — test accounts/OTPs on the program
   page = no real-account setup friction (Meesho: OTP 999999, supplier
   panel logins).
3. Fast payment / retesting / collaboration flags; short avg time to
   first response.
4. Local context: for this user, Indian platforms (Meesho, PhonePe,
   Razorpay) = ecosystem familiarity + Indian-phone OTP signup.
5. Read scope + rules carefully: closed-scope programs reject
   out-of-scope reports; required test headers (e.g. `X-Hackerone:
   <username>`); banned actions (rate-limit tests on order flow, real
   transactions).

## Report quality = 50% of the game
Clear step-by-step repro, proof of impact (screenshots/video), one issue
per report, no automated-scanner dumps, no spam. Quality reports build
signal → unlocks private programs → the real money.

## Realistic expectations (tell the user straight)
2-4 months to first payout is normal. Strategy: easy-accepting program
first (first payout + morale), HackerOne's own program for reputation,
then graduate to competitive ones. GLM-5.2 (glm CLI via Puter) is the
analysis assistant: recon notes, payload tweaks, reading obfuscated JS.

## Support files
- `references/hackerone-programs-aug2026.md` — verified directory
  snapshot (Aug 2026): ~30 bounty programs with bounties/volumes,
  Meesho full program detail (bounty table, test creds, rules),
  beginner-ranked shortlist with rationale.
