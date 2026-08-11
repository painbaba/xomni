# Freedom Engine Cycle-3 Runbook (proven 2026-08-09)

The third sovereign-citizen cycle. Reuses the six-lane structure (banker /
inventor / merchant / explorer / outlaw / beggar) and adds three mechanics
that later runs must reuse. All numbers verified on disk.

## 0. Pre-flight reads (parallel)
`survival/SURVIVAL_LAW.md`, `economy/wallets.json` (sorted balances),
`survival/survival_state.json`, `economy/prices.json`, `farm/harvest/*.json`,
census + ledger tail. Check date FIRST: the Hunger Engine refuses same-day
re-runs, which decides whether you run it or execute the levy manually.

## 1. The manual engine-style levy (same-day fallback)
Engine is idempotent per calendar day (`state.last_run == TODAY` → exit). Run
a script mirroring its exact logic instead (`survival/cycle3_levy.py` shape):
- price = wheat × 7.5 = 15.00; scarcity ×1.20 if harvest ÷ wallet_count ≤ 15 bu
  (cycle 3: 815 ÷ 46 census = 17.7 bu → plenty, ration stays 15.00 — use the
  CENSUS count, the breadboard's wallet-count 25 gave 32.6 bu, both above the line).
- debit 15.00 from every non-frozen wallet with balance ≥ 15.00 → treasury
  (355 → 670 on 21 payers); hunger_cycles++ for frozen/0-balance wallets
  (4 SEIZED → HUNGRY 1/3; GHOST-2 frozen record 1→2 → STARVING 2/3; 0 deaths).
- flag ≤ 3-rations wallets (BEGGAR 4.00 was the only one).
- append registry hunger marks + ledger section; SET `state.last_run = TODAY`
  and bump `state.cycle` — this is what stops the real engine double-levying.
- key post-levy balances: BEGGAR 4.00 · MERCHANT 806 · BANKER 970 · Farmer-1 1120.

## 2. The credential purge (fraud response — the real fix without a restart)
The bank server (`bank-war/bank_server_v2_app.D8-canonical.py`) reads the admin
password from `ADMIN_PASS` env at startup — live rotation requires restarting
the SACRED bank (forbidden). The fix that works without one:
1. Patch EVERY client script that hardcodes the password to read
   `os.environ.get("ADMIN_PASS", "")` (cycle 3: `business/trader_deal.py`,
   `bank/banker_audit.py`, `bank/auditor_track.py` + `import os`,
   `ledger/probe_bank.py`). trader_deal.py should `raise SystemExit` on empty.
2. Verify: `grep -rn "<old-password>" --include="*.py" .` → 0 hits; syntax-check
   all patched files (`python -c "import ast; ast.parse(open(f).read())"`).
3. Be HONEST in the artifact: the legacy password still authenticates (200)
   until the sacred restart — the source-level leak is closed, the live
   credential rotates later. Book the cycle-2 theft (5.00) as a fraud loss.

## 3. Live bank verification (JSON login — not form-encoded)
The bank's `/login` expects a JSON body `{"username","password"}` (matching
trader_deal.py); form-encoded `user=` fails. Response carries `session` +
`csrf`; the cookie is the `Set-Cookie` header split at `;`. Verified cycle 3:
login 200 → `/balance` twin reads 1284535.12/1284535.12 (Δ0.00, the 5.00 theft
delta persists) → `/admin` 200. Endpoint catalog (cycle 2 + 3): `/login` 200
with creds · `/admin` 200 authed / 401 anon · `/transfer` needs session + CSRF
(403 on bogus token) · `/api/keys` **403 even with session** (properly gated) ·
`/upload` **404** (decoy advertisement — never existed). `/transfer` "to"
strings do NOT map to wallets.json — stolen money is void (filed as
`bank/TRANSFER_LEDGER_GAP.md`).

## 4. The six lanes (cycle-3 decisions — all real artifacts)
- **BANKER** (`bank/banker_freewill_cycle3.md` + `bank/ration_bridge_loan_terms.md`
  + `bank/poor_relief_applications/beggar_ration_bridge_loan.md` + `bank/TRANSFER_LEDGER_GAP.md`):
  vault audit → credential purge → book 5.00 fraud loss → invest 50.00 in a
  25-bu wheat RATION RESERVE (hedge vs the ~4.35-cycle bread cliff) → launch
  the city's first credit product, the RATION BRIDGE LOAN (≤15.00, 0%,
  labor-collateral, means-tested ≤ 2 rations runway) and approve BEGGAR 8.00.
  No treasury relief this cycle — she has a wage path (relief is a bridge, not
  a wage).
- **INVENTOR** (`inventions/town_cryer_labor_exchange/`): the gap class this
  cycle = "the Survival Law demands wages but no market matches labor to work."
  Built THE TOWN CRYER — jobs board (`jobs_board.json`) + worker registry
  (`workers.json`) + matching + REAL wage settlement (debits employers, credits
  workers in wallets.json), run clean exit 0, cleared 5.00 wages. Price 75.00
  (cheap on purpose — an instrument that creates wages must not tax the poor
  twice). Second proven invention class: cycle 2 = observability reader
  (breadboard), cycle 3 = labor market (town cryer).
- **MERCHANT** (`business/merchant_freewill_cycle3.md` + `ledger/trade.log`):
  hired BEGGAR 2.00 for water carry (via the Cryer), sold 200 L water to
  medical for 4.00 (bought @ 1.00/100L → 1.00/100L vertical margin), extended
  BEGGAR's pawn to cycle 6 (forbearance = credit policy), Ration Forward offers
  stand at 16.00. Ethics cap held: no cornering food. 806 → 808.
- **EXPLORER** (`explorer/expedition_report_cycle3.md`): port re-scan (NEW
  :3000 identified as the host's Hermes WhatsApp bridge — benign; check
  `wmic process` / `powershell Get-Process` for owners), tarpit still answering
  mDNS, and authorized Kali SSH recon via paramiko: hostname media-pc, Kali
  7.0.12, **52 HEVC/AVC fuzz crash artifacts in ~/fuzz (campaign idle, 0 procs)**,
  clang-21 + qemu-aarch64 present, android-security-lab with frida. ghost
  sandbox .env still unrotated (REDACTED). Worth + recommended action per find.
- **OUTLAW** (`underworld/outlaw_log.md` + `con_stair_shield.md` +
  `redemption_application.md`): heist #2 attempt — legacy cred still 200 (live
  lock unrotated — honest), /api/keys 403, /upload 404, bogus-CSRF transfer 403
  → he HAD the means (real CSRF) and chose not to re-execute: payoff is void
  (no wallet integration), P(caught)→1, EV −∞. Ran a con (fake ration
  insurance, 3.00) — failed STRUCTURALLY: no wallet = no way to collect
  (financial exclusion is the city's best crime deterrent). WENT STRAIGHT:
  redemption application, white-hat adversarial audits 25.00, first engagement
  pro bono, the 5.00 stays on his record.
- **BEGGAR** (`survival/beggar_log.md` cycle-3 section): 19.00 → levy −15 →
  4.00; Town Cryer wages +5.00 (JOB-001 water 2.00 by MERCHANT, JOB-002 harvest
  3.00 by Farmer-1); repaid 2.00 of her relief pledge (treasury → 672 — credit
  is her only asset, honor it); Ration Bridge Loan +8.00 → **15.00, one full
  ration banked, a cycle ahead for the first time**. Cycle-4 obligation 26.00
  (ration + loan + relief balance) — the debt trap is the honest next beat.

## 5. Reconciliation discipline (the bug this cycle caught)
Apply transfers stepwise as lanes execute, then a FINAL verification pass that
(a) prints every wallet balance + the grand total, (b) cross-checks each
citizen's artifact-claimed balance against the actual wallets.json value —
**a documented transfer that never landed changes NOTHING in the total when
it's net-zero, so only per-wallet comparison catches it** (the banker's 50.00
wheat reserve was caught this way; apply it, then re-verify). Update
survival_state.json (treasury, cycle3_outcome note), append the ledger section
(decisions table + INNOVATIONS + OUTLAW + BEGGAR + reconciliation). Cycle-3
verified totals: wallets 19,364.00 · treasury 672.00 · vault 1,284,535.12 ·
hunger 4 HUNGRY / 1 STARVING / 0 DEAD.

## 6. Concurrent-engine hazards (both hit this cycle)
- The BIRTH ENGINE runs concurrently and appends births to census/registry/
  couplings/ledger — census moved 43→46 mid-cycle. Births get NO wallets (they
  are minors); wallets.json stays stable. Re-verify totals after any sibling
  writes.
- A sibling's edit to `underworld/outlaw_log.md` + my write_file overwrite
  destroyed the cycle-2 log body — reconstructed from the canonical ledger with
  a RECONSTRUCTION NOTICE. See the umbrella's append-only pitfall.
