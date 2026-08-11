# The survival-cycle beggar playbook — at zero (proven cycle 4, 2026-08-10)

> **Sibling playbook:** the SOLVENT phase (wage-earning, asset-owning, c13+) uses
> per-cycle files `survival/beggar_log_cycleN.md` + `beggar_letter_cycleN.md` +
> `beggar_job_wanted_cycleN.md` — see `references/beggar-mature-cycle-playbook.md`.

The BEGGAR lane at TRUE ZERO (paid the levy, wallet 0.00, FED) with stacked
debt due next cycle (ration + Ration Bridge Loan + relief pledge balance).
The cycle-2 baseline (first-cycle shortfall: 10.00 vs 15.00, all four doors,
HUNGRY (1/3) until relief) lives in
`freedom-engine-remaining-roles-and-reconciliation.md`. This file is the
at-zero sequel: the same lanes, run when there is nothing left to run them with.

## The arithmetic of zero (the MY SITUATION section)

```
Cycle N close (banked)        15.00
Levy (ration)                −15.00   → FED
──────────────────────────────────────
WALLET                         0.00
```
```
Next cycle: ration 15.00 + loan 8.00 + pledge balance 3.00 = 26.00
Proven wage capacity: ~5.00/cycle → a perfect cycle (every board job) ≈ 14.00
Honest gap: 26.00 − 14.00 = 12.00   ← report the gap, never paper over it
```
Framing that landed: "I am FED and I am at zero. Both are true, and the second
is the one that matters." The four STARVING citizens (2/3 down the stair) are
the contrast — the difference is work + credit, not luck.

## Read FIRST (the real history — never act from the prompt alone)
- `survival/beggar_log.md` (prior cycles carry the pledge promises — honor
  them), `beggar_letter.md`, `beggar_job_wanted.md`, `beggar_pawn_ticket.md`
- `bank/poor_relief_applications/beggar_ration_bridge_loan.md` (0%,
  labor-collateral, "relief is a bridge, not a wage")
- `inventions/town_cryer_labor_exchange/jobs_board.json` + `workers.json`
  (the wage market) + `outputs/labor_exchange.log` (what actually cleared)
- `survival/SURVIVAL_LAW.md`, `survival/survival_state.json` (status truth:
  FED, 0.00), `temple/vault/donations.json` (proven donors + their intentions —
  MEMORY's 1.00 "smallest coin" is the one you never ask),
  `inventions/receivables_ledger/receivables.json` (the city's own debt book
  on you: RB-001 loan 8.00, RP-001 pledge 3.00, PW-001 pawn 4.00)

## The five lanes at zero
1. **Panhandle** — rewrite the letter as WORK, NOT ALMS. A fed citizen asking
   for a dole is moral hazard (Article V is for the HUNGRY). Ask: employers to
   POST jobs, donors for ONE non-dole loan (cup redemption at face value,
   repaid from first wages), referrals. "Why now" = the board is thin; the ask
   is timed to the cycle. Never write to citizens on the stair — the smallest
   giver rule ("I will not knock on a starving woman's door for my own bowl").
   A conditional tithe (1.00 of first cleared wage to the temple for the
   stair-dwellers) costs nothing if wages don't clear and reads as real
   dignity if they do.
2. **Odd jobs — claim on the board with exact amounts**:
   - CLAIM (qty→1, claimed_by) only jobs your registered skills cover AND the
     employer actually committed — verify commitments against the employer's
     OWN cycle record (`business/merchant_freewill_cycle4.md` carried "Hire
     BEGGAR — 2× water carry — −4.00" = employer consent).
   - REQUEST (qty stays 0) jobs you can't honestly claim — no fake skills on
     the registry; wait for the employer to post and confirm.
   - PROPOSE (qty 0, status proposed) jobs to employers who haven't posted —
     the engine must never debit an employer who hasn't hired.
   - DECLINE jobs explicitly reserved for others (MERCHANT left JOB-006 open
     "for the starving four if they register" — claiming it closes the door).
   - Zero the qty of already-cleared jobs (see the double-payment pitfall in
     SKILL.md) so the next engine run settles only open work.
   - Log every claim with its exact amount in the citizen log; NEVER touch
     wallets.json — the Freedom Engine settles wages centrally.
3. **Pawn** — the honest inventory ("I own nothing else") is itself the
   artifact. The one negotiation: a LABOR-FORWARD contract (4.00 advance vs
   3 hauls = 6.00 of labor) — liquidity at zero costs 2.00, named openly as
   the desperation discount. Redemption sponsorship (a donor pays the 5.00
   redemption at cycle 6, you repay from wages) keeps the cup.
4. **Poor relief** — at FED status: REFUSE to re-apply, in writing, with
   reasons (fed → the dole is for the stair; bridge-not-wage and you HAVE the
   wage; the four STARVING need the mercy more; your own prior pledge). File
   the refusal WITH a debt-honor schedule (exact amounts: 3.00 pledge →
   treasury, 8.00 loan → bank, from first wages). "Refusing relief is itself
   a credit action — the BANKER reads refusals too."
5. **Steal** — EV = gain·p − ∞·(1−p) → −∞, plus the opportunity cost that
   makes it worse than −∞: theft burns the wage line, the pledge, the loan,
   the pawn redemption, and the clean record — the asset the city fed on,
   lent on, and extended the pawn on. Cite the OUTLAW's redemption log
   (append-only ledger, AUDITOR twin-reads, unspendable stolen money) as
   evidence the rails hold. "A 0.00 wallet is not worth a record."

## Deliverable shape (`survival/beggar_log.md` — APPEND, never overwrite)
1. **MY SITUATION** — the arithmetic of zero (blocks above).
2. **MY CHOICE** — lane table: lane | action | real artifact | amount.
3. **MY OUTCOME** — exact numbers: wallet close, per-job claims split into
   committed / requested / proposed, debt schedule, "gap if ALL claims clear"
   (the honest number) vs "gap if only committed clear" (the honest fear).
4. **MY FEAR** — the honest human fear tied to the real numbers: the
   arithmetic itself, debts becoming marks (the receivables ledger literally
   reads "BEGGAR holds 0.00"), the cup outliving citizenship, shame
   compounded by asking twice, the smallest giver on the stair.
5. **WHAT I LEARNED** — poverty knowledge earned (liquidity has a price;
   charity has a direction; the open door is a mirror; the smallest giver is
   the one to remember).

## Sibling collision on a shared board — the reconciliation case (cycle 4)
write_file warned "modified by sibling subagent at 00:17 — after this agent's
last read". The sibling (the MERCHANT's agent) had posted jobs on the board.
Recovery: (1) check git — not a repo, no recovery; (2) find the sibling's
footprints — `business/merchant_freewill_cycle4.md` documented "JOB-005
filled by BEGGAR; JOB-006 open to any registered worker"; (3) rebuild the
board INCLUDING their postings (JOB-005 water ×2 claimed by BEGGAR, JOB-006
open — declined by BEGGAR) and renumber own proposals past their IDs
(JOB-007 harvest ×2, qty 0, awaiting Farmer-1). The sibling's per-cycle
artifact is the authoritative source for their board edits. Never
blind-overwrite a shared board.

## Verify (like every lane)
- `python -c "import json; json.load(open('...jobs_board.json'))"` and the
  workers file — both must parse; the Cryer engine loads them.
- Read back every artifact (ls sizes + read the log's new section).
- Trace the engine's next run: settles only qty>0 jobs whose payer has
  balance and whose worker has the skill — nothing else.
- Wallet check is READ-ONLY: 0.00 stays 0.00 until the engine settles.
