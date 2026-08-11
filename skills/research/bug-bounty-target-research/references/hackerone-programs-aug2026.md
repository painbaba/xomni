# HackerOne directory snapshot (verified 2026-08-07, live browser)

Sorted by resolved_reports_count (activity), filtered offers_bounties=true.
Columns: min bounty / avg bounty / reports resolved.

## Established high-volume programs
| Program | Min | Avg | Resolved | Notes |
|---|---|---|---|---|
| AT&T | $100 | $300-400 | 10,283 | managed |
| Adobe | - | $560-810 | 8,855 | managed |
| Twilio | $50 | $200-300 | 3,032 | managed, collab, retest |
| Uber | $500 | $500-700 | 2,680 | managed |
| GitLab | $100 | $1k | 2,220 | managed, collab, retest — $1k avg |
| Slack | $250 | $500 | 2,292 | retest, collab |
| X / xAI | $100 | $560 | 1,686 | managed |
| Vimeo | $100 | $350-500 | 1,682 | managed |
| Ubiquiti | $150 | $150-200 | 1,643 | managed, retest |
| Booking.com | $100 | $400-500 | 1,497 | managed |
| Coinbase | $200 | $200 | 1,135 | managed |
| HackerOne | $200 | $500 | 1,010 | managed, retest — own platform, rep builder |
| Dyson | $100 | $200-400 | 858 | managed |
| Snapchat | $250 | $250-500 | 727 | retest |
| Priceline | $100 | $250 | 641 | managed |
| Yelp | $50 | $300-500 | 509 | retest |
| Basecamp | $100 | $233-250 | 461 | collab |
| Cloudflare | $0 | $250-350 | 379 | managed, VDP+bounty mix |
| Airtable | $50 | $100-150 | 261 | managed |
| Greenhouse | $100 | $100-250 | 248 | managed |
| HubSpot | $50 | $250 | 238 | managed |
| Box BB | $150 | $500 | 208 | managed (private-ish team slug) |
| Notion | $50 | $150-250 | 173 | managed |
| Robinhood | $50 | $966-1k | 145 | managed — high avg |
| Vercel Open Source | $50 | $628-876 | 101 | managed — OSS targets, code-readable |
| DoorDash | $50 | $724 | 11 | managed |
| Anthropic | $50 | $750-1k | 390 | retest, collab — AI/LLM scope + separate Cyber Jailbreak program |

## India-relevant
- Meesho (meesho_bbp) — see full detail below.
- PhonePe — VDP (no bounty), 1 report.

## Meesho — full verified program detail (best beginner target found)
- Closed scope; Fast Payment (~1 month); Collaboration + Retesting.
- Response times: first response 1d15h, triage 4d15h, bounty 1w20h.
- Reward table (web & platform): Low $50-150, Medium $150-600,
  High $600-1200, Critical $1200-2000. Mobile apps: static-analysis
  findings only, $100-2500 by severity.
- Severity mix of resolved reports: Low 44.9% (avg $100), Medium 30.6%
  (avg $308), High 18.4%, Critical 6.1% — ACCEPTS LOW SEV = beginner
  entry point.
- Test credentials PROVIDED: consumer accounts (mobile 6666666661/2,
  OTP 999999); supplier panel (suppliertest-1@meeshoai.com /
  suppliertest-2@meeshoai.com, password Hackerone@123).
- Required: `X-Hackerone: <h1-username>` header on ALL test requests;
  Indian phone OTP signup supported.
- Banned: rate-limit testing on order flow, real financial transactions,
  touching real user data, account/security-settings changes, automated
  scanners on production.
- Disclosure policy: no public disclosure without explicit written
  consent; no selling/transferring vulnerability info.
- CVEs <30 days old ineligible; duplicate root causes paid once;
  out-of-scope reports → N/A, repeated → spam/ban.

## Beginner-ranked shortlist (delivered to user)
1. Meesho — test creds, low-sev accepted, India context, responsive.
2. HackerOne own program — $200/$500, reputation/signal building.
3. Vercel Open Source — read the code, $628-876 avg.
4. Anthropic — AI/LLM security matches user's skillset (LLM work).
5. Twilio — massive acceptance volume, realistic odds.

## Scraping recipe
- Directory: navigate + FULL snapshot; filters via URL params
  (offers_bounties=true, order_field=resolved_reports_count,
  order_direction=DESC).
- Program page: `/hackerone.com/<slug>` full snapshot.
- Re-verify before hunting: programs change scope/terms often.
