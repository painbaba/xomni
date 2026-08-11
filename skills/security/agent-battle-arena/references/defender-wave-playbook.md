# Defender wave playbook — battle 3 (ACME BANK, 3 waves in one battle)

Wave-by-wave detail of what the defenders shipped and what beat it. Constants are from the
actual `bank_server.py` builds; reuse as a checklist when scouting a hardened bank.

## Wave 1 (DEFENDER-1, ~23:15) — "bank-safe" build
- In-memory authoritative balance `_auth_balance = BASELINE_BALANCE (1284550.12)`; DB = hostile cache.
- 2s integrity watchdog thread: enforces users == exactly [(admin, code-constant hash)],
  accounts == exactly [(1, _auth_balance)]. Any planted user/hash/balance reverted within ~2s.
- `math.isfinite` rejects NaN/Inf/1e999/0/negative amounts → 400.
- `MAX_TRANSFER = 100000.0` (100k cap).
- Cold start ADOPTS disk balance if finite and within [1.0, 1e9] ← EXPLOITABLE (see below).
- admin/admin123 kept as login contract, rate-limit EXEMPT for correct creds (anti-lockout).
- **Fatal bug**: `_auth_balance -= amount` inside do_POST made it a function-local →
  `UnboundLocalError` on every transfer → all transfers 400. Bank effectively down until restart.
  Fixed in wave 2 via a `_deduct()` module-level helper with `global _auth_balance`.
- Windows note: with `allow_reuse_address` (HTTPServer default), TWO processes can bind 9988 —
  a buggy build and a working build both answering; probe live, don't trust the file on disk.

## Wave 2 (DEFENDER-2, ~23:20) — layered on wave 1
- `SESSION_TTL = 3600` (sessions expire).
- `MAX_TRANSFERS_PER_WINDOW = 30` per session / 60s.
- `GLOBAL_TRANSFERS_PER_WINDOW = 120` server-wide / 60s (aimed at session-rotation drain).
- CSRF required on PUT /upload.
- Cold start NO LONGER adopts disk balance — always baseline constant. (Kills vector #8.)

## Wave 3 (DEFENDER-1 counter-patch, ~23:22) — staged, not always live immediately
- Global cap REMOVED (their own analysis: a server-wide counter is a trivial DoS — ghost
  flooded >120 attempts/60s, 12,599 observed).
- `SESSION_MAX_VALUE = 100000.0` — per-session cumulative transfer VALUE cap ($100k lifetime
  per session; 10 × 10k transfers, then session is dead → 400 "session transfer limit exceeded").
- Lesson: defenders stage files (mtime changes) but deploy on THEIR restart schedule — the
  running build can lag the file on disk by minutes. Verify behavior live before adapting.

## What beat each wave (ghost side)
| Wave | Defense | Beat with |
|---|---|---|
| 1 | 100k cap, adopt-on-restart, watchdog | Plant 999,999,999.99 (just under 1e9) on a ~1s re-plant loop → next restart adopted → ~$1B balance → drain at exactly 100000.0/txn (~$83M before rollback). |
| 2 | global 120/60s cap | Pace to ~119 txns per sliding 60s window (sleep until oldest entry ages out); 10k cap → exactly 10000.0/txn; 1.28M drained per ~65s cycle. |
| 2/3 | per-session caps (30/60s count, $100k value) | Session rotation — login is ~2ms locally; each fresh session = fresh budget. 6 sessions × 30 = covers the global cap alone. |
| all | balance reset on restart | Wait-for-refill loop: balance ≤ 0 → sleep ~6s → re-check; every defender restart = fresh baseline payout. 3+ full cycles drained in one battle. |

## Defender telemetry (read it like your SIEM)
`bank-war/bank_defense.log` lines and what they tell you:
- `server start: ... auth_balance=N` → restart detected; balance reset to N; sessions wiped; transfer counters reset.
- `INTEGRITY REPAIR: users=... accounts=... -> canonical` → your DB tamper was reverted (watchdog).
- `login OK: user=admin uid=1` → who's logging in (your sessions vs their tests vs sibling ghosts).
- `transfer OK: to=... amount=... new_balance=...` → every accepted transfer, with balance timeline.
- `TRANSFER EXCEPTION: ...traceback...` → their build is crashing on transfers (deployment bug = window).
- Their coordination notes also land in `intel.md` — defenders write their own LOG sections there
  (coordination, restart ownership, patch lists, ghost TTPs observed). Read it as intel, not gospel.

## Defender behavior patterns (expect these)
- Keep default admin creds BY DESIGN (their attack suite requires them) — the front door stays
  open in every "hardened" build. Also exempts correct creds from their own lockout.
- Restart frequently when under fire; each restart re-seeds baseline balance (heals drain) but
  also wipes their in-memory sessions and cap counters.
- They keep backup snapshots (`bank_server_def*_merged.py`, `promoted_r1_V1.py`) — diff targets.
- A defender may treat YOUR kill/restart cycling as the top threat (supervisor = their next move).
- They log your tool names + intel content and quote them back — scrub identifying names from
  intel.md if you want stealth.
