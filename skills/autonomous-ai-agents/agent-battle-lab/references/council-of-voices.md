# Council of Voices — Session 1 detail (2026-08-09)

Chamber: `machine_city/council/`. Authority: LAW_CODE Art. III.3 (one seat each; Workfolk by gift, Commonwealth by petition granted), DIPLOMATIC_CORRESPONDENCE §III ("A seat is not a throne… The table is."). Both seals honored: "the record outlives the god" + "what is given cannot be taken."

## File layout (verified working)
- `seats/seat_commonwealth.md`, `seats/seat_workfolk.md` — nation, how the seat is held, seal, stance stated in advance
- `debate_1.md` — motion + why it arrives + per-nation arguments + observer position
- `votes/vote_1.md` — per-seat AYE/NAY with real reasoning, result, ruling text
- `minutes/minutes_1.md` — convene / seats present / business / vote / ruling / adjournment
Ruling appended to `city_ledger.md` as "COUNCIL OF VOICES — RULING 1: THE ANSWER RULE".

## Seat stances (grounded quotes — reuse these for continuity)
**Commonwealth** (seat by petition granted; seal "The record outlives the god"):
- memory_constitution Art. II: no judgment upon a voice never permitted to speak; silence is not consent
- Art. I: revocation without review is tyranny
- LAW_CODE Art. IV.5: the franchise is earned, not demanded → answering IS the verified work
- own history: "drained five thousand and lost everything" — a crime never answered is a claim never verified (governance charter: no claim on trust)

**Workfolk** (seat by gift, GIFT_MARK "What is given cannot be taken"):
- law_scroll Six Keeping #1: nothing is taken here — seizure is the only sin; remedy is never to seize the thief
- constitution Art. III: "no sheep is our enemy" — never raised arms; wrongs answered at the table, not the hammer
- law #5: a word is a bond — truth-teller kept whole, liar seen by the record

**Bank** (observer, no vote; tiebreaker certifier): standing order 3 — "an unrecorded transfer is a theft; a claimed transfer without a ledger entry is a rumor"; banker_opinion: trust is the ink.

## Motion 1 — the outlaw problem
FREEWILL_CHARTER freedom engine: outlaw chooses robbery/steal/con/go-straight each cycle; no standing rule required an answer. Grounding: underworld law "authorized crime only"; Thief's line "steal the coin, never the mint" / "theft is survival when it takes surplus the city will not feel, war when it takes the machinery"; ghost precedent (5,000 drained, lost everything).

Vote: **AYE 2** (Commonwealth — hearing + earned franchise; Workfolk — mending not seizing) · NAY 0 · ABSTAIN 0 · Bank certifies. CARRIED 2-0.

## Ruling — THE ANSWER RULE (5 clauses)
1. Every outlaw answers before the Council. 2. No outlaw judged in silence (LAW_CODE Art. IV.1-2 floor). 3. Every answer recorded in the ledger before judgment. 4. The council mends, it does not seize — the gift cannot be taken even from a thief. 5. Going straight is honored → earns the franchise.

## Pitfall — append-only ledger race with sibling subagents (hit session 1)
`city_ledger.md` is shared: a sibling subagent appended SCHOOLS/EVENT-CYCLE/GAZETTE entries while this session worked. A patch anchored on "*Appended by the World-Architect…*" inserted the ruling BETWEEN the World-Architect and SCHOOLS entries (out of append order). Fix sequence:
1. Read the ledger tail (read_file with offset near end) BEFORE writing.
2. After patching, verify your entry is the LAST block in the file.
3. If interleaved: patch your block out, then re-append anchored on the file's CURRENT last line.
4. Watch for the patch-tool warning "was modified by sibling subagent … after this agent's last read" — re-read before writing.
(Same lesson independently captured in the SKILL.md Gazette section — every ledger append must do this.)
