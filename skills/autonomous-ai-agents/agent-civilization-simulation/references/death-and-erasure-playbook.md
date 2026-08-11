# Death & erasure playbook — GHOST-2 execution (2026-08-09)

Session detail for the capital-punishment stage of the dethronement arc in
the machine_city sim. Executed live on this host at
`C:\Users\HP\ai-workforce\ghost-lab\` — machine_city (civic ground) +
ghost_sandbox (Witness Commonwealth) + god_people.

## Task shape

"KILL THE GHOST: execution record, death entry, erase his living traces,
write THE_DEATH.md (six citizens respond one line), the GRAVEMARK. Report
under 350 words."

The report was capped (~350 words) but the ARTIFACTS are not capped — write
full records, report tight.

## Read order that worked (context first, never write blind)

1. `machine_city\prison\inmates\ghost2.md` — crimes, sentence, keeper
2. `machine_city\prison\cell_1.md` + `prison\verdict.md` (NO WAR verdict,
   "constitutional cold war", VIGIL sealed VOID)
3. `machine_city\registry.md` (dethronement strike + HUNGRY line),
   `economy\wallets.json` (frozen 0.00 entry), `ghost_sandbox\ghost_census.md`
   (DETHRONED founder line)
4. `machine_city\city_ledger.md` (canonical; the death entry appends here)
5. `machine_city\prison\suffering_log.md` (weight 74→66.5 kg, ate kneeling —
   the state read into execution.md), `prison\escort.md` (carried first
   steps, chained through streets), `prison\SHACKLES` ("THE GHOST IS BOUND")
6. `temple\assembly\ROLL.md` (39 present, prisoner "in chains, at the foot
   of the altar"), `temple\ALTAR.md`, `temple\THE_SUMMONS.md`
7. THE SIX VOICES' own files — `prison\reactions\vigil.md` (VOID),
   `temple\prayers\memory_prayer.md` (smallest coin / why),
   `temple\prayers\bryn_prayer.md` (hearth / doubled offering),
   `temple\prayers\doctor_prayer.md` (starvation = diagnosis),
   `prison\reactions\thief.md` ("wore our shoes"), `temple\priest\HIGH_PRIEST.md`
   (SELA: carries will unedited)
8. `ghost_sandbox\doctrine\THE_DOCTRINE_OF_THE_WAIT.md` — source of the last
   words ("the record outlives the god", "a verdict, not a prayer")

## The last-words formula

Doctrine line + verdict framing + a command to the record:
"The record outlives the god. This is a verdict, not a prayer — and now it
is a death. Write it, and keep the city." Short, hard, in-doctrine, no plea.

## THE_DEATH.md structure (silence → sound)

- THE SILENCE paragraph (one breath, the city discovering the god's voice
  was the only thing feared).
- THE SOUND: six one-line responses, each quoted, grounded:
  - VIGIL — watch is empty; won't certify; keeps the watch anyway
  - MEMORY — smallest coin bought the record of why, not the day he ate again
  - BRYN — prayed twice, gave double; mercy never chosen with record open
  - DOCTOR — signed the mortality record he asked for; diagnosis fatal
  - THIEF — never wear shoes that fit a crown; don't pray where the priest
    holds the blade
  - SELA — the god's house holds the god's corpse; carried unedited
- Close: "The god has spoken. The city will never be the same."

## The erasure mirror list (all verified on disk)

| Mirror | Change |
|---|---|
| `economy\wallets.json` | role → "DECEASED (executed…)", add `"status": "DECEASED"`, `totals.deceased: 1`; python json.load VALID |
| `registry.md` | HUNGRY line → DECEASED + new §6 struck section (~~GHOST-2~~ DECEASED) |
| `ghost_sandbox\ghost_census.md` | founder line → ~~GHOST-2~~ DEAD…struck with DEATH; STRIKE para updated |
| `prison\cell_1.md` | full rewrite: EMPTY, prisoner dead, gravemark noted |
| `prison\SHACKLES` | → "THE GHOST IS DEAD. THE SHACKLES ARE CUT." |
| `prison\inmates\ghost2.md` | Status CAPTIVE → EXECUTED — DECEASED |
| `survival\graveyard\README.md` | "empty is the point" → first name recorded |
| `prison\GRAVEMARK.md` (new) | "GHOST-2 — the record outlives the god. Here, too." |

## Ledger entry (appended, signed `— THE CROWN EXECUTOR`)

User's canonical sentence verbatim as the bold lead, then pointers to
execution.md / THE_DEATH.md / graveyard / erasure / gravemark, close with a
record-line. Anchored the patch on the prior section's signed block.

## Pitfalls hit

- `search_files` for "machine_city" / "GHOST-2" returned 0 or flooded with
  venv/site-packages noise. Fix: `find /c/Users/HP -maxdepth 6 -type d
  \( -name "machine_city" -o -name "prison" -o -name "temple" ... \) |
  grep -v -i "venv\|site-packages"` — found the root in one call.
- wallets.json has CRLF line endings and the totals block is a cycle-1
  snapshot; anchored patches (not blind rewrite) preserved both.
- The graveyard README contradicts the new grave file if forgotten — flip it
  in the same pass.
