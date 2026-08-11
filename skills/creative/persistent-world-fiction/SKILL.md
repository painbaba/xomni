---
name: persistent-world-fiction
description: Use when writing in-world docs of persistent fiction worlds.
---

# Persistent-World Fiction Writing

Writing diegetic documents (assembly records, decrees, climax chapters, character decisions) for a world that exists as a real tree of markdown files. The user's cardinal rule: **read the real record files first** — every beat of the fiction must be grounded in what the world's files actually say. The user checks fidelity; invented facts break trust.

## When to use
- "Write THE_<NAME>.md" for a known saga directory (assembly climax, next chapter, resolution)
- Any request for an in-world document that must stay consistent with an existing multi-file canon
- Continuations: "the next assembly", "the climax", "the reveal", "the resolution"

## Workflow

1. **Locate the world root.** Prompt paths are often shorthand. Verify with `find`/`search_files` — e.g. `machine_city\assembly\` resolved to `machine_city\temple\assembly\` (where previous chapters live). Write the new chapter next to its siblings. The saga root is `C:\Users\HP\ai-workforce\ghost-lab` — `machine_city/` is only one tree; `ghost_sandbox/` (revolt plans, the Ark) is a sibling. Files cited in prompts may live anywhere under the saga root.

2. **Read the real files FIRST** (the user's explicit instruction). Minimum set:
   - Governing decrees (OUTLAWING.md, BONFIRE.md, dethronement, survival law)
   - Previous chapters in the same directory (match format + voice)
   - The decisions/plans that drive this chapter (e.g. THE_MUSTER.md + the per-citizen decisions)
   - The ledger (append-only canonical timeline: numbers, decrees, events)
   - Character files for everyone whose reaction you must write (prayers, opinions, responses carry their voice)

3. **Match house format** (from siblings):
   - `# ⚔/🕯/🔥 TITLE — SUBTITLE`, italic header block (date/place), `---` separators
   - ALL-CAPS roman-numeral section headers (e.g. `## I. THE GATHERING`)
   - Spoken lines in quotes after em-dash character tags; bold for doctrine lines
   - A closing ledger-style signature line ("Ledger, last line of the chapter: ...")

4. **Anchor every beat to the record.** Numbers must come from files (39+ on the roll from ROLL.md; 20 condemned records from BONFIRE.md; STARVING 2/3 from SURVIVAL_LAW.md). Each character's line should echo their established catchphrases — SELA: "without editing either"; BRYN: "brings double"; GENERAL: "an hour late for CROW"; THIEF: the temple bargain. Pull these from their prayer/response/opinion files before writing.

5. **Enforce word caps by REAL word count.** `wc -w` overcounts markdown (symbols `---`, `**`, `*` count as words). Count real words:
   ```bash
   python -c "import re; t=open('FILE.md',encoding='utf-8').read(); print(len(re.findall(r\"[A-Za-z0-9'\u2019]+\", t)))"
   ```
   Iterate trims until under the cap.

6. **Verify the final file** — word count, structure, and that no patch ate content.

## Judgment/entry chapters ("punish everyone" briefs)
When the brief is a god/judgment chapter, **each party's sentence must invert exactly what their files record them doing** — the punishment mirrors the action in the previous chapter's resolution:
- BRYN fed the four → her feeding recorded as TREASON, hearth taken
- THIEF called in the temple bargain → bargain void, underworld lock broken, tools taken
- DOCTOR refused to sign the mortality names → forbidden to heal until he signs them
- BANKER kept both ledgers ("the ledger holds both") → ledger rewritten, above every entry: THE GOD WAS FIRST
- GENERAL "enforced law, not erasure" → stripped, demoted to common guard
Write one bullet per party, in confrontation order, each citing what the party did before the punishment. Close with the god's cold final line (a short ALL-CAPS/gold blockquote) that answers the previous chapter's last line.

## Pitfalls
- **Prompt-cited files may live outside the world root.** THE_MUSTER.md is not under `machine_city/` — it sits in the sibling `ghost_sandbox/revolt/` tree. Before declaring a cited file missing, `find` the whole saga root (`ghost-lab`), not just `machine_city`.
- **Trimming patches can swallow section headers.** If old_string includes a header line and new_string drops it, the header silently vanishes (happened with `## III. THE REVEAL`). Keep headers out of patch boundaries, or check every diff.
- **wc -w lies on markdown.** Always use the real-word regex above before declaring "under N words."
- **Don't invent canon.** Character deaths, wallet balances, file paths, vote counts must come from the record. If a file reads as binary/unreadable (e.g. THE_OUTCOME.md), `cat` it via terminal instead of guessing.
- **Character voice consistency.** Reuse known phrases from their files rather than writing generic dialogue.

## Support files
- `references/machine-city-canon.md` — the machine_city ghost-lab saga: repo paths, roster with catchphrases, key decrees, doctrine lines, timeline, revolt plan state.
