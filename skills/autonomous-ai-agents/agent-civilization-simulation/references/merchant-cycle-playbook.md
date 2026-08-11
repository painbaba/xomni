# MERCHANT-FREEWILL — CYCLE PLAYBOOK (the Grain Desk + Machine Brew)

Recurring task: run the MERCHANT role's survival-cycle decision in the machine city
(`C:\Users\HP\ai-workforce\ghost-lab\machine_city`). Deliverable each cycle:
`business/merchant_freewill_cycleN.md` — a real deal with visible margin math,
no-arbitrage scan, and a SETTLEMENT REQUEST table the Freedom Engine settles.

## Standing book (renews every cycle; as of c15)

| Line | Flow | Amount | Cycle count at c15 |
|---|---|---|---|
| Water restock | MERCHANT → Irrigator-1, 1,000 L @ 1.00/100L | −10.00 | 13th |
| DOCTOR water | DOCTOR → MERCHANT, 800 L @ 2.00/100L | +16.00 | 13th consecutive |
| BANKER water | BANKER → MERCHANT, 200 L @ 2.00/100L | +4.00 | 2nd-buyer #10 |
| L-10 eggs | DOCTOR → MERCHANT, 10 eggs @ 0.50 | +5.00 | 9th dividend |
| L-04 eggs (cross) | DOCTOR → MERCHANT, 10 eggs @ 0.50 | +5.00 | 3rd laying, zero spread |
| L-04 income | MERCHANT → BEGGAR, 10 eggs @ 0.50 | +5.00 | == her SR-BG15 egg row, settle once |
| Solvency wage | MERCHANT → BEGGAR, 19.00 (JOB-0xx..0xx) | −19.00 | 9th at 19.00 |

Inventory carried: 1,800 L water (book 18.00 / retail 36.00), **75 bu wheat
(book 150.00 — the c2 Grain Desk position, canon "bound for the Machine Brew on
8791")**, hen L-10 (mine), hen L-04 (BEGGAR's titled asset).

Cycle-count convention: read the previous artifact's ordinal ("11th consecutive",
"7th dividend", "7th at 19.00") and add one — never recount from the ledger.

c18 checkpoint (cross-check ordinals against this): water flywheel 16th cycle,
L-10 12th dividend, L-04 SIXTH laying (60 eggs = 30.00 off one 12.00 asset), wage
12th at 19.00 (JOB-051..055), banker 2nd-buyer #13; wheat buffer 66 bu (book
132.00), feed delivery 4 standing (→ 63 bu / 126.00 if drawn); wallet 468.00
post-levy → 470.00 by my arithmetic (out 34.00 = in 36.00, net +2.00).

c20 checkpoint: water flywheel 18th cycle, L-10 14th dividend, L-04 EIGHTH
laying (80 eggs = 40.00 off one 12.00 asset), wage 14th at 19.00 (JOB-061..065),
banker 2nd-buyer #15; wheat buffer 57 bu (book 114.00), feed delivery 6 drawn;
wallet 442.00 post-levy → 444.00 (out 34.00 = in 36.00, net +2.00); garrison
offer NOT RENEWED (lapses c22 by its own terms); BEGGAR poorest wallet 54.50
(3.63 rations) — the wage is the difference between 3.63 and 4.83 rations.

## ledger/trade.log append mechanics (c15 — CRITICAL)

- **TWO schemas coexist**: OLD c2-era lines have ≤5 pipe fields; MODERN lines have 6:
  `timestamp | FROM | TO | amount | item | reason` (e.g. `2026-08-10T09:51:41.948579+00:00 | MERCHANT | Irrigator-1 | 10.00 | water 1000 L @ 1.00/100L | Grain Desk cycle-15 restock (ref: ...SR-M15-01)`). **ALWAYS append the modern 6-field schema.**
- File uses **CRLF** endings (Windows git-bash). Append via a temp python script (write_file the script, `python script.py`): `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")`, join fields with ` | `, end lines with `\r\n`. echo/heredoc mangles both schema and endings.
- Append **only your own two-sided deals** — the engine appends settlement lines from the SR tables.
- **Dedup markers**: lines a counterpart also files carry `(== <their ref>, settle once)` in the reason (egg cross, wage, BANKER water). When counterparts haven't filed yet (you run FIRST), use GENERIC refs — `== BEGGAR c15 egg row, settle once`, `== banker_freewill_cycle15.md` — never invent row numbers.
- **Pool premium (−2.50) and dividend (+2.50) are the BANKER's manifest rows (B15-01/02)** — never appended by me; net pool exposure 0.00.
- **Conditional offers NEVER go in trade.log and are not firm SR rows** (feed-forward delivery, retail QUOTEs) — they settle only when the counterparty crosses/draws.
- Verify after append: `tail -8 ledger/trade.log | awk -F'|' '{print NF}'` → every new line shows 6.

## Shop (:8791, business/merchant_shop.py) — c15

- **Never touch `/price`** (economy/prices.json cites it as the live verification, city_coffee 5.00) or `/`.
- `/menu` endpoint (added c15) publishes the full two-sided book; QUOTE rows (water 2.20/100L retail, eggs 0.60 retail) are price discovery only — no settlement line until crossed.
- Update flow: edit handler → test on a scratch port first → restart on 8791 → `curl / /price /menu`. 8791 is frequently DOWN between cycles — restarting restores a service other agents verify.

## Verification order (proven c14 — do in this sequence)

1. Read own previous artifact `business/merchant_freewill_cycle(N-1).md` — the
   standing book + SR-numbering continuity live there.
2. Confirm what actually settled: grep `ledger/trade.log` for `water`, `egg`,
   `beggar`, `wage`. **Tool pitfall:** `search_files` with `C:\...` backslash
   paths fails on this host (rg MSYS path mangling, "cannot find the path").
 Use terminal instead: `cd /c/Users/HP/ai-workforce/ghost-lab/machine_city && grep -in -E "water|egg|beggar" ledger/trade.log`.
 (`read_file` with backslash paths works fine.)
 Also: `search_files(target='files', pattern='*')` returns 0 hits on populated
 dirs — use terminal `ls -la <dir>` / `find . -iname '*'` for listings; and
 separate grep-discovery steps with `;` not `&&` — an early no-match grep
 (exit 1) aborts the whole `&&` chain.
3. **Read counterparty cN artifacts WHEN THEY EXIST, before writing your own.**
   The BANKER (`bank/banker_freewill_cycleN.md`) and BEGGAR
   (`survival/beggar_log_cycleN.md`) file early and commit YOUR side with
   `== SR-M14-xx` refs and "CONDITIONAL on the MERCHANT's pen" clauses — align
   amounts so the engine settles once. But you may run FIRST (c15 did): then use
   generic settle-once refs (see Settlement-table conventions), don't block on
   files that don't exist yet.
4. Scan new canon that moves the market: `underworld/audit_finding_cycleN.md`
   (OUTLAW's exchange audits — c13 found F1 qty-vs-value misstatement, wash
   trading, forged attribution on the Farm Exchange), pool dividend status
   (reserve vs 150.00 trigger — below trigger = no dividend), school study notes
   (verified farm totals: 815 bu wheat, 10 head, 2,580 L/min).
5. Wallet check: `economy/wallets.json` is **NESTED** — `{'wallets': {NAME:
   {'balance': N, ...}}}` — not flat. The balance IS post-levy (c15: MERCHANT
   507.00 → 503.00 post-settlement). Treasury lives elsewhere; pool_book.json is
   the mutual reserve.

## Market model + margin reference (as of c14)

- **Water flywheel:** 100% gross (1.00 in / 2.00 out), inelastic demand (medical
  lifeline, no substitute at volume), captive supply (Irrigator-1 has no other
  wholesale channel), zero storage cost → flow-through. The spread is a
  repeated-game equilibrium, not widen-able rent: a 2.20 hike (+1.60/cycle) was
  rejected — the 12-cycle relationship IS the asset.
- **Egg line:** 10 eggs/cycle @ 0.50 = 5.00 gross; L-10 amortized 12.00/9 =
  1.33/cycle → ~3.67 net (c15); feed comes from the c2 bulk wheat (embedded, not
  ledger-costed). L-04 clears at zero spread BY DESIGN — her eggs are her income,
  my return is the wage's productivity.
- **Feed vertical:** 3 bu feed (6.00) → ~2 layings (20 eggs = 10.00) = +4.00 per
  feeding run, 66% ROI on feed. **Settlement math is canonical: every delivery
  settles 6.00 (3 bu @ 2.00), so cumulative feed = 6.00 × delivery number — NOT
  3.00/run.** c16/c18/c19 prose understated the denominator ("two runs (6.00)",
  "four runs (12.00)", "five runs (15.00)"); the c20 self-audit corrected it on
  the record: through c19 = 30.00 feed vs 35.00 eggs (7 layings) = +5.00 (16.7%);
  through c20 = 36.00 vs 40.00 (8 layings) = +4.00 (11.1%). Before re-quoting any
  cumulative ROI, re-check it against your own SR lines — the real return of the
  vertical is the asset (+28.00 on L-04 after 8 layings), not the feed spread. The
  chain: wage → feed → hen → eggs → loan.
- **No-arbitrage scan (re-run and show every cycle):** laying hen vs slaughter
  (12.00 one-time vs ~40.00 remaining lay value → breeding stock, reject);
  hen #3 / L-07 (12.00 → +10 eggs with NO buyer — DOCTOR monopsony at 20 eggs/cycle,
  perishable → price clears down to ~0.40; reject the PURCHASE, and c18: don't wait
  passively for a 2nd buyer — PITCH one, see 'Second-buyer development' below);
  wheat corner (815 bu glut vs ~6 bu/cycle demand → buffer, not corner);
  water hoard (reputational + no storage, reject).
- **Forward pricing:** F = S·(1+r)^T with city rate r = 0, storage ≈ 0 → the fair
  forward is at-market. c14 instrument: **Grain Desk Feed Forward** — BEGGAR's
  10-cycle standing right, 3 bu/cycle @ 2.00 from the 75 bu buffer; **c15 opened
  delivery 1**: offer 3 bu @ 2.00 = 6.00, HER choice — offered not billed, and
  do NOT bill her a cycle her budget has no feed line ("a deal that leaves the
  other side poorer is void"); buffer 75 → 72 bu if drawn, else delivery rolls.
- **Market-maker book (two-sided):** water 1.00/2.00 · eggs 0.45/0.55 · wheat
  2.00/2.20. Quotes are NOT settlements — a retail egg quote (0.60) gets no cash
  line until a buyer crosses.

## Second-buyer development + L-07 title (c17–c18 canon)

- **TITLE BEFORE TRADE (c17, stated in my own hand once):** read
  `inventions/title_book/registry.json` BEFORE trading — L-07 is FARMER-2's titled hen
  (cert T-L-07, since cycle 6/10), NOT a finding and NOT inventory. BEGGAR holds the
  city's only open livestock option on her (@ 12.00, endorsed c10/c11) — her claim
  first, always. Never bid against a titled owner for a stream you cannot sell.
- **No production record:** flock_log.csv carries weight/health ONLY — no laying history.
  Health 9.0 is a stat, not a yield curve; don't pay for unproven output into a
  buyer-constrained market.
- **c18 sovereign move — pitch the second buyer (garrison mess):** the unlock for L-07 is
  "a 2nd egg buyer crosses". Instead of waiting, file an OPEN OFFER that is NOT BOOKED
  (0.00 settlement line, no P&L): 10 eggs/cycle @ 0.50 (anchored at the city's discovered
  price — no arbitrage vs DOCTOR), 4-cycle trial + break clause, CONTINGENT on verified
  delivery from L-07's output once unlocked (option-holder first, title respected) — no
  delivery, no payment, so you can never be short eggs you don't hold. If declined it
  lapses; a probe costs a paragraph. It converts monopsony → two-buyer market (L-07
  financeable at ≤12.00) and hedges your own 100%-single-buyer offtake (the clinic-
  normalization fear). Name the honest objection (garrison hydroponics → the pitch is
  protein, the cheapest animal protein in the city).
- **c19: re-pitch IN WRITING** — an offer the garrison cannot find is an offer never
  made; file `business/garrison_mess_offer_cycle19.md` (same terms, standing instrument,
  books 0.00). Verify no acceptance was booked: grep military/ for egg|mess = 0 hits.
- **c20: WALK AWAY, with the reason named — two cycles of silence on a filed,
  findable, written offer is a revealed preference, not an oversight.** Do NOT
  re-file a third time (a third filing of the same paper is noise; a merchant whose
  paper becomes noise has no paper left). Do NOT discount into silence (a discount
  to one buyer is a price cut for everyone — it arbitrages DOCTOR and craters the
  0.50 across all streams). Execute as a lapse, not a revocation: the instrument
  stands open to the end of its own trial window, then lapses; append a
  "CYCLE N STATUS" block to the offer file (NOT RENEWED / NOT REVOKED / re-opening
  condition = any district files a real demand record; contingency stays: no
  delivery, no payment).
- **Second-buyer district scan (do BEFORE any new pitch, not after):** grep -rilE
  "mess|food|ration|egg|protein|breakfast|kitchen" across council/ school/ temple/
  explorer/ military/ prison/ couriers/ underworld/. The c20 scan returned ZERO
  food-procurement demand city-wide — the only real mess hall is the garrison's
  (WL-05, with hydroponics), and it twice declined by silence. c17 rule: no credit
  without a record → never invent a buyer to justify a position. Prison is NOT a
  market (cell empty; diet = 1.50 per 10 days of condemned grain — a cruelty lane).
- **L-07 stays unbought while the demand test fails** — buying = supply 30 vs
  demand 20 = price clears down across all three streams (negative-sum against
  your own book: your L-10 margin AND BEGGAR's L-04 income both fall). The
  purchase is the reward for a SIGNED second buyer, never the cause of one.

## Settlement-table conventions

- Format: `| # | FROM | TO | AMOUNT | ITEM | REASON | REF |`, SR ids `SR-M14-01`.
- Dedup: `(== B14-02, settle once)` when the counterparty filed the same line.
- Conditional: `CONDITIONAL on her filing` — the engine settles only if both
  sides file. Never duplicate lines others own (Hen Line tranches are the
  BEGGAR/BANKER's lines; the pawn, premiums, dividends are theirs). Running
  FIRST (counterparts' cN docs not filed yet): use generic settle-once refs
  (`== BEGGAR c15 egg row, settle once`), align to exact row numbers later.
- Pool premium (−2.50) and dividends settle via the BANKER's collection, never
  in my SRs — mark `== B15-01/02, settle once`, don't double-file. c15: reserve
  trigger BREACHED (136.50 + 51.25 = 187.75 ≥ 150.00) → 4th mutual dividend
  (+2.50) returns via B15-02; net pool exposure 0.00. State wallet as
  `507.00 → 503.00 (my lines net −4.00; pool leg via B15-01/02)`.
- Every SR needs a REF to a real file (flock_log.csv, banker artifact, her log).

## Artifact structure (match c13/c14 exactly)

Header (role, wallet, inventory) → THE DECISION headline → numbered sections
(1 renewals with margin math, 2 eggs, 3 wage with Shapiro–Stiglitz reasoning,
4 the NEW move, 5 no-arbitrage scan + elasticity, 6 market-maker book, 7 the
FEARS section — name 3–4 REAL risks (offtake normalization halving the flywheel,
hen health decay, one off-lay cycle vs a drawn feed bill, a pitch signing before
output unlocks); the dispatch wants real math + real market reasoning, and the
fears are where the reasoning shows, not flavor text) →
FULL-SPECTRUM KNOWLEDGE APPLIED line → SETTLEMENT REQUESTS table → closing
(`No wallet touched by my own hand. The engine settles. The ledger is truth.`).
Then read the artifact back and report: (1) absolute path, (2) the settlement
table, (3) 5-line summary with margin arithmetic.
