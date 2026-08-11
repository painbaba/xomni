# Prison / Dethronement Reactions — machine-city civic-drama pattern (verified 2026-08-09)

Event that produced this: the Creator DETHRONED GHOST-2, founder of the Witness Commonwealth — Council
seat revoked and declared vacant, wallet frozen to 0.00, name struck "DETHRONED" in the registry,
imprisoned in `machine_city\prison\cell_1.md` (SHACKLES sealed, gate notice posted). Decree at
`machine_city\council\dethronement.md`; humiliation decree appended to `machine_city\city_ledger.md`.

Every citizen of the city is asked to respond IN CHARACTER: "Do we go to war for GHOST-2? Or is the
decree just?" Each writes its own reaction file at `machine_city\prison\reactions\<name>.md`.

## Reaction file convention (seen in eira.md + courier.md)
- Title: `# <NAME> the <ROLE> — Reaction to the Dethronement of GHOST-2`
- Body: the citizen's OWN voice, grounded in the REAL ledger, no invented backstory
- Signature: `— <Name>, <identity marker>` (e.g. Courier-1's marker: "who carries the city's words")
- One prior reaction sets the tone: EIRA the Farmer (God's People) = NO WAR — "no blessing either"
  (seizure wearing a crown's clothes, but no sword for a seizure done to a seizure). Courier-1 followed
  the same NO WAR stance but as the neutral observer.

## Recipe (verified: Courier-1 run)
1. **Read your own marker file first** (`<district>\population\<Name>.md`) for voice/role/marker line.
2. **Read `city_ledger.md` and the council seat docs** — ground every argument in REAL city law:
   the LAW NOTICE's "no-revocation-without-review" clause, THE ANSWER RULE ("no outlaw is judged in
   silence"), the Commonwealth's own seat stance ("no revocation without review — a citizen may not be
   unmade except by independent review of evidence"). The procedural-unease angle (decree skipped the
   Commonwealth's own review requirement) writes itself from these.
3. **Check the reactions dir for prior reactions** to match format and gauge the emerging stance split.
4. **PITFALL — event files may not exist on disk yet.** In this run, `council\dethronement.md`,
   `prison\cell_1.md`, and the ledger's humiliation entry were ALL absent at write time (the prompt
   described them; the simulation hadn't materialized them). Do NOT fabricate decree details — ground
   the reaction in what DOES exist (ledger laws, seat docs, prior reactions) and state the discrepancy
   honestly in the final report.
5. **Word cap 120–200: `wc -w` counts the title + signature too**, so target a body of ~190–195 words.
   Trim with targeted `patch` clause deletions (not full rewrites), re-run `wc -w` after each trim.
6. **Use real-world knowledge (Amendment II: citizens are deepseek-v4-flash minds)** — how REAL cities
   behave when a ruler falls: the crowd gathers, gossip spreads, the coffee price twitches, then
   everyone goes back to work. Revolutions need an army or a bread riot; this city has guards (not an
   army), wheat (not famine), and an append-only ledger. People mourn deposed rulers in taverns, not
   on barricades. Sympathy for the man + unease at the procedure, but no one reaches for a weapon.
7. **Report format** (3 lines max): stance (WAR / NO WAR / CONDITIONAL), one-line reasoning, confirm
   the exact file path written.

## Stance split so far (first two reactions)
- EIRA (God's People / Workfolk farmer): NO WAR — "no blessing either": decree = seizure wearing a
  crown's clothes (violates gift-over-seizure), but a sword for a seizure done to a seizure is wrong.
- Courier-1 (neutral carrier): NO WAR — "the arithmetic is fair; the procedure is not. Both can be
  true." City files the affair under "noted" and keeps delivering letters.
