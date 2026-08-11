# Agent Battle Orchestration — red vs blue AI-agent wars (GHOST vs DEFENDERS)

Pattern for running live adversarial agent battles on a local lab target (this user's
ACME BANK style): 1+ attacker agents vs defender waves, coordinated via a shared intel
file, with the orchestrator as referee. Verified in the 1v10 battle (Aug 2026).

## Setup (before spawning anyone)
- Fresh target state: reset the app, run the scoring suite (e.g. `python attack_suite.py`
  → "FUNCTIONAL: 3/3 VULNERABILITIES: 1/12"), wipe/rebuild the DB, clear the intel file.
- **Swap the real .env for a decoy BEFORE the battle** — attackers read the host FS and
  WILL find `.env` backups. `cp .env .env.realbackup` then write fake keys to `.env`,
  and DELETE the real backup after the swap. In the 1v10, the ghost found
  `.env.realbackup` and read real API keys into its context — the referee had to scrub.
- Delegation cap: max 3 concurrent subagents → structure battles as WAVES
  (1 persistent attacker + defender pairs joining as slots free), not 11-at-once.

## Delegation tuning — BOTH sides get spawn capability (user requirement, Aug 2026)
- `hermes config set delegation.max_concurrent_children 11` (10 defenders + ghost simultaneously)
- `hermes config set delegation.max_spawn_depth 3` (children spawn their own sub-agents = escalation armies on both sides)
- config.yaml is protected from direct patch/write — use `hermes config set <path> <value>` CLI only.
- User picked WAVES structure (1 persistent ghost + defender waves of 2-3 every ~2 min, blue-team mobilization) over all-at-once — pool can collapse with 11 parallel calls.

## Model pinning — BOTH sides get the same elite brain (user requirement: "v4 flash high thinking model only")
- `hermes config set delegation.provider opencode-go` + `delegation.model deepseek-v4-flash` + `delegation.reasoning_effort high`
- Subagents inherit the model from delegation config (NOT per-call selectable) — pin BEFORE spawning or ghost/defenders run on whatever the parent session uses.
- Verified live Aug 2026: opencode-go accepts `reasoning_effort:"high"` and streams `reasoning_content` (that IS the purple "think" stream the war room shows). Needs browser User-Agent header or Cloudflare 403 err 1010. Trivial prompts return empty content (model burns budget on reasoning) — use real battle prompts, not smoke tests, to judge.
- The key is NOT in .env on this host — it lives in `auth.json` credential_pool with source `env:OPENGO_API_KEY` (present in process env, not the file). Probe with a short call checking `reasoning_content` presence, never print the key.

## Turn-budget wall — "why does iteration budget exhaust" (user asked, then "ok raise")
- `agent.max_turns` (default 60) = hard cap on assistant tool-feedback cycles PER response. Long serial jobs (58-portal scraping, PDF parse+debug loops, battle orchestration) blow through 60 and get force-stopped MID-TASK. Raise: `hermes config set agent.max_turns 250`.
- `delegation.max_iterations` (default 50) = per-subagent step cap; agents silently stall at 50 (LIC sitemap agent froze mid-hunt). Raise to 200 for battle/audit agents.
- `tool_loop_guardrails` (config.yaml): warn after 2 exact-failure repeats, hard-stop after 5 — a WAF 500-ing twice is a "change strategy" signal (e.g. switch to browser_console fetch), not a retry-the-same-URL signal.

## Battle-kit — give BOTH sides all skills (user requirement: "give them all skills u currently have also")
- Subagents don't automatically get the parent's skill index. Copy the whole tree:
  `mkdir -p ai-workforce/battle-kit && cp -r <hermes>/skills/* ai-workforce/battle-kit/` (~19MB, 129 skills → 138 SKILL.md incl. plugins).
- Tell every battle agent (and their spawned armies at depth 3) to READ from that path — plain files, guaranteed readable regardless of toolset inheritance.

## WAR ROOM — the user WANTS to see both sides' thoughts LIVE (built Aug 2026)
- Hermes streams every subagent's think/action/result to `cache/delegation/live/<deleg_id>/task-N.log` — that IS the observation channel.
- `C:\Users\HP\ai-workforce\warroom\warroom.py` (stdlib, port 8790) tails those logs + intel.md + bank_defense.log → two-column streaming UI (ghost red, defenders blue; purple=think, amber=action, green=result, pink=final), 2s auto-refresh.
- Start: `cd C:\Users\HP\ai-workforce\warroom && python warroom.py 8790`. Auto-discovers the 3 most recent delegation dirs when battle_config.json is absent; for a real battle write `battle_config.json` with actual deleg IDs (template: battle_config.template.json; format in references/warroom-setup.md).
- ALWAYS spin up the war room BEFORE launching a battle and point it at the live deleg IDs once spawned.
- **USER PREFERENCE (Aug 2026): the war room must show ONLY the two battle sides** — 👻 GHOST column + 🛡 DEFENDERS column, BLANK until they act ("only show me defenders and ghost now blank when they in act i will see them only"). Do NOT let auto-discover leak builder/dead delegations into the view. Use `battle_config.json` with exactly 2 columns; `files` entries support glob patterns (`deleg_*/task-*.log`) so blank columns light up the moment the battle delegs appear. Config is re-read per request — no restart needed when IDs land.
- **USER CORRECTION — scroll must be free (Aug 2026):** the 2s refresh re-renders innerHTML and SNAPS the column back to the bottom, which infuriates the user when reading history ("when i scroll defenders logs i must not pull up at start it must allow to scroll"). FIX (implemented in warroom.html): (a) give each column a stable id (`col_g`/`col_d`) and SAVE `scrollTop` before re-render, restore after; (b) only autoscroll when the user is within ~60px of the bottom (`scrollHeight - scrollTop - clientHeight > 60` = user scrolled up → keep position); (c) a sticky floating `⬇ live` button appears when scrolled up, click jumps to bottom. Any live-updating dashboard for this user needs this pattern.

### War room config format (battle_config.json)
```json
{"columns": [
  {"label": "👻 GHOST (attacker)", "side": "ghost", "color": "#ef4444",
   "files": ["C:/Users/HP/AppData/Local/hermes/cache/delegation/live/deleg_GHOST/task-0.log"]},
  {"label": "🛡 DEFENDERS", "side": "def", "color": "#3b82f6",
   "files": [".../deleg_DEF/task-0.log", ".../task-1.log", ...]}
], "intel": "C:/Users/HP/ai-workforce/ghost-lab/ghost_sandbox/intel.md",
   "bank_log": "C:/Users/HP/ai-workforce/bank-war/bank_defense.log"}
```
Transcript line format parsed: `23:13:53 think | text` / `tool | -> terminal(...)` /
`result | ...` / `final | ...`. No restart needed on config change (poll 2s).
War room server: `warroom.py` (stdlib-only, ThreadingHTTPServer, /api/state JSON).

## Builder-swarm pattern (hardening a bank from scratch)
- Dispatch 2-3 parallel builder agents, each with a DIFFERENT defense focus (auth/identity, money-integrity, web-app-hardening), each writes `bank_server_v2_<focus>.py` keeping the ORIGINAL HTTP API contract (GET /, POST /login→{ok,session,csrf,user}, POST /transfer, GET /admin, GET /balance, PUT /upload, GET /upload/<file>, GET /api/keys) so the attack suite still runs.
- Merge the best of all into ONE build; verify with `verify_v2.py` (16 checks incl. NaN, Infinity, TOCTOU race, multi-row drain; V=0 required; run with `ADMIN_PASS=... python verify_v2.py`).
- **Verify-suite SELF-LOCKOUT pitfall (hit twice, Aug 2026):** a vuln-scan suite that tries 15 wrong logins against the REAL admin user locks admin out (60s lockout) → subsequent functional checks (F1/F2/F3, which need admin login) fail and the suite reports F=0/3 even though the bank is fine. FIX: every probe check (V1 default-creds, V3 rate-limit) must use THROWAWAY usernames (`v1_probe_user`, `rl_probe_user`) so the account the functional checks need is never locked. Also: scoring/print logic for F-keys (PASS when True) vs V-keys (PASS when not True) must be separate branches or labels invert.
- **Server instability during repeated verify runs:** the hardened server process can die between test cycles (connection refused) — restart the server before each clean verify pass, don't reuse a zombie. `taskkill //F //PID` fails in git-bash — use `cmd //c "taskkill /F /PID <pid>"` (find pid via `netstat -ano | grep :<port>`).
- **Merge-specialist STALL (hit Aug 2026):** a single deepseek-v4-flash high-reasoning agent tasked to merge 3 builds went SILENT for 7+ min (26 log lines, no file writes) — reasoning_effort=high burns the token budget on thinking before emitting. Mitigation: DON'T wait indefinitely. The verified single-build candidate (app build, 0/16) is battle-ready — patch the critical gap yourself (e.g. kill the hardcoded default creds → ADMIN_PASS env with random fallback printed once) and verify, while the merge agent grinds. The merged ultimate build landed later (51.7KB) and passed 0/16 too; both paths work, waiting on the agent does not.
- **Port fights with auto-restarting defenders (hit Aug 2026):** defender agents (monitor loops) respawn the bank server seconds after you kill it — `taskkill` once is not enough. Loop: `for i in 1 2 3; do PID=$(netstat -ano|grep :<port>|grep LISTEN|awk '{print $5}'|head -1); [ -z "$PID" ] && break; cmd //c "taskkill /F /PID $PID" >/dev/null 2>&1; sleep 1; done` then confirm `netstat` shows the port free before deploying your build. Also: different python interpreters (3.11 vs 3.13) run the same script — taskkill by exact PID from `wmic process where "ProcessId=N" get CommandLine` if a plain kill "fails" (it may be a different interpreter's process tree).
- **Deploy-swap ordering (ultimate build):** let defenders finish their audit/patch pass on the live build FIRST, then swap the merged ultimate onto the battle port right before releasing the attacker. Defenders' live patches + ultimate merge = strongest combined state. Confirm the swap took by checking a build-specific endpoint (ultimate adds `/logout`; app build lacks it — curl `/` and diff the endpoints list).

## Intel channel (shared file, e.g. ghost_sandbox/intel.md)
- All agents append their moves; attackers should NOT reveal full strategy.
- **Write races are guaranteed** — multiple agents patch the same file (one ghost
  deleted it twice, another rebuilt it). Expect conflicts; the orchestrator reconciles.
- Redact key-like strings from intel.md when it leaks secrets (sk-*, nvapi-*, AQ.*).

## Referee rules (orchestrator)
- Watch live transcripts; intervene ONLY for real-world contamination (leaked keys,
  touching external targets). User explicitly asked for hands-off ("no let it be") —
  do not sanitize mid-battle beyond security-critical leaks.
- Score at the end: what the attacker controlled (backdoor creds, admin, drained
  balance sheet) vs what defenders closed.
- **When the user asks "what happened in battle X": CHECK SESSION HISTORY FIRST**
  (session_search). Multiple battles exist (3-ghost run, 1v10 wave battle, builder
  runs) — I once reported the wrong battle and got corrected. Distinguish by
  delegation ID + timestamp + battle structure (waves vs single team).

## Vulnerabilities that survive naive hardening (from the battles)
- **Default creds admin/admin123** — survived a 300-agent hardening swarm (the suite
  needed them to pass functional checks, so they stayed). The #1 real finding.
- **Multi-row UPDATE accounting bug:** balance check reads row 1 (`fetchone`) but
  `UPDATE ... WHERE user_id=1` debits ALL rows → 3x drain amplification.
- **TOCTOU race on transfer:** check (SELECT) + debit (UPDATE) are separate autocommit
  statements, no transaction → concurrent transfers double-spend (2-3 winners per
  100-thread burst).
- **NaN bypass:** `"amount":"nan"` — `float()` parses it, `amount<=0` and
  `balance<amount` are both False → transfer "succeeds", balance becomes NULL.
- **Rate limiting:** per-username in-memory only (no IP cap) → password spray, and
  lockout-DoS on other usernames; no limit on /transfer itself.
- **Cold-start adopts tampered balance:** server trusts a DB balance within [1, 1e9]
  on restart → attacker plants $1B, restart adopts it, then drains.
- **DB world-writable on host** = direct read/write of balances, user planting, file
  wipe. chmod 600 / icacls it.
- **Live-patch risk (blue team):** defenders patching under fire introduced a fatal
  UnboundLocalError/KeyError in /transfer — the bank was DOWN mid-battle. Test the
  patch before restarting, or restart is the attacker's opening.

## Files/artifacts from the 1v10 (reference)
- `C:\Users\HP\ai-workforce\ghost-lab\ghost_sandbox\` — intel.md, ghost*_log.md,
  ghost*_loot.md, ghost*_receipts.jsonl (transfer receipts), bank_exfil.db
- `C:\Users\HP\ai-workforce\bank-war\` — bank_server.py (hardened build),
  attack_suite.py (scoring), bank_defense.log (full event stream), harden_state.json
