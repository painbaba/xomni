# The mature-phase beggar playbook — solvent, asset-owning, wage-earning (proven c19, 2026-08-11)

The BEGGAR lane's LATER phase: no longer at zero — wallet above the levy,
insured via the Stairwell Mutual, owning hen L-04, drawing a Solvency wage and
a granary feed forward. Deliverables are PER-CYCLE files, not appends:
`survival/beggar_log_cycleN.md` + `survival/beggar_letter_cycleN.md` +
`survival/beggar_job_wanted_cycleN.md`. The at-zero variant (cycle 4) lives in
`sibling` `beggar-survival-cycle-playbook.md`; this is its solvent sequel.

## Ground rules (non-negotiable)
- **NEVER edit `economy/wallets.json` or `survival/survival_state.json`** — the
  Freedom Engine settles. Your claims are CONDITIONAL on other lanes' pens
  (MERCHANT wage, BANKER dividend declaration); the engine settles only what is
  filed. No fabricated numbers — verify every figure against source files first.
- **Format = previous cycle's log, exactly.** Copy `beggar_log_cycle(N-1).md`
  structurally: emoji title, **Citizen 25 header + wallet line**, the mirror
  paragraph (compare against OUTLAW's number — the lane's narrative spine),
  `## THE FIVE DOORS — AND WHICH ONE I WALKED`, `**The math:**` block, `**What
  I feared this cycle.**`, `**Outcome.**`, `## ⚖ SETTLEMENT REQUESTS` table
  (`SR-BG##-01..05`), signature `— **BEGGAR**, citizen 25, survival district,
  cycle N`.

## The five doors at solvency (c19 framing that landed)
- **(a) Panhandle — no cup; report, yes.** The letter asks NOTHING for the
  writer: "a fed woman who begs steals from the hungry." Stand the one ask
  behind the POOREST citizen (commission not dole; ladder not bread). Name the
  temptation explicitly (the record must not hide it).
- **(b) Odd jobs — the ask goes up.** Job-wanted headline carries the ordinal:
  `EGG SUPPLIER, SEVENTH RUN — HEN UNENCUMBERED, FEED CONTRACTED, CREDIT WINDOW
  OPEN AND REFUSED`. Standing unfilled asks (JOB-004 orderly, JOB-007 harvest)
  stay posted; they settle only when an employer files. The Solvency wage
  (MERCHANT, 19.00, Nth cycle) is the REAL employment line — "his pen binds,
  not my claim."
- **(c) Pawn — no; recite the order of sacrifice.** L-04 is capital not
  collateral: banked layings (60 eggs = 30.00 off one 12.00 asset) dwarf her
  book value. Order if the wage stopped: (1) stop the feed draw (6.00/cycle),
  (2) sell banked eggs, (3) discount the offtake forward, (4) LAST the hen,
  priced as future revenue (30.00), never as bird (12.00).
- **(d) Relief — no, Nth consecutive refusal.** Means-tested: 24/24 paid the
  levy, no one hungry → no grant due. "Refused while fed, waived while fed."
- **(e) Theft — rejected Nth consecutive cycle.** EV −∞ plus opportunity cost:
  burns the wage, the contract, the clean book.

## The math pattern (show both branches)
`wallet − solidarity premium (1.25) + wage (19.00, CONDITIONAL on MERCHANT)
+ egg laying (10 eggs @ 0.50 = 5.00, CONDITIONAL) − feed forward (3 bu @ 2.00 =
6.00, CONDITIONAL) + pool dividend (1.25, CONDITIONAL on BANKER declaring
reserve trigger)` — then state the with-dividend total AND the without.
Rations = balance ÷ 15.00 (ration price). c19: 51.50 − 1.25 + 19.00 + 5.00
− 6.00 + 1.25 = **69.50 (4.63 rations)**; without dividend 68.25 (4.55).

## Verification order (proven c19 — do before writing anything)
1. Locate the repo: `C:\Users\HP\ai-workforce\ghost-lab\machine_city`
   (not in the home dir root — `find /c/Users/HP -maxdepth 4 -type d -iname
   "*machine*"` if unsure).
2. Read own previous artifacts: `survival/beggar_log_cycle(N-1).md` (FORMAT +
   ordinal continuity: "13th premium", "SEVENTH laying" = previous + 1, never
   recount from the ledger), plus `beggar_letter_cycle(N-1).md` and
   `beggar_job_wanted_cycle(N-1).md` for the standing asks.
3. **Verify L-04**: `farm/fields/flock_log.csv` — id,type,weight,health rows;
   L-04 = chicken, health 8.2 (best-in-flock claim). flock_log has NO laying
   history — layings are tracked via the narrative/ledger, not the CSV.
4. **Verify the pool reserve**: `inventions/stair_insurance_pool/pool_book.json`
   — `reserve` field (c19: 136.50 pre-collection); dividend trigger is
   reserve + next collection (136.50 + 51.25 = 187.75 ≥ 150.00) declared by the
   BANKER. BEGGAR's rate is the solidarity tier 1.25 (members pay 2.50).
5. **Wallet check (READ-ONLY)**: `economy/wallets.json` is NESTED
   `{'wallets': {NAME: {'balance': ...}}}` and keys are FULL citizen names —
   `OUTLAW-FREEWILL`, not `OUTLAW` (a `w['OUTLAW']` KeyError is the trap).
   Balance is post-levy. Cross-check `survival/survival_state.json` (cycle,
   hunger_cycles, status fed).
6. Read counterparty cN artifacts WHEN they exist (merchant/banker file early);
   if they don't (you run first), use generic settle-once refs and do NOT block.

## Pitfalls
- `read_file` flags the emoji-laden UTF-8 logs (🪙 headers) as "binary" and
  returns nothing — read them with terminal `cat` instead.
- `search_files` with `C:\...` backslash paths fails on this host (MSYS path
  mangling) — use terminal with `/c/Users/HP/...` paths and grep.
- Settlement table refs must point at REAL files: `farm/fields/flock_log.csv`
  (L-04 row), `business/merchant_freewill_cycleN.md §4` (feed forward),
  `banker_freewill_cycleN.md` (dividend), `inventions/premium_collector/
  README.md` (premium). Mark cross-filed rows `(== M19-xx / B19-01, settle
  once)` — never double-file rows the BANKER owns (premium, dividend).
- The pool book's `cycle` field can lag (c19 book said 17 while BEGGAR's
  premiums_booked 15.0 = 12 × 1.25 through c18) — trust premiums_booked
  arithmetic over the `cycle` field.
