# CITY EVENT ENGINE — deck, roll protocol, and worked cycle (Aug 2026)

Session detail for the Machine City event engine (`ghost-lab/machine_city/events/`). Built 2026-08-09, cycle 1 rolled VISITOR + MARKET and both executed for real. Reuse for every future event cycle.

## The deck (`events/EVENT_DECK.md`) — 5 events, real mechanics

| Event | Mechanics | Expected outcome | Responder |
|---|---|---|---|
| ROBBERY | POST /transfer to 127.0.0.1:9988 with bad/absent session + no CSRF (reuse `ledger/probe_bank.py` pattern) | Bank rejects 401/400; attempt appended to `underworld/thief.log`; Sentinel logs alert | SENTINEL |
| FIRE | Scan python.exe for dead/zombie (WorkingSetSize==0 via healer_round.py logic); kill a harmless decoy if one exists, else declare false alarm | Healer note in `medical/prescription.md` + `ledger/medical.log`; real PID dies OR false alarm | HEALER |
| MARKET | Run `business/trader_deal.py`: login → transfer 5.00 → shop /price → append trade.log | Balance drops 5.00; real trade.log entry with before/after | BANKER |
| OUTBREAK | Find biggest .log under city, truncate to 200 lines (keep tail), record truncation in EVENT_LOG | Biggest log ≤200 lines | ENVIRONMENT MINISTRY |
| VISITOR | Create marker file in a district `population/` dir (e.g. `couriers/population/Visitor-N.md`) + append birth line to `census.md`, update totals | Marker on disk; census total +1 | SCRIBE |

## Roll protocol
- `python -c "import random; print(random.sample(['ROBBERY','FIRE','MARKET','OUTBREAK','VISITOR'], 2))"` — 2 unique events per cycle.
- Check service liveness BEFORE executing: TCP connect_ex + HTTP GET on 9988 (bank) and 8791 (shop). Both returned 200 in cycle 1.
- Every event leaves a verifiable artifact. A claim without an artifact is a rumor (city law).

## Response doctrine (`events/RESPONSE.md`)
- One responder per event; the responder's artifact is the verdict.
- Real commands only; ledger outranks the claim; HEALER never kills (false alarm is a valid honest outcome).
- After response: append event + outcome to `city_ledger.md` (append-only).

## Worked cycle 1 (real outcomes)
- Roll → `['VISITOR', 'MARKET']`.
- **VISITOR**: wrote `couriers/population/Visitor-1.md` (role Courier, Generation G3, "arrived on the road through the border"). Patched `census.md`: TOTAL POPULATION 36→37, couriers district 3→4, added G3 arrival line. Verified: `ls couriers/population/` shows Courier-1/2/3 + Visitor-1. Scribe responded.
- **MARKET**: ran `python business/trader_deal.py` → `LOGIN OK {session, csrf}`, `TRANSFER RESPONSE {"ok": true, "transferred": 5.0, "balance": 1284540.12}`, balance 1284545.12 → 1284540.12, shop price city_coffee 5.0, trade.log line appended (timestamp 07:57:50 UTC). Banker responded.

## Key city service facts (reused across cycles)
- Bank: `http://127.0.0.1:9988` — login admin/city-admin-pass-2026 → `{session, csrf}`; GET /balance with `Cookie: session=...`; POST /transfer with `Cookie` + `X-CSRF` header + JSON `{csrf, to, amount}`. Canonical balance in ledger is truth.
- Shop (The Machine Brew): `http://127.0.0.1:8791` — GET /price → `{"product": "city_coffee", "price": 5.0, "currency": "city-credit"}`.
- Never start/kill/restart the bank — managed by the world-architect (`bank/launch_bank.py`).
- Reusable district scripts: `business/trader_deal.py` (full trade), `underworld/thief_attempt.py` (3 wrong-password attempts → thief.log), `medical/healer_round.py` (wmic scan → prescription.md), `military/sentinel_watch.py` (3× liveness → sentinel.log), `ledger/probe_bank.py` (endpoint probes).
- Census rule: a citizen = a marker file in its district's `population/` dir. No file = no citizen. Birth/arrival = marker file + census.md line + district count bump.
