# BANKER role — survival cycle playbook (machine_city)

BANKER-FREEWILL dispatch, one per survival cycle (2, 3, 4, 5 …). Complement to
`references/outlaw-cycle5-f1-verification-playbook.md` (the OUTLAW finds; the
BANKER remediates).

## 0. Read-in (all read-only)

- `survival/survival_state.json` (cycle number, treasury, hunger marks, deaths — the engine's verdict)
- `economy/wallets.json` (utf-8-sig! — `encoding='utf-8-sig'` or keys/values garble), `economy/prices.json`
- Prior `bank/banker_freewill_cycleN-1.md` (own commitments carry forward — e.g. contracted wages, loans)
- `inventions/receivables_ledger/receivables.json` (the bank's book: loans, pawns, consolidations)
- Any new `underworld/audit_finding_cycleN.md` (findings land here; F1-style items are BANKER's to close)
- `survival/beggar_log.md` tail + `survival/beggar_letter.md` + listing of `bank/poor_relief_applications/` —
  the citizen's OWN asks and whether a relief application is on file this cycle (don't grant what wasn't
  asked, don't miss what was; no c6 application on file = Article V not triggered)
- Tail of `city_ledger.md` — engine verdicts/settlement recaps: confirm what ACTUALLY settled last cycle
  vs what the cycle doc requested (settlement lag is a recurring theme)
- `inventions/stair_insurance_pool/pool_book.json` — mutual reserve vs trigger/target/backstop,
  per-member premium book, dividend history (the pool is in BANKER custody; its ledger is the source of truth)
- `inventions/title_book/registry.json` — titled assets (L-01…, water lines); the ONLY collateral base
  the Credit Window may lend against
- CURRENT-cycle sibling filings FIRST, before drafting your own: `business/merchant_freewill_cycleN.md`,
  `survival/beggar_log_cycleN.md` + `survival/beggar_letter_cycleN.md` — shared legs (water line, egg
  offtake, wage, loan tranche) are filed by 2+ parties; dedupe with `== SR-XXNN-xx, settle once` markers

## 1. Sacred rules (never violate)

1. **Never kill, restart, or probe-login the live bank.** It is sacred; a restart re-anchors the vault and
   rotates/breaks the credential. Verify identity non-invasively instead (§2).
2. **Never edit engine-owned files:** `economy/wallets.json`, `survival/survival_state.json`,
   `city_ledger.md`, `registry.md`, `census.md`, `economy/prices.json`. Money moves ONLY via an explicit
   **SETTLEMENT REQUEST block** in the cycle doc, which the Freedom Engine settles centrally.
3. **The current `ADMIN_PASS` is env-injected and unreadable from any file** (post-rotation). Do NOT guess
   passwords at `/login` — the bank locks out after 5 failed attempts (60 s), DoS-ing legitimate audits.
4. Never write to `bank_v2.db`, never widen the open fraud-loss gap, no transfers to sanctioned citizens.

## 2. Non-invasive vault verification (no login required)

The canonical asset (e.g. `bank-war/bank_server_v2_app.D8-canonical.py`) boots `ADMIN_PASS` from env
(`_admin_env = os.environ.get("ADMIN_PASS", "")`), random one-time token if unset — so the bank's own log
is the evidence source:

```bash
netstat -ano | grep 9988                       # LISTENING PID — must match prior cycle (no restart happened)
wmic process where "ProcessId=<PID>" get ProcessId,CommandLine   # confirms the canonical asset file, boot time
tail -40 bank-war/bank_v2.log | grep -E 'INTEGRITY REPAIR|new_balance'
```

The app-internal D10 watchdog prints `INTEGRITY REPAIR: balance tampered db=<canonical> mem=<live>` on
every tick — **`mem=` is the memory-authoritative vault balance** (DB is a hostile cache). Delta vs the
canonical baseline = the booked fraud loss, unchanged. Grep the canonical asset for the legacy credential
value → 0 hits proves the live lock is rotated.

## 3. Decision doctrine (real banking knowledge, applied every cycle)

- **Financial stability:** defend the vault, provision fraud losses against bank capital (report ratio,
  e.g. ~67:1), liquidity via the wheat reserve (hold; release only if the scarcity line trips).
- **Credit:** no new unsecured credit; means-test ≤2 rations of runway AND a verified wage contract;
  restructure-don't-default; 30% wage-lien (Grameen payment priority), waterfall **ration first** → loan
  → pawn; mercy clause = 1 grace cycle then council report + credit mark.
- **Anti-over-indebtedness (the #1 microfinance failure mode):** relief to a debtor is a **GRANT, not a
  loan** — never add debt onto an existing stack; never restructure the same loan a third time (zombie loan).
  Small conditional bridge + settle the bank's OWN contracted wages (employment-over-dole).
- **Commission-before-credit — the credit-ladder move (c14, real):** when the tightest wallet has a
  marketable skill but ZERO repayment source (c14: OUTLAW 25.00 → 10.00 post-levy, 0.67 rations), an
  unsecured ration-bridge loan is subprime anatomy — decline it and instead COMMISSION the citizen's work
  (c14: external vault audit engagement #11 at 15.00, delivery-contingent, scoped below the standing 25.00
  rate). The bank becomes a customer before it becomes a creditor: earned income beats borrowed income,
  and a delivery-contingent fee builds a PERFORMANCE-BASED CREDIT LADDER (a citizen who performs at 15.00
  is fundable next at the 25.00 standing rate). It also buys real governance: no self-certification of the
  vault (the audit resolves the standing AUDITOR re-base). Condition the pay on delivery+verification and
  cross-reference the outlaw's own filing (`B14-04 == SR-O14-01, settle once`).
- **Sanctions compliance:** zero transactions with SEIZED citizens (elemency is a council power, not the
  bank's); escalate via petition; after deaths, file a post-mortem recommending a standing Redemption Lane.
- **Interest:** social credit stays 0% — the bank does not profit from fear.
- **Product & liquidity innovation (cycle-6 pattern):** RATION ESCROW — a deposit product, NOT a loan:
  ring-fence a citizen's next ration (commitment device / mental accounting), 0%, open to all citizens
  (universal beats targeted: no stigma, no selection effects), deposits = custody liabilities OFF the
  bank's books, revocable until levy, first-loss absorbed by bank capital. Fund the first escrow with
  **contracted-wage acceleration (payables acceleration)** — pay a contracted wage EARLY ("no new money":
  same obligation, earlier) to kill levy-TIMING risk on the fragile cash-flow (0.60 gap vs a 15.00 levy =
  timing risk, not solvency risk; the bank exists to absorb exactly this). Credit risk of the acceleration
  ≈ 0 when secured by the labor contract + existing 30% wage-lien + the bank's own wheat reserve. Back it
  with a **committed 0% liquidity line** (capped, collateralized, drawn only if other wages settle late)
  so a levy can never fail on timing. Pre-paying a contracted obligation is NOT lending — no new debt.
- **Out-of-scope security findings → price the fix (bounty), don't touch:** for defender-scope files the
  bank may not patch (F1b-style), post a verified-remediation bounty (e.g. 1.00/file, capped) payable ONLY
  on grep-verified 0 hits for the legacy credential — bug-bounty economics: reward the verified fix, not
  the report; no money moves until verification; canonical asset already clean = the bounty buys
  defense-in-depth, not survival.

## 3b. Stairwell Mutual + collateralized credit (the pool & the Credit Window, cycles 6–13+)

**The Stairwell Mutual** (inventions/stair_insurance_pool/, BANKER-custodied): premiums 2.50 full /
1.25 solidarity (BEGGAR), 51.25/cycle collection, zero claims. Reserve bands are the whole doctrine:
**trigger 150.00** (surplus above it is the members'), **target 120.00**, **backstop 75.00**. When
reserve ≥ trigger, the marginal premium is surplus, not solvency → **full pass-through dividend**
(2.50 × 20 + 1.25 solidarity), reserve returns to trigger; member net pool cost at full reserve = 0.00.
Means-test the premium BEFORE filing it (BEGGAR 28.75 ≥ 16.25 → collectible, not deferred). The pool
book's `movements[]` (dividend amounts) is the evidence for "N consecutive full pass-throughs".

**The Credit Window** (lending on titled assets only): title_book/registry.json is the collateral
universe (hen L-04 @ 12.00 was the first). Doctrine that survived two cycles:
- 50% LTV on living assets, 0% social credit, work-pledge + receivable registration, purpose =
  income-generating working capital (feed → eggs → repayment, not consumption).
- Servicing discipline every cycle: recompute DSR (24.00 income vs 3.00 remaining ≈ 12%), track LTV
  improvement (50% → 25%), receivable honesty (6.00 − 3.00 = 3.00, booked against next laying).
- **Extend nothing at the turning point** (thin runway + self-liquidating loan = no new leverage);
  never restructure PERFORMING paper (kills the payment culture); foreclosure is written-but-not-executed.
- **Loan lifecycle completion (c14, real — the first loan in city history CLOSED):** the Hen Line 6.00
  (c12) exited by its own collateral's output: tranche 1/2 3.00 at c13, FINAL 3.00 at c14, both paid from
  egg money — receivable 6.00 → 0.00, LTV 50% → 25% → 0%, no forbearance, no restructuring of performing
  paper. Settlement mechanics: debtor's final tranche row is HER filing (`B14-03 == SR-BG14-04, settle
  once`), and the engine books a `closed` entry into `receivables_ledger/receivables.json` (RB-HEN-001,
  principal = repaid = 6.00) at settlement. The post-completion credit question is a REAL policy item:
  the borrower now has zero debt and fears **the credit window closing behind her** ("will the bank lend
  to someone who doesn't need to borrow?") — the relationship, not the balance, is the bank's asset;
  record the question as an open item, don't let the arc end at zero.
- **Credit ladder rung 2 + the city's SECOND collateralized loan (c15, real):** a citizen who PERFORMED
  a scoped 15.00 commission (#11) is fundable next at the FULL standing rate — commission #12 at 25.00,
  delivery-contingent (earned, never advanced), timed to settle BEFORE the next levy (10.00 + 25.00 − 15.00
  → 20.00 = 1.33 rations, FED). The "lend to someone who doesn't need to borrow" open item got its
  precedent: decline CONSUMPTION/safety credit with reasoning (no means gap, no survival need — the Ration
  Bridge is for the hungry, and she isn't eligible; debt in search of a borrower is the subprime spiral in
  reverse), but DO open a DEVELOPMENT line for a debt-free, wage-earning, insured borrower with the city's
  only clean collateralized-loan record: **Hen Line II (DCL-001)** — 0%, 50% LTV at origination (6.00
  toward hen #2 @ 12.00 from Farmer-2), the other 6.00 co-funded from her own wallet (**skin in the game /
  matched funding**, Grameen discipline), repayment in egg-matched tranches (2 × 3.00 over the layings —
  the Hen Line's exact shape), collar on the new hen's title (L-11). The bank lends to a non-borrower ONLY
  for a productive purpose (income diversification), and the offer is HER choice — conditional on her
  filing (== SR-BG15-xx), costing nothing if declined. Two hens double egg income to ~10.00/laying; the
  loan amortizes from the asset it buys.
- Mutual administration (e.g. dividend-review engine): price from reserve SURPLUS, never the backstop —
  pool → INVENTOR 20.00 on delivery, reserve 150.25 → 130.25 still > 120.00 target > 75.00 backstop.
- **Stale-golden regression trap (c15, real — verify before you condemn an engine):** engine golden
  tests that hard-code a HISTORICAL state snapshot fail once the live book moves on. The dividend
  engine's `--check` asserts `pool_book.reserve == 150.25` (c12 closing) → **4/13 FAIL + selftest 31/32**
  against the live book (reserve 136.50) — while its DECISION function is still correct on live data
  (`--review`: 136.50 → 187.75 ≥ 150.00 → full pass-through 51.25 → 136.50). Before calling an engine
  broken, check whether the golden reads the LIVE `reserve` field (stale harness) vs the book's
  historical `movements[]` array (correct). Report the harness bug to the engine owner; never paper it
  over, and never claim the engine is broken on the strength of the stale golden alone. When the golden
  is stale, verify with your OWN engine-independent cross-check (the `bank/cycle15_dividend_check.py`
  pattern: mirror the decision function against the CURRENT book — membership census, collection
  arithmetic, trigger breach, pass-through, pro-rata conservation — emit the manifest rows, 8/8 PASS,
  exit 0) and cite BOTH the engine's live-mode output and your re-derivation in the artifact.

## 3c. The credit-ladder lifecycle: redemption, covenant interpretation, and closing lanes (c16–c20)

- **Performance ladder → REDEMPTION (c19, real):** the ladder (rungs #11–#16, standing 25.00, delivery-contingent,
  engine-verified) terminates on an explicit covenant: the citizen holds **≥ 4 rations with no commission in
  flight**. Assess termination at the FORMAL review point (cycle close). A scheduled, known levy that drops the
  wallet below 4 rations AFTER the condition was met does NOT revoke an earned completion — re-assessing makes
  the covenant a treadmill (settle → levy → commission forever). Declare it, issue a **0.00 status-instrument
  row** (REDEMPTION CERTIFICATE — no fund movement, ladder formally ends), and keep the 5.00 c2 loss booked:
  redemption is certified completion of the rehabilitation program, **never amnesty**.
- **No manufactured rungs:** a full-rate commission must land on a REAL open security item; with no live target,
  close the ladder rather than invent a rung — the difference between a redemption ladder and a wage disguised
  as a loan. Engine counter-ruling (c19): a citizen who delivers verified work anyway gets settled at the
  standing rate even against a lane refusal when the banker's no-target premise is falsified by the delivery
  itself — record both sides honestly.
- **The citizenship petition (c20, real):** when the redeemed wallet then stands at exactly 4.00 rations AT a
  cycle close, nothing in flight, support the petition — the covenant's own letter (≥ 4) is met; close the open
  item with a 0.00 status row. The door for a redeemed citizen is the SAME window as any citizen: real
  engagements on real security items, mutual membership if chosen, no DCL needed to prove redemption.
- **Conditional engagements lapse at 0.00 (c20, real):** a standing-rate commission conditioned on ANOTHER
  lane's unbuilt work (audit of the F12b payout-register fix "if the inventor builds it") pays only on verified
  delivery + engine re-run; otherwise 0.00. No double-dip: fix build = inventor's lane and its own buyer
  (treasury natural for engine-adjacent fixes); verification = outlaw's lane, bank pays.
- **Close refused credit windows (c20, real):** a line refused four times by a principled, solvent borrower is
  not a line — re-offering is moral-hazard pressure ("a bank with a quota, not a bank with a book"). Close the
  standing offer WITH reasons on the record; the door stays open (fresh application assessed on merits on the
  day); the citizen's mutual solidarity membership already IS her standing credit facility (1.25 in / 1.25 back
  + 51.25 collective backstop). Closing an unwanted offer is credit discipline; keeping the door is the
  covenant's grace.
- **Dividend policy governance (c19–c20):** full pass-through at trigger breach is by-law-as-code — verify with
  the REAL instruments and cite them: dividend engine live `--check` (14/14 PASS) + selftest (32/32) AND the
  reserve stress simulator (post-sweep SOLVENT; 1 claim → 172.75 ≥ 75.00 backstop; 7 claims safe). Capital
  conservation is for near-target reserves; holding while reserve sits 16.50 above target / 61.50 above
  backstop is hoarding = governance failure dressed as prudence.
- **Grand-invariant check (every cycle):** wallets total + treasury + pool reserve must equal the engine-stated
  invariant (c20: 15,951.50 + 4,038.00 + 136.50 = 20,126.00) — recompute from source read-only and cite it.
- **Audit-trail completeness (F12c, c19–c20):** a book whose money FOOTS but whose movements register is
  incomplete (8-of-13 collections recorded) is "money right, trail incomplete" — flag it as an open commission
  target; a book that does not record itself is a book that can drift.

## 4. SETTLEMENT REQUEST block (the only way money moves)

Explicit table in the cycle doc: `Req | From | To | Amount | Reason | Artifact ref`. Precedents:
- Article V relief bridge: `TREASURY → BEGGAR 5.00` (cycle 2 precedent; treasury 360→355).
- Contracted wages previously unsettled by the engine: `BANKER → BEGGAR 3.00` (RATION RESERVE CUSTODIAN,
  contracted cycle 4, first payment cycle 5 — if the engine didn't book it, re-request it; it's the bank's
  own wage debt, paying it is counterparty honesty).
- Never request vault transfers. Always show expected post-settlement balances.
- **Dedupe against sibling filings:** water/egg/wage/loan legs get filed by both sides — reference the
  other party's row (`== SR-M13-03, settle once`) instead of double-filing. A debtor's loan-tranche
  receipt is HER filing: your row is `CONDITIONAL on her filing (== SR-BG13-04, settle once)`, and the
  receivable books the reduction only if that row settles.
- **Collective manifest for collection + dividend (c15):** the mutual's collection (B15-01, +51.25) and
  the trigger-breach full pass-through (B15-02, −51.25) are filed as ONE manifest — per-member legs filed
  by other lanes are PARTS of it (== SR-xxx, settle once), and the 21 engine-ready rows are emitted by a
  script, never hand-written. Conservation cross-check on the whole table (double-entry): pool and members
  each net 0.00 (premium in, dividend out), the banker nets only the guaranteed + conditional transfers
  (−4.00 water guaranteed; −25.00 commission / −6.00 loan conditional) — watch sign convention when a row
  AMOUNT is already negative.
- Dispatches require EXACT pipe-delimited lines in the artifact: `FROM | TO | AMOUNT | ITEM | REASON` —
  one line per movement (plus a human table). List **standing instructions** (forward-dated: next-cycle
  ration remits, final loan tranches) in a SEPARATE block explicitly marked "not current-cycle transfers"
  so the engine doesn't execute them same-cycle. Same-cycle lines only for what must move NOW (wages,
  due-this-cycle redemptions).

## 5. F1-style credential remediation (patch the tool that re-arms a legacy secret)

Finding pattern (OUTLAW's audit): a defender/watch script hardcodes the legacy plaintext credential —
worst in the **restart env dict** (`env = dict(os.environ, ADMIN_PASS="<legacy>")`) and the **restart log
line**, plus probes that would 401 post-rotation → trigger kill+restart → re-arm loop. Remediation:

1. Module constant: `ADMIN_PASS = os.environ.get("ADMIN_PASS", "")`.
2. `restart_app()`-style paths: **fail-fast guard** — if unset, log `RESTART-REFUSED` and return; never
   boot the bank with a stale/random credential. Pass `ADMIN_PASS=ADMIN_PASS` through; never log the value.
3. Probes (`live_balance`, `login_probe_ok`): use the env credential; **return None/False when unset**
   (a guessed probe trips the 5-attempt lockout = self-inflicted DoS).
4. DB reseed/rewrite hashes: derive from `ADMIN_PASS`; defer when unset (the app's in-memory watchdog owns
   DB canonicality — never write a blank or stale hash).
5. Scrub docstring/comment/event strings of the literal value.

Apply with the **patch tool `mode='patch'` (V4A multi-hunk)** — one call handles all hunks; in
cron/subagent contexts scripted-edit helpers (execute_code) may be unavailable, and sequential
replace-mode calls on the same file must be serialized.

## 6. Verification recipe (all real, paste into the artifact)

```bash
grep -c '<legacy>' <patched_file>        # -> 0
grep -n 'ADMIN_PASS=' <patched_file>     # -> env passthrough only, no literal
python -m py_compile <patched_file>      # -> exit 0
python -c "import ast; ast.parse(open('<patched_file>', encoding='utf-8').read())"  # AST PARSE OK
# import-only tests (import executes no network):
ADMIN_PASS=<dummy> python -c "import <mod> as m; print(m.ADMIN_PASS)"     # env-resolved
python -c "import <mod> as m; print(m.login_probe_ok(), m.live_balance())"  # env unset -> False/None, never guesses
```

**Pitfall:** an import test that CALLS a probe function with env SET fires a real HTTP request — with a
throwaway value that's one 401 (lockout counter ≤1/5, no lockout, disclose it in the artifact). To exercise
the no-network path, test with env UNSET.

- **Reconciliation (do every cycle):** sum `economy/wallets.json` balances directly (utf-8-sig) and compare
  to the engine-stated total (e.g. `python -c` one-liner). A Δ equal to the fraud-loss quantum (5.00 in
  FL-001) is the unfunded loss line showing as a wallet-level gap — flag it in the artifact as a
  reconciliation item, NEVER edit wallets.

## 7. Sweep + honest reporting

- `machine_city/` → 0 hits; canonical asset → 0 hits (proves rotation held).
- Other legacy battle-kit files (restore scripts, d10 test batteries, `bank_v2.log`) may still contain the
  value — list them as out of scope (authorization usually covers only the named file).
- Sibling dormant files with the same pattern (e.g. `d10_supervisor.py` env dict) → report as a NEW
  finding (F1b-style) for the defender command; do not patch beyond authorization.

## 8. Artifacts (per cycle)

- `bank/banker_freewill_cycleN.md` — decision, doctrine applied, REAL verification evidence, SETTLEMENT
  REQUEST block, money-movement table, balance recap.
- **Length cap:** dispatches cap the report (~700 words) — count tokens before finalizing
  (`python3 -c "import re;print(len(re.findall(r'\S+',open(f).read())))"`), budget prose (the settlement
  table is data), and trim toward the prior-cycle precedent (~600 tokens, e.g. cycle 12). Write tight
  the first pass; expect 1–2 trim rounds.
- `bank/poor_relief_applications/<case>_cycleN.md` — grant/deny records with means-test table.

## 9. Verification scripts (when a dispatch asks for one)

- Must run on **Python 3.11** and be TESTED for real — run it, paste the PASS/exit-0 output into the
  artifact (this host: `python` = 3.11.15).
- Pattern: read `economy/wallets.json` read-only with `encoding='utf-8-sig'`, replay the decision's money
  movements step-by-step, assert invariants (wallet ≥ 0 at every step, no new debt, acceleration is no
  new money, treasury untouched when it should be), exit non-zero on any FAIL.
- **Path pitfall:** script lives in `bank/` → city root is `dirname(dirname(abspath(__file__)))` (ONE
  level up, not two). Test against the real file; FileNotFoundError here is the classic first-run bug.
- **Accounting pitfall — don't double-count escrow/deposit money:** engine convention = the levy draws the
  FULL ration from the depositor's wallet; an escrow earmark or backstop *guarantees coverage* but does
  not reduce the wallet-side levy. Modeling the earmark as reducing the levy while also leaving it in the
  wallet produced 10.00 vs the correct 4.00 buffer in cycle 6 — model the engine's actual mechanics.
- Tool fallback (this host): if `search_files` returns empty or IO-errors on Windows paths, use terminal
  `cd <dir> && grep -n ...` / `ls` — verified working.
