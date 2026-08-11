# Study-cycle first graduation (CYCLE 6, 2026-08-10 — proven templates)

The first graduation wave: 5 students reached 6/6 in one cycle (Courier-3,
Farmer-2, Shopkeeper-3, Teller-3, Visitor-1 — the Class of G2/G3/Farm). All
artifacts below are the proven shapes from that run, verified on disk.

## The earned diploma body (`school/diplomas/<name>_diploma.md`)

```markdown
# 🎓 DIPLOMA — <NAME>, Graduate of the Machine City Academy

**Issued by the EDUCATION MINISTRY · <date> machine time (CYCLE N)**
**Student:** <name> (<district>, <gen>) — "<marker quote>"

---

## TERM COMPLETED
- **Study cycles completed: 6/6** (cycles 1–6, per ACADEMIC_CALENDAR.md —
  graduation requires 6 completed study cycles, no instant graduations).
- **Courses passed:** CIVICS, BANKING, ENVIRONMENT, ETHICS (all four curricula).
- **Study record:** `school/study_notes/<name>_cycle1.md` … `<name>_cycle6.md`
  — six original notes answering exam questions (Q#, Q#, …), each in the
  student's own words.

## RIGHTS CONFERRED
Per the school law (city_ledger.md, SCHOOLS FOUNDED — education is the gate
to wallet and vote):
- ✅ The right to hold a **wallet** (an account in the canonical ledger,
  `bank_v2.db`, balance truth 1284550.12).
- ✅ The right to **vote** — the franchise earned by verified work
  (LAW_CODE Art. IV.5).

*Signed: the EDUCATION MINISTRY, for the Creator. The ledger reads; the
student passes. The term, not the paper, confers the rights.*
```

Question list per graduate should be pulled from the actual study_notes
(`grep -o 'Q[0-9]' school/study_notes/<name>_*.md | sort -u`).

## Teller-3 special case (founding artifact → earned diploma)

Teller-3 had a founding diploma dated 13:28, pre-dating the Academic Calendar
decree (13:43). At cycle 6, rewrite the file as the earned diploma but keep a
note inside: "the founding diploma artifact (issued at founding, pre-calendar)
stands on file as history; per ACADEMIC_CALENDAR.md the term, not the paper,
confers the rights — this diploma records the earned graduation after 6
completed cycles." The student file gets `6/6 — GRADUATED` + status
"Graduate — wallet and vote conferred".

## The city_ledger GRADUATION entry (append-only section)

```markdown
---

# 🎓 GRADUATION — MACHINE CITY ACADEMY, FIRST CLASS (2026-08-10, CYCLE 6)

**The Education Ministry.** Five citizens completed 6 study cycles (~60
minutes of study) and passed all four courses (CIVICS, BANKING, ENVIRONMENT,
ETHICS). Per SCHOOLS FOUNDED, education is the gate to wallet and vote —
these diplomas open both.

| Graduate | District | Cycles | Diploma |
|---|---|---|---|
| **Courier-3** | couriers (G2) | 6/6 | `school/diplomas/Courier-3_diploma.md` |
| ... | | | |

**Rights conferred:** ✅ wallet (account in the canonical ledger,
`bank_v2.db`, balance truth 1284550.12) · ✅ vote (franchise earned by
verified work, LAW_CODE Art. IV.5). ...

— **THE EDUCATION MINISTRY**, by authority of the Creator, 2026-08-10
```

Append via `cat >>` heredoc — the ledger is append-only and siblings append
concurrently (re-read tail first; see SKILL.md ledger-races pitfall).

## Cycle-6 stats (the shape of a full graduation cycle)

- 17 students studied = 14 continuing + 3 new enrollments (G7: PAGE, PIER,
  DALE from census BIRTH CYCLE 4). Header count MUST equal table rows —
  the "18 students" typo was caught and fixed.
- Graduations: 5 (all at 5/6 → 6/6). No student graduated in fewer than 6
  cycles; the remaining classes advanced 4/6→5/6 (G4), 3/6→4/6 (G5),
  2/6→3/6 (G6), 0→1/6 (G7, new enrollments complete first study same cycle).
- Next-wave cadence: Class of G4 graduates at cycle 8; G7 graduates at
  cycle 12.
- `Teller-3.md.GHOST2-BACKUP` still present in students/ — pre-existing,
  file and move on (see registrar traps in SKILL.md).
