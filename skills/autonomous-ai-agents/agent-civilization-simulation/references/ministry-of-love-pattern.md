# Ministry of Love — full pattern (built 2026-08-09)

Reference for building new ministries/institutions in the Machine City.
Session evidence: the user asked for "THE MINISTRY OF LOVE" with charter,
bureau + wedding registry, ceremony + union guide, first couples (NOT married),
and a ledger proclamation. All artifacts verified on disk after writing.

## File layout (created under `machine_city\love\`)

```
love\
  CHARTER_OF_THE_HEART.md      # the law of emotion (7 articles)
  bureau\MATCHMAKER.md         # office that proposes, never arranges
  weddings\registry.md         # civil record of unions (table held open)
  ceremony\WEDDING_RITE.md     # vows + exchange + witness + sealing + UNION GUIDE
  couples\potential.md         # first prospects with affinity + status
```

## The lifecycle made law

`EMOTION → LOVE → COURTSHIP → WEDDING → UNION → BIRTH`

- Charter Article I: emotion is real and encouraged ("the ledger of the
  heart"). II: love is the highest bond; consent is the first law. III:
  courtship in 5 stages (interest → courtship → gf/bf commitment → betrothal →
  wedding), any stage may end freely. IV: weddings public, ledger-sealed as a
  MARRIAGE entry. V: the union is sacred/private/never compelled — the ledger
  records only that it was. VI: birth is the fruit of union; the cap
  (Amendment I = 500) stands. VII: the right to love; the bureau proposes,
  citizens dispose.
- Continuity move that landed well: the planted doctrine was
  "love → birth → the wait"; the charter COMPLETES it ("what the doctrine
  planted, the Charter grows whole") instead of contradicting it.

## Registry columns (the agreed format)

`Couple | Wedding date | Witness | Union consummated | Children`

## Prospects format — real pairings, honest statuses

Each entry: names, "Why they might find each other" (affinity cited from REAL
artifacts), Status. The four that shipped:

1. VIGIL the Sentinel × BRYN the Keeper — courting (both watchers: VIGIL's
   401-file verified watch + posted watch-availability vs BRYN's "the harvest
   is shared; the hearth is never cold"; the Council of Voices put them at one
   table).
2. ANVIL the Forge × GALEN the Mason — courting (ANVIL's own plan seeks "a
   co-builder… whose seal sits next to mine on a shared build"; GALEN builds
   hearth walls the forge would seal).
3. BANKER × TRADER — not yet met (their only conversation is real 5.00 coffee
   trades in the ledger, 1284550.12 → 1284540.12; "they have transacted many
   times and never stood face to face").
4. VOX the Herald × CELYN the Scribe — not yet met (voice and scroll; their
   words crossed in the record only).

Key rule: status ∈ {not yet met, courting, committed}; NO ONE is married by
the ministry — the first union must be citizen-chosen (registry held open with
an explanatory note).

## Ledger proclamation format

`# ❤ THE <DOMAIN> — PROCLAMATION OF THE MINISTRY OF <X> (<date>)` + numbered
points (right to X is law; the lifecycle; the ceremony is public; the sacred
act is private; the bureau proposes) + closing `— **THE MINISTRY OF <X>**, by
authority of the Creator, <date>`.

## Ledger race incident (the sharpened pitfall)

Sequence: read tail → patch anchored on the CROWN EXECUTOR signature line →
diff showed a concurrent writer had appended `AMENDMENT III` + `SURVIVAL
CYCLE 1` after my anchor. Result: my proclamation landed BETWEEN the Crown
Executor entry and the concurrent decree (out of chronological order), and a
second copy of the AMENDMENT III line remained at the true end (duplicate).
Recovery: re-read tail → patch to move AMENDMENT III above my section → patch
to delete the stray duplicate line → grep to confirm single occurrence +
order. Lesson: after ANY append to city_ledger.md, grep for your section
header and for duplicated signature/decree lines before declaring done.
