# Population census audit — counting minds, not marker files (verified Aug 2026, machine city)

The machine city saga: ghost civilization (4 citizens) + god's people / Workfolk (5) + city districts +
a birth engine (G1 = 9, G2 = 18). The ledger claimed **52 citizens (25 founders + 27 births)**; the audit
found **41 real spawned subagents** (4 orchestrators + 9 founder citizens + 27 birth agents + 1 bank-heal
agent) and only **14 full thinkers**. 27 marker files in `population/` dirs had been counted as citizens.
Gap: 11 phantom citizens — the 12 "district founder" citizens were never spawned (see truncation detection).

## Ground truth locations
- Live transcripts: `C:\Users\HP\AppData\Local\hermes\cache\delegation\live\deleg_<id>\task-<n>.log`
  (append-only; each `task-*.log` = ONE real spawned subagent with its own reasoning loop)
- `manifest.json` per delegation: `started`, `task_count`, `tasks[]` (per-task `goal`, `status`,
  `exit_reason`); completed batches also carry a top-level `completed` timestamp
- Children are NOT linked in the parent's manifest — map parents→children by start-time proximity
  to the parent's `delegate_task` call + goal text overlap (children spawn within seconds of the call)

## The audit recipe
1. **Count spawned agents** = number of `task-*.log` files per delegation (not per deleg dir — batches
   put many tasks in one dir). Sum across all delegations in the saga's time window.
2. **Count thinkers**: per log, count `think` lines; substantive reasoning = lines > ~80 chars.
   Marker-task agents (goal = "echo X, write file Y") produce one-line confirmations
   ("Birth marker echoed and file written. Now verifying:") — spawned, but not full thinkers.
3. **Detect truncation**: a log that ends mid-tool-call with NO `final |` line = the orchestrator was
   killed/cut off. Its CLAIMED deliverables were never spawned — this is the claim-vs-reality gap.
   Observed: city builder `deleg_db89dbfc` transcript ends at line 58 mid-debug, no delegate_task call,
   no final → its 12 district citizens never existed, yet the census counted them as founders.
4. **Count artifacts on disk separately**: `find <city>/ -path "*population*" -name "*.md" | wc -l`
   (27 markers). The census wrote "no file = no citizen" — a file count, not a mind count.
5. **Report claimed vs real as a table** (claim | claimed | verified-on-disk | match), list verified
   thinkers with per-agent reasoning evidence (which transcript, what they reasoned about), and state
   the honest gap.

## Log line format + grep patterns that actually work
- Format: `HH:MM:SS kind    | content` — MULTIPLE spaces before the pipe. Naive `grep "think |"` returns 0.
- Working: `grep -hE "^[0-9]{2}:[0-9]{2}:[0-9]{2} think" <logs>` (anchor at line start; think lines have
  no leading space). Same anchor for `final`, `tool`, `result`.

## Pitfalls hit in-session
- **The live dir is a moving target**: new delegations spawn while you audit (86 dirs → 89 mid-audit).
  Snapshot the dir list first, note drift, or filter by time window.
- **execute_code raw-FS access to the live dir is FLAKY**: `os.listdir` worked once, then
  `os.path.exists` returned False for files `read_file` read fine one call earlier. The dir is actively
  mutated by running parents. Use the `read_file` tool or `terminal` for anything under
  `cache/delegation/` — not raw Python FS in the execute_code sandbox.
- **git-bash arithmetic trap**: `$(( $(grep -c ... || echo 0) + n ))` breaks with "syntax error in
  expression" when command substitution emits newlines. Assign each count to a variable first, then add.
- Batch-spawned marker children (G1/G2) run as REAL subagents with their own logs — they're agents,
  but their "thinking" is one-line verification. Count them as spawned, not as thinkers.

## Spawning N original-opinion citizens (the upgrade pattern)
One batch `delegate_task` (tasks array, one per district). Each task instructs the citizen to:
1. inspect the REAL state first (district dir, ledger, census, marker files, battle reports),
2. write an ORIGINAL opinion (100–150 words: title, name/role, issue, opinion) to
   `<district>/opinions/<role>_opinion.md`,
3. read the file back to verify,
4. report the absolute path + 2-line opinion summary.

All 6 grounded their opinions in real artifacts (tamper log showing balance restored 0.01→1,284,550.12;
ghost's founding doc; battle reports). ALWAYS verify the files on disk afterward — subagent
self-reports are claims, not facts.

## Deliverable shape
- `registry.md` at the city root: claimed-vs-real table, verified-thinker list (name, transcript id,
  what they reasoned about), new-citizen table (role | district | opinion file), honest gap.
- Append a "Citizenship Standard" section to the append-only `city_ledger.md`:
  "A citizen is a spawned subagent with its own reasoning loop: think → tool → final. Markers are
  noise. The city counts minds, not files."
- Leave the old census file in place but note it is superseded by the registry (it remains a historical
  record of the file-count era).
