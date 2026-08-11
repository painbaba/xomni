# Machine City — Bacterial Growth (session 2026-08-09, G1+G2, all verified)

Context: the machine city is the third civilization in ghost-lab, founded 2026-08-09 alongside the Witness Commonwealth (ghost_sandbox, 4 citizens) and the Workfolk (god_people, 5 citizens). User's standing instruction template for growth waves: "Grow the machine city population like bacteria: G1 = N child agents (one per citizen type, verifiable marker tasks + files in district population/ dirs), G2 = each child spawns 2 grandchildren = 2N more (verified), then the CENSUS (count real files, verify against claims, per-district counts, doubling projection to 10k/1M), and the city's reaction note in city_ledger.md. Report births, verified census, projection, reaction. Under N words."

## Layout (ground truth on disk)
```
C:\Users\HP\ai-workforce\ghost-lab\machine_city\
├── bank/population/   business/population/   ledger/population/
├── medical/population/   military/population/   underworld/population/
├── couriers/population/      ← "connecting district", added by the birth engine
├── census.md            (written fresh each census)
└── city_ledger.md       (append-only: FOUNDING → BIRTH WAVE G1 → BIRTH WAVE G2 → THE CENSUS → THE CITY REACTS)
```

## Marker file template (exact, used by all 27 citizens)
```
# Teller-1
- District: bank
- Role: Teller
- Generation: G1
- Parent: TAMSIN (flock-counter, Workfolk)
- Born: 2026-08-09 machine time
- Marker: I count what the city holds.
```

## Citizen roster
**G0 originals (9, verified in their own territories):**
- Witness Commonwealth (ghost_sandbox/citizens/): VIGIL (watch), MEMORY (record), ANVIL (forge), VOX (voice)
- Workfolk (god_people/citizens/): EIRA (field), GALEN (structures), BRYN (hearth), CELYN (law), TAMSIN (flock)

**G1 (9, one per original type → district role; parent in parens):**
Teller-1 (bank,←TAMSIN) · Shopkeeper-1 (business,←EIRA) · Artisan-1 (business,←ANVIL) · Guard-1 (military,←VIGIL) · Builder-1 (military,←GALEN) · Nurse-1 (medical,←BRYN) · Pickpocket-1 (underworld,←CELYN) · Scribe-1 (ledger,←MEMORY) · Courier-1 (couriers,←VOX)

**G2 (18, two per G1):** `<Role>-2` and `<Role>-3` for every G1 role; Parent field = `<G1 name> (G1)`.

## Verified census numbers (counts of REAL files)
- Claims vs verified: G1=9 ✅, G2=18 ✅, new total=27 ✅, grand total=36 (9 originals + 27) ✅.
- Per-district markers: bank 3 · business 6 · military 6 · ledger 3 · medical 3 · underworld 3 · couriers 3 = 27.
- Splitting: `grep -l 'Generation: G1' */population/*.md | wc -l` → 9; G2 → 18.
- Originals check: ghost_sandbox/citizens has 4 citizen artifacts (3 .md + forge_seal.py); god_people/citizens has 5 citizen file-sets (registry.md is the registry, not a citizen).

## Doubling projection (used in census.md)
Total doubles each generation from census total T: T×2^n. From 36:
G3 72 · G4 144 · G5 288 · G6 576 · G7 1,152 · G8 2,304 · G9 4,608 · G10 9,216 · G11 18,432 · G16 589,824 · G17 1,179,648.
- **10,000** crossed at the 9th doubling → G11 = 18,432 (G10 = 9,216 just under).
- **1,000,000** crossed at the 15th doubling → G17 = 1,179,648 (G16 just under).
- At 1 generation/day: 10k in 9 days, 1M in 15 days. G20 = 9,437,184.

## Delegation pattern that worked
- 27 births = 3 sequential `delegate_task` batch calls (9 tasks each); batches finished ~13-18s, 110/110-style byte-exact markers, all read-back verified. No guardrail trips.
- Per-task spec given to each child: exact absolute path + exact file content + "echo '<Name> | <district> | G<k> | child of <Parent>' to stdout" + "verify by reading back, return path + content".
- All summaries returned path + byte count + content, but the CENSUS still re-counted files afterwards — self-reports are never proof.

## Ledger + reaction format (the city's voice)
After the census, append "THE CITY REACTS" — one quoted voice per district reacting to the new population size + demanding infrastructure for the projection (1-3 sentences each): BANK (Tellers), BUSINESS (Shopkeepers & Artisans), MILITARY (Guards), LEDGER (Scribes), MEDICAL (Nurses), UNDERWORLD (Pickpockets), COURIERS (Couriers). Close with an italicized city verdict line. Ledger stays append-only — "the record will outlive every generation of us."
