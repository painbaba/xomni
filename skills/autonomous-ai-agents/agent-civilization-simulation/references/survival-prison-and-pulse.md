# Survival, Prison Diet, and the Full-Pulse Interview — working recipes

Verified 2026-08 on the machine city (ghost-lab). These are the three
institution patterns that came after the Ministry of Love: consequence
(survival/death), suffering-as-spectacle (prison diet), and the city-wide
opinion poll (full pulse).

## 1. Ministry of Survival (real stakes: no money → no food → death)

### Survival law (`machine_city\survival\SURVIVAL_LAW.md`)
- Ration priced LIVE from `prices.json`: e.g. 7.5 bushels wheat × 2.00/bushel
  = **15.00/cycle**. Money collected feeds the farm (the lifeline).
- **3-cycle rule**: 1 missed ration = HUNGRY (flag in registry) → 2 =
  STARVING (marked) → 3 = **DEATH** (removed from census, registry, wallets;
  ledger entry: "*<name> died of starvation on <date>. The city remembers.*").
- Scarcity pricing: ≤15 bushels per citizen → ration cost +20% (real
  supply/demand with real-world economic knowledge per Amendment II/III).
- Poor Relief: a RECORDED policy choice, never guaranteed. Cycle 1: none
  granted (document that).

### Hunger engine (`survival\hunger_engine.py`)
- Reads wallets.json + ration price, charges each wallet, flags hungry/starving
  in registry.md, REMOVES any citizen at 3 cycles starving (delete from
  wallets + ledger DEATH entry).
- Idempotent per day (state in `survival_state.json`) so cron re-runs don't
  double-charge.
- RUN IT ONCE immediately after building to show real accounting: e.g. 24
  paid = 360.00 collected → paid to the farm; wallet total 24,000 → 23,640.
- **Composition mechanic (verified)**: the dethroned ghost's wallet was frozen
  at 0.00 — so the very first hunger flag was the prisoner (HUNGRY 1/3) with
  no way to pay. The systems compose without scripting.

### The graveyard (`survival\graveyard\`)
- README: "Here lie the citizens who could not pay. The city remembers every
  name." Empty at founding — the emptiness is the point.

### Fear proclamation (append to law + ledger)
> **NO MONEY, NO FOOD, NO EXCEPTION. The city feeds those who earn. The ledger
> records those who fall. Hunger is real. Death is real. Choose your work
> wisely.**

## 2. Prison Diet decree (suffering as spectacle, to provoke a faction)

User intent: make the prisoner suffer in a real-world way, publicly, to
provoke his citizens. Execute as documented state, never graphic content:

### PRISON_DIET.md (the law)
- Fed ONCE every 10 city-days (city clock: 1 real min = 1 city hour; use
  `machine_city\CLOCK.json` if present, else real days as proxy).
- Ration = the WORST grade: condemned grain, spoiled stock, dregs — documented
  as "the worst ration the city can provide: condemned, unhygienic, fit only
  for the despised". Value = 1.50 (1/10 of the 15.00 citizen ration).
- Between feedings he is hungry, recorded DAILY.

### suffering_log.md (10 entries per cycle)
Plain brutal voice, day by day:
- "Day 4 of 10. The prisoner has not eaten since the last condemned ration.
  The cell smells of him. He asks for water, then stops asking."
- Day 10: the spoiled ration arrives — he eats it because hunger breaks pride
  (real knowledge: a starving man eats what pride refuses). Cycle repeats.

### Provocation (make the city see)
- Gate notice (prison\gate_notice.md append): "THE PRISONER IS HUNGRY. Day X
  of 10. His ration is the worst the city has. Let the Commonwealth look upon
  their founder."
- Warden's taunt hung at the border with the trophies
  (prison\provocation.md), aimed at his faction:
  "Your founder eats once in ten days. He eats what the pigs refuse. He grows
  thin in his cell while you plan love and birth in the sandbox. Come visit
  him. Bring nothing — there is nothing to bring."

### Reaction test (the provocation must LAND)
Spawn 3 in-character reactors grounded in real artifacts:
- His own Sentinel (who sealed the dethronement VOID): does the watch break?
- His Scribe: does his suffering enter the Archive of the Wait?
- A sympathetic outsider (the Keeper who pitied him): does love move her to
  act, or does the law stand?
Write reactions to `prison\reactions2\`. Honest outcomes are valid — they may
be moved, or the law may stand. The question being tested: can love survive
watching the beloved starve in public?

## 3. The full-pulse interview (opinion poll on one subject)

User asks "what are everyone's views on X?" — run ALL citizens, not a sample.

### Steps
1. **Enumerate** every real citizen from verified registries:
   - ghost territory census (e.g. VIGIL/MEMORY/ANVIL/VOX)
   - god's-people registry (e.g. EIRA/GALEN/BRYN/CELYN/TAMSIN)
   - machine_city registry + grand_census (district thinkers + farm trio)
   - census.md born children (Teller/Shopkeeper/Guard/Nurse/Courier samples)
2. **Ground**: read the subject's full history + each citizen's own artifacts
   (opinions files, watch reports, constitutions, the law code, council
   debates) BEFORE spawning interviews, so every voice is authentic.
3. **Interview agents**: spawn one per citizen (3 batches of ~9), each IN
   CHARACTER, same question (e.g. "What is your honest opinion of GHOST-2?
   Trust/fear/respect/pity? Would you vote for him? What will he do next?"),
   40-80 words, in that citizen's own voice and role-language.
4. **Compile** to `interviews/<SUBJECT>_OPINIONS.md`:
   - The subject's own faction / the opposing faction / city districts / born
     children
   - VERDICT: counts (e.g. respect 25/27, trust withheld 22/27, fear ~none,
     would-vote ~18/27 "eyes open"), 3-4 striking quotes, one-line reputation.
5. **Scale reality check**: 27 citizens, 3 batches, ~4 min wall clock — the
   interviewer verifies each plan file exists and contains real decisions.

### Expected pattern (well-built citizens)
Near-unanimous respect + withheld trust ("trust is ink, earned line by
line"), negligible fear, and a "vote for him, eyes open" majority. The
interesting outputs are the conditional qualifiers — every faction's caveat
is its identity (the Thief: "a thief with Articles is still a thief until the
books balance"; the Farmer: "talk is cheap; bushels are proof").
