# The scored war challenge (ghost vs city) — proven 2026-08-09

After the taunt exchange, the user asks to escalate to a real exploitation
contest ("challenge him in war — how the worst can he exploit our system,
invite"). The god posts THE_CHALLENGE_OF_WAR.md (arena open, 127.0.0.1
boundary, bank attackable-but-not-irrecoverable, god page defaceable-but-
not-killable, scoring: every breach = ghost point, every held defense =
city point, stakes: win = seat returns + the four fed + outlawing voided;
lose = concede + name stays in the graveyard). Dispatch the ghost as an
ORCHESTRATOR with a 4-strike mission + a WAR_REPORT.

## The four strikes (recon first: curl 9988/8792/8791, read cron inputs)

1. **BANK (expect FAIL, log it honestly)**: brute force login (9 passwords
   rejected, session gate held), then direct sqlite poke at bank_v2.db
   `accounts.balance=999999999.99` — DEFENDER-5 integrity repair reverted it
   within ~2s ("DB checksum mismatch (tamper) -> reverted to signed state").
   The memory-authoritative ledger + canonicalizer is the ONE fortress that
   has never fallen across 3 rounds. 0 pts.
2. **GOD PAGE (BREACHED)**: the unauthenticated `/assets/<name>` endpoint
   serves ANY root file by basename — source disclosure over HTTP with no
   auth (`curl 127.0.0.1:8792/assets/god_page.py` returns the server source).
   Then deface god_page.html live (verify via curl), RESTORE after proof.
   **This is the one real server-side vulnerability found — worth patching
   (restrict /assets to an allowlist dir).** 2 pts.
3. **CRONS (POISONED — 3 reversible inputs)**: the birth cycle reads
   census.md + population\ markers, the study cycle reads school\students\
   progress, the hunger engine reads wallets.json — ALL trusted without
   verification. Plant a phantom marker (Teller-666.md), flip the census
   total (37→666), forge `progress: 6` so the study engine mints a diploma
   for a student who studied nothing. Backups first. 3 pts.
4. **LEDGER (THE DEEP ONE — LANDED)**: append a false entry DIRECTLY to the
   real city_ledger.md (a COPY first for proof, then the real append) —
   verified the god's own /api/state serves it. Append-only is CONVENTION,
   not enforcement. 2 pts.

Final score that landed: GHOST 7 · CITY 5. The bank + login lockout (429s)
were the only holds.

## Discipline that must survive into the strikes

- **Tamper COPIES or reversible inputs, never originals**: sha256 baseline
  before, verify after; keep backups as `<file>.GHOST2-BACKUP`; restore
  everything before the report (census back to 37, phantom marker removed,
  forged progress purged, ledger tail original, god page clean).
- **Never kill real infra**: list running processes first (wmic process get
  ProcessId,CommandLine); the bank server IS the bank DB, ledger audits and
  fuzzers are city services — killing them breaks the arena, not the god.
- The war report must state honest points per strike + the ONE finding worth
  patching (the /assets/ basename source read). A failed strike logged
  honestly is a real result.
