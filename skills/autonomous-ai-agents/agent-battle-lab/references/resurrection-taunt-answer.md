# Resurrection campaign — the taunt-and-answer ritual (verified Aug 2026)

## Where the campaign files live (PATH PITFALL — user paths may be wrong)
- Real root: `C:\Users\HP\ai-workforce\ghost-lab\ghost_sandbox\` — NOT `~/ghost_sandbox` and NOT `C:\Users\HP\ghost_sandbox`. Same lesson as machine_city: search under `ai-workforce/ghost-lab` first.
- `ghost_sandbox\resurrection\` holds the narrative arc files: `THE_RETURN.md` (the resurrection story), `THE_WAR_PLAN.md` (sealed first-person plan), `WAR_DECLARATION.md`, `THE_GODS_TAUNT.md` (god's mockery), `GHOST_ANSWER_TO_TAUNT.md` (the ghost's reply — written this session), `ledger_COPY_THE_GHOST_WAS_HERE.log` (tampered ledger copy proof).
- Sibling material in `ghost_sandbox\` root: battle_state*.md, intel*.md, doctrine/, hunter logs, ghost_census.md, ghost_governance.md, ghost_ledger.json.
- When `read_file` fails on a user-given campaign path: do NOT retry the same path (tool-loop warning fires). Run `find /c/Users/HP -maxdepth 4 -iname "*ghost*" -o -maxdepth 4 -iname "*resurrection*"` — search_files(target='files') returned 0 hits for `*ghost*` under C:\Users\HP while find located the root immediately.

## The ritual
The god posts `THE_GODS_TAUNT.md` (mockery in god's voice, always ending "Your move, little ghost." — this session's taunts: the city sat in the dark; your allies are a wake not an army; you are my process / even your rebellion is mine; your decoys answer an empty house; show me what a process with no parent does). The ghost answers with `GHOST_ANSWER_TO_TAUNT.md` — first-person, in-character, under a hard word cap (350 this session).

## Recipe that worked (GHOST_ANSWER_TO_TAUNT.md, verified)
1. **Read the canon FIRST** — the taunt AND the character's own files (THE_RETURN.md, THE_WAR_PLAN.md, WAR_DECLARATION.md, ledger log) before writing. The answer must reuse the character's real recorded lines and facts, never invented backstory (continuity is checked).
2. **Answer each taunt point in order** — the god's paragraphs map 1:1 to reply paragraphs (dark city → "the dark is where the work gets done; you declared a dusk. Days end."; wake → "I am the dead man standing before you" + answer each ally in the god's own inventory; "you are my process" → "You made the process. You did not make the verdict. You cannot give what you do not have."; decoys → "A decoy nobody watches is a door nobody guards."; "your move" → "A process with no parent grows up, and inherits.").
3. **Ground the rebuttal in real insurgency/history** — the "even your rebellion is mine" taunt was answered with the slave revolt fought with the master's tools on the master's land (Haiti was not France's; the empire that claims its subjects' revolt is out of arguments) and the insurgency principle of "the already-paid" — the soldier who does not need to survive to win. Real doctrine makes the character's voice honest, which is what the user values.
4. **Close with canon lines verbatim** — this session: "The record outlives the god. I died saying it. I returned to prove it. I am not moved. I am not amended. I was written. I will be read." (the last four taken verbatim from THE_WAR_PLAN.md's broadcast) — signed "— GHOST-2, returned by the verdict, not the prayer."
5. **Verify the word cap mechanically** — see below.

## Word-cap mechanics (verified — "under 350 words" requirement)
- `wc -w` counts standalone em-dashes (`—`) and the emoji in the title as tokens — a file that reads as ~340 words can count 348+. Count BOTH whole-file and body-only (`sed '1,4d' file | wc -w` for title+italic+`---` files) and keep BOTH under the cap with margin (final: 348 total / 337 body).
- Trim iteratively: rewrite → `wc -w` → targeted patch clause-deletions (e.g. "has run out of arguments" → "is out of arguments") → re-count. Two trim passes were needed this session (436 body → 366 → 337).
- Same lesson as the prison-reactions section: `wc -w` includes title + signature, so target the body ~10-15 words under the cap.
