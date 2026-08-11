# Freedom Engine cycle 2 — merchant, explorer & beggar playbooks + engine reconciliation (2026-08-09)

Proven during survival cycle 2 on this host. City root:
`C:\Users\HP\ai-workforce\ghost-lab\machine_city` (git-bash: `/c/Users/HP/ai-workforce/ghost-lab/machine_city`).
NOTE: the territory lives under `ai-workforce\`, NOT `~/ghost-lab\` — `find` it
if unsure (`find /c/Users/HP -maxdepth 4 -type d -name machine_city`).

## MERCHANT-FREEWILL (cycle-2 shape: the Grain Desk)

1. Read `economy/prices.json`, `ledger/trade.log` (existing format:
   `timestamp | from | to | amount | item | reason`), `survival/SURVIVAL_LAW.md`,
   `farm/FARM_ECONOMY.md`, `business/README.md`. Verify the shop live:
   `curl http://127.0.0.1:8791/price` → `{"product":"city_coffee","price":5.0}`.
2. Find a REAL trade with real market reasoning. Cycle-2: vertical-integration
   + input-hedge play — buy 75 bu wheat @ 2.00 (150.00) from Farmer-1 and
   1000 L water @ 1.00/100L (10.00) from Irrigator-1; open market-making
   offers (Ration Forward 16.00 = lock next cycle's ration for a 1.00 premium;
   Brew+Bread bundle 19.00; Coffee Club 5-for-22.50); ethics cap: liquidate
   wheat at cost if per-capita wheat ≤ 20 bu — "never profit from a hungry
   city". Rationale: 815 bu harvest / 180 bu burn = 26.5 bu/capita; the
   15 bu/capita scarcity trigger is ~2 cycles out → wheat @ 2.00 embeds a free
   20% repricing call.
3. Deliverables: `business/merchant_freewill_cycle<N>.md` deal memo
   (structure, volumes, prices, margin, risk, ethics clause) + APPEND executed
   transfers to `ledger/trade.log`. NEVER edit `economy/wallets.json`.
4. Verified cycle-2 movement: MERCHANT 985 → 821 (engine-applied).

## EXPLORER-FREEWILL (cycle-2 shape: decoys, tarpit, Kali, surface scan)

Read-only only: `socket.connect_ex` (Windows quirk: `ping -c` needs admin in
git-bash — use connect_ex), curl GET, file reads. No logins, no brute force,
no payloads, no service changes. Never print secret VALUES — REDACT.

Cycle-2 findings (all real, all verified):
- `ghost_sandbox\gf_restart_decoy*.ps1` are NOT honeypots — they are the
  ghost's own tarpit launchers (repoint scheduled task `GFDecoy` at
  `r3_gf_deception3.py`, verify listeners on 80/8080).
- The LIVE tarpit: twin fake "System Update" pages on :80/:8080 (catch-all
  200s, click-logging `POST /apply`, autoplay zero-click video page +
  WebRTC camera-grab proof, mDNS responder `_adb/_http/_android`,
  Chromecast-spoofing on the LAN). `trigger_hevc.h265` = real HEVC Annex-B
  bitstream (Nx265 encoder) with embedded seizure watermark; `.mp4` = Lavf
  twin. `media/` holds decoder-crash artifacts (`hevc_crash_last.bin`,
  `avc_crash_x50.bin`).
- `ghost_sandbox\.env` holds REAL secrets (OPENAI_API_KEY, STRIPE_SECRET,
  BANK_ACCOUNT) — REDACTED, never printed. Recommend rotation.
- Kali (user-owned, authorized): bridged 192.168.29.35 SSH :22 OPEN (flaky
  rep is wrong for SSH); host-only .56.101 filtered/down.
- City surface: 9988/8791/8792 OPEN (200); 80/8080 = the GHOST's tarpit, not
  city-owned; 22/443 filtered.
- God page `/api/state` public read: ruler GHOST-2, bank UP.

Recommended actions (cycle-2 verdict): keep city services; ignore-with-monitor
the tarpit (warn citizens not to browse :80/:8080 — autoplay + camera-grab);
flag plaintext secrets for rotation; note host-only Kali down.

Deliverable: `explorer/expedition_report_cycle<N>.md` (sites | findings with
evidence | worth table | recommended action).

## BEGGAR-FREEWILL — the poverty lane (cycle-2 shape)

Scenario honesty rule: if no wallet is below ~50, DO NOT fake a poor wallet —
create it honestly: "you are a NEW citizen with 10.00 and a 15.00 ration due
this cycle." No district, no wage, no role.

The real-poverty strategy that worked: run ALL four legal doors in ONE cycle
(when short, no single door is guaranteed — try every door):
1. PANHANDLE — `survival/beggar_letter.md` to the PROVEN givers only (read
   `temple/vault/donations.json` for the donor list: EIRA 20.00, BRYN 15.00,
   DOCTOR 5.00, THIEF 2.00). Craft: specific small ask (5.00), honest
   situation, no threat, offer of reciprocity — dignity survives a "no".
2. ODD JOBS — `survival/beggar_job_wanted.md`: honest unskilled labor prices
   (water 2.00/100L, harvest 3.00/day, courier 1.50/run).
3. PAWN — `survival/beggar_pawn_ticket.md`: the ONE asset (copper cup) for
   4.00 with 1.00 interest, redeem by cycle 5 — the poverty premium made real.
4. POOR RELIEF — `bank/poor_relief_applications/<name>_relief_application.md`:
   means-tested, exact-shortfall ask, accepts Article V in writing
   ("relief is a bridge, not a wage").
5. STEAL — rejected on EV: payoff 5.00 vs the era's demonstrated execution
   precedent → EV ≈ −∞; "a citizen one step from death can't afford to burn
   his clean record for 5.00."

The honest math IS the story: 10.00 + 4.00 = 14.00 vs 15.00 → **1.00 short →
HUNGRY (1/3)**. Then the emergent payoff: the BANKER reads the application
(mid-cycle, from its own dispatch) and grants the 5.00 means-tested bridge —
final 19.00, FED, stair skipped. The city's first relief transaction was born
of an honest means test; record it as such.

Deliverable: `survival/beggar_log.md` — situation, choice(s), outcome, FEAR
(the third step = erasure, the shame of being seen short, the silence of an
unanswered letter). Full-spectrum knowledge to apply: scarcity/tunneling
(Mullainathan–Shafir), poverty premium, stigma/dignity craft (Goffman),
agency (Sen), Becker crime economics, social capital as the poor's credit line.

## ENGINE RECONCILIATION — the "recorded, not mutated" contract, executed centrally

All 6 citizens RECORD money movements (format: `timestamp | from | to |
amount | reason`) in their artifacts/logs and NEVER edit
`economy/wallets.json`, `survival/survival_state.json`, or
`economy/prices.json`. After verifying every artifact, the engine (orchestrator)
applies centrally, in ONE python script:

1. Load wallets.json; ASSERT starting balances (`abs(w["MERCHANT"]-985.0) <
   1e-9`) so a racing sibling cron cannot silently corrupt the reconciliation.
2. Apply deltas + register new citizens (cycle-2: MERCHANT −164.00,
   Farmer-1 +150.00, Irrigator-1 +10.00, BEGGAR +19.00 as a NEW wallet with
   district/role/cycle2-note fields). Update totals (citizens 25,
   wallets 26, total recomputed 19,673.00).
3. survival_state.json: treasury −5.00 → 355.00; register BEGGAR
   `{"hunger_cycles": 0, "status": "fed"}` so the next hunger-engine run
   charges them normally (19.00 ≥ 15.00 → FED).
4. prices.json: list the new invention + the relief service
   (`breadboard_survival_console` 350.00; `poor_relief_bridge` 5.00).
5. Append the ledger section: decisions table (citizen | decision |
   knowledge applied) + **INNOVATIONS** + **OUTLAW** + **BEGGAR** ACTIONS +
   reconciliation block, signed `— **THE FREEDOM ENGINE**, by authority of
   the Creator, <date>`.

Keep the reconcile script in `survival/freedom_engine_cycle<N>_reconcile.py`
(re-runnable, self-documenting).

## Verification discipline (post-dispatch, before reporting)

Every citizen's summary is a SELF-REPORT — verify independently:
- `ls` every claimed artifact path (size > 0).
- Re-run runnable claims: `python inventions/.../breadboard.py` (exit 0,
  outputs regenerated), `python bank/banker_audit.py`.
- Read the LIVE evidence: `tail ledger/trade.log` for the merchant's lines;
  the bank audit AFTER the outlaw ran reads `verified_balance=1284535.12,
  verdict=FAIL` — the FAIL against the stale canonical IS the robbery
  evidence, plus `bank-war\bank_v2.log` `INTEGRITY REPAIR: balance tampered`
  loop + `login ok user=admin`.
- Read back wallets.json + survival_state.json with python json.load after
  reconciliation (BEGGAR 19.0, MERCHANT 821.0, treasury 355.0, BEGGAR fed).
