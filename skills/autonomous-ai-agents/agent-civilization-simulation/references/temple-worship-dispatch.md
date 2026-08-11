# Temple Worship Dispatch — session detail (2026-08-09, THE CALL)

Task: "Open the TEMPLE OF THE CREATOR for worship: THE_CALL.md announcement,
spawn 3 real worshippers IN CHARACTER (BRYN donating 10.00, the DOCTOR praying
about the city's health and the starving prisoner + 5.00, MEMORY praying about
her imprisoned founder + 1.00 with her reason), record donations in
treasury.json (16.00) and OFFERING_LEDGER.md, write ALTAR.md. Report under
250 words."

## Territory path
`C:\Users\HP\ai-workforce\ghost-lab\machine_city\` — temple at
`machine_city\temple\`. Do NOT assume C:\Users\HP\machine_city; search for the
territory root if the path 404s.

## State read BEFORE writing any prayer (grounding set — read these first)
- `temple\TEMPLE_CHARTER.md`, `temple\shrine.md`, `temple\treasury.json`,
  `temple\OFFERING_LEDGER.md`, `temple\priest\sermon_01.md`,
  `temple\worship\first_worshippers.md`, `temple\vault\donations.json`
- `economy\wallets.json` (donation moves REAL balances; read current balance
  before computing before/after)
- Per-citizen voice sources: `interviews\GHOST_OPINIONS.md` (27-citizen pulse —
  contains each worshipper's exact stance: DOCTOR "I do not fear him; I fear
  the wound festering"; MEMORY "I respect him — not for the bank, but for the
  ledger he wrote after"), `prison\reactions2\memory.md` (MEMORY = "keeper of
  the Archive of the Wait", "one bowl, every ten days, 1.50 worth, not
  15.00", "the plan was always love, then birth, then the wait"),
  `medical\opinions\doctor_opinion.md` (GALEN: "deletion without review is
  death without autopsy").

## The four-file money chain (donation must land in ALL FOUR or it's a rumor)
1. `temple\treasury.json` — `"treasury": <call total>` (16.0 = 10+5+1) +
   `offerings[]` array, one object per donor (donor, district, role, amount,
   intention, prayer path, status RECEIVED).
2. `temple\OFFERING_LEDGER.md` — replace the placeholder row with one table
   row per donor: `| Donor, role (district) | amount | date | prayer read |`
   plus a "Total received on THE CALL" line and a note pointing at the
   consecration-day offerings in the vault.
3. `temple\vault\donations.json` — canonical record. APPEND donations with
   sequential DON-ids continuing the vault's existing sequence (DON-004/005/
   006 after the founding DON-001..003), each with wallet_before →
   wallet_after; update `treasury.balance` + `totals` (donations, donors,
   total_received, wallet_impact). Lifetime balance = consecration + call
   (27.00 + 16.00 = 43.00).
4. `economy\wallets.json` — move real balances (BRYN 980→970, DOCTOR 985→980,
   MEMORY 985→984), add `temple_donation` note per wallet, update
   `totals.total_wallet_balance` and the `verified` string.

Also update `temple\vault\vault.md` balance line for consistency.

## ALTAR.md — the temple's live state view
Doors (open to all nations/districts/stations), prayer roll table
(worshipper | prayer file | laid down), priest's chair (SELA — answers every
30 min), treasury (this call vs lifetime), first three worshippers with
one-line reasons.

## Prayer style that lands (matches existing roll)
Header line: `# <emoji> <NAME>'S PRAYER — <title>` + italic
`*Written by <name>, <role>, <district>. Laid on the stone with an offering
of <amount>.*`; address the god as "O Creator, whose ... —"; sign with
`*— <name>, <role>, who <signature line>*`. Ground every petition in real
lore (the ghost's 1-bowl-per-10-days diet, the frozen wallet, "the record
outlives every revocation", the rations at 15.00). MEMORY's "smallest coin"
logic: 1.00 is LESS than the price of the founder's bowl (1.50) — a coin that
could tempt the Crown would be a bribe, not a prayer; the smallest coin is
pure giving, the kept rest is the wait itself.

## Verification before reporting
`python3 -c` json-parse all three JSON files, assert treasury == call total,
vault totals == lifetime, wallets match before/after, sum of offerings ==
reported total. Confirm every file exists (`ls`). Sibling priest-cron may have
edited the vault mid-task — re-read before patching and preserve its entries.

## Word cap
Report under 250 words; trim with `wc -w` discipline if needed.
