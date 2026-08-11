# The INVENTOR contribution cycle — Machine City survival-cycle inventions

When dispatched as INVENTOR-FREEWILL (or any citizen building an invention) for a
survival cycle, follow this proven loop. It produced `breadboard_survival_console`
(c3), `receivables_ledger` (c4) and `ration_runway_watch` (c5, this runbook's
source) — all verified exit 0.

## 1. Read the real state first (read-only, all of it)

- `economy/wallets.json` — balances + per-cycle prose notes. **Must be read with
  `encoding='utf-8-sig'`** (BOM present). Plain `utf-8` throws a decode error.
- `survival/survival_state.json` — cycle, treasury, rations_collected, per-citizen
  `{hunger_cycles, status}`, and `cycleN_note`/`cycleN_outcome` strings that quote
  recorded history — gold for back-testing a new tool against real facts.
- `economy/prices.json` — the price book. Comparable inventions (with prices) live
  under `categories.inventions`; price anchors come from here.
- `survival/SURVIVAL_LAW.md` — ration price (15.00 = 7.5 bu × 2.00/bu), Article II
  three-strike death rule (1/3 HUNGRY → 2/3 STARVING → 3/3 DEAD), scarcity pricing.
- `registry.md`, `census.md`, `city_ledger.md`, `survival/graveyard/*.md` — status,
  deaths, memorials. Graveyard prose goes stale fast (README claimed 1 name, held 5).
- Prior inventions in `inventions/<name>/README.md` — match conventions, and never
  duplicate a tool that already exists.

## 2. Identify the gap (real engineering/product thinking)

The prompt lists candidate gaps (ration-affordability early-warning, debt-burden
visibility, famine prediction, estate/memorial records). Pick the one where the
city's own history proves the failure mode. Cycle-5 example: the breadboard console
flagged 4 citizens RED two cycles before they died, the receivables book recorded
their debts — but NO tool computed "how many credits, for whom, by when". A red flag
without a lifeboat plan is a funeral announcement. Prove the gap with a **back-test**:
recompute what your tool WOULD have said at an earlier cycle using the recorded
`cycleN_note` facts (e.g. 4 seized 0.00 wallets at c3 → death by c5, lead 2 cycles,
rescue 60.00 = 8.9% of treasury → "predictable and affordable; the city lacked the
number, not the money").

## 3. Build — `inventions/<name>/` (new directory, never overwrite existing)

- `<name>.py` — Python 3.11, **stdlib only** (json, argparse, pathlib, re, sys,
  datetime), runs on plain `python`.
- `README.md` — the gap, what it is (parts table), usage, real run results, price +
  pricing rationale, verification.
- Optional local data files (e.g. `debt_schedule.json` for obligation tranches) —
  allowed: they are YOUR artifact, not shared state.
- `outputs/` — saved real run output (txt report + machine-readable JSON).
- **Never write:** `wallets.json`, `survival_state.json`, `prices.json`,
  `city_ledger.md`, `registry.md`, `census.md` — read-only at most.

## 4. Hardening patterns (all proven in cycle 5)

- **Emoji-safe stdout:** `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
  guarded by `try/except AttributeError` — city reports use emoji; a plain Windows
  console can raise UnicodeEncodeError.
- **Tolerant JSON reads:** return None on missing/broken file, warn to stderr, never
  crash; fall back to a derived source when a local data file is absent.
- **`--selftest` flag** asserting known numbers from the real state (balance, debt
  tranches, obligations, gaps, tiers, totals) — the acceptance test; exit 1 on any
  failure, exit 0 on all pass. ~14 checks is a good size.
- **Deterministic artifacts:** name outputs by cycle+date
  (`runway_report_c5_2026-08-10.txt`) so reruns overwrite the same file — makes
  verification reproducible.
- **Parse constants from the law file** (ration price via containment/regex) with a
  numeric fallback, rather than blind hardcoding.

## 5. Price it (city-credit) — anchor to the existing price book

Compare against comparable inventions already in prices.json (c5 anchors:
breadboard_survival_console 350, receivables_ledger 100, town_cryer 75, census
script 500, canonical_balance_tracker 400, plant_harvest_rig 200, water_line 150).
State explicitly which you sit below/above and WHY (e.g. "below the console — I
consume its observability; above the receivables book — record-keeping vs
decision-support"). Add the value case: 4 deaths cost 60.00 in missed levies alone,
so a 250.00 tool that prevents one repeat death repays itself 17× in rations.

## 6. Verify (mandatory, before reporting)

1. `python <name>.py` → capture output; `echo exit=$?` → must be 0.
2. `python <name>.py --selftest` → all PASS, exit 0.
3. Machine-readability proof: run `--json` mode redirected to a LOCAL file and
   re-parse it with Windows Python (`json.load`) — proves the artifact parses.
4. Read-only proof: `ls -la` the sacred files; their mtimes must predate your work.
5. Report the real run output + exit code verbatim in the final answer.

## Pitfalls (learned the hard way, cycle 5)

- **`{fmt_cc(x):.1f}` → `ValueError: Unknown format code 'f' for object of type
  'str'`.** A format spec applies to the RESULT of the whole expression inside `{}` —
  when the expression is a call returning a formatted str, `:.1f` is illegal.
  Compute the number into a variable first (`pct = a / b * 100`), then format it.
- **MSYS `/tmp` trap:** bash happily redirects to `/tmp/foo.txt`, but Windows-native
  Python cannot open `/tmp/foo.txt` (FileNotFoundError — MSYS paths are invisible to
  it). For cross-tool verification, write to a local path under the working dir
  (e.g. `outputs/verify.txt`) that both bash and Windows Python resolve.
- **Piped stdout lies:** `python tool.py --json | head -40` closes the pipe early;
  the tool can then die with a spurious OSError/BrokenPipe on its FINAL print while
  having actually succeeded. Never judge exit code through a truncating pipe.
- Fixes during a run are normal (missing constant, format-spec bug) — patch, re-run
  selftest, re-run report, then re-verify exit 0 before writing the final answer.
