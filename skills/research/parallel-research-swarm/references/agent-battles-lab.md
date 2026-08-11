# Agent Battles Lab — hardened-target builder swarm + defender/attacker wars

Pattern for running a live, multi-agent offensive/defensive battle on a LOCAL
target (this host: ACME BANK at 127.0.0.1:9988, `ai-workforce/bank-war/`).
Reused machinery from the lab campaigns, scaled to full red-vs-blue wars where
BOTH sides are spawn-capable agent armies.

## The 4-phase program (as run Aug 2026)
1. **BUILD** — spawn N parallel builder agents (deepseek-v4-flash, high
   thinking), each writing a hardened target from scratch with a DISTINCT
   defense philosophy (auth/identity, money-integrity, web-app-hardening). Each
   writes its own file, keeps the HTTP contract, self-tests.
2. **VERIFY** — a comprehensive scoring suite that includes the KNOWN exploit
   classes (NaN/Infinity amounts, TOCTOU races, multi-row UPDATE drain, default
   creds, SQLi, CSRF gaps, path traversal, webshell upload, session
   predictability, verbose errors, rate-limit absence, public secrets).
   Ultimate build must score V=0. Merge specialist combines the best of all
   builder candidates into one file, re-verifies, reports both suite scores.
3. **GUARD** — spawn 10 defender agents (specialized: deep-audit,
   monitor-and-respond, forensic-hardening, network/transport, database,
   upload/app-layer, session/crypto, incident-response lead, backup/HA,
   ex-attacker). All coordinate via a shared intel file; all read the
   battle skill-kit; all may spawn their own helpers.
4. **RELEASE** — spawn the attacker (GHOST) as an ORCHESTRATOR with explicit
   spawning capability, pointed at the same intel + defender transcripts.

## Config knobs (hermes config set — ALL required for a real battle)
```
delegation.max_concurrent_children 11     # 10 defenders + ghost
delegation.max_spawn_depth 3              # both sides field armies
delegation.model deepseek-v4-flash
delegation.provider opencode-go
delegation.reasoning_effort high          # streams reasoning_content (war-room purple lines)
delegation.max_iterations 200             # battle agents are long-lived
agent.max_turns 250                       # parent budget; 60 gets cut mid-battle
```
Subagents inherit model/provider/effort from delegation config. Verify the
channel is live BEFORE the battle: probe opencode.ai/zen/go/v1 with browser UA
+ `reasoning_effort: "high"` — expect 200 with reasoning_content present.

## Skill kit for battle agents
Subagents do NOT inherit the parent's skill index. Copy the whole skills tree
once and tell every agent to read from it:
`cp -r ~/AppData/Local/hermes/skills/* ai-workforce/battle-kit/`
Spawn prompts must say: "battle skill kit at <path> — read security/bug-bounty-hunting,
software-development/systematic-debugging for technique."

## War room (live thought viewer)
Hermes streams every subagent's thoughts to
`cache/delegation/live/<deleg_id>/task-*.log` (lines: `HH:MM:SS kind | text`).
`scripts/warroom.py` + `templates/warroom.html` (see skill) render a two-column
GHOST/DEFENDERS feed that polls every 2s. battle_config.json maps column ->
glob of task logs; config is re-read per request (no restart to add columns).
UI must PRESERVE scroll position on re-render (user scrolls up to read history,
it must not snap) + a floating "⬇ live" button to jump back.

## Pitfalls (all hit in real battles)
- **Verify suites self-lockout**: a suite that probes failed logins on the REAL
  admin username trips the 60s shared-IP lockout, then later functional checks
  fail → looks like the bank broke. ALWAYS probe with throwaway usernames
  (V1/V3-style checks), never admin. Run suites on a fresh instance.
- **F-key display inversion**: score headers vs per-line PASS/FAIL logic must be
  consistent (`'PASS' if r[k]` for F-keys, `'PASS' if not r[k]` for V-keys).
- **Split-brain listeners**: parallel defenders each restart the server → 2-3
  processes bind the same port. Restore scripts must enforce EXACTLY ONE
  listener (kill ALL on port, spawn one).
- **Port-fight churn**: defenders auto-respawn seconds after a kill; loop the
  kill (up to 3x) and verify the port is FREE before spawning your build.
- **Multiple python interpreters**: python.exe (3.11 uv) vs python3.13.exe
  (WindowsApps). taskkill needs the exact PID; check `wmic process where
  "ProcessId=N" get CommandLine` if a kill "fails" silently.
- **Merge-agent stalls on high-thinking**: deepseek-v4-flash with
  reasoning_effort=high sometimes burns its token budget reasoning and NEVER
  emits (transcript mtime frozen for minutes). Check transcript mtime; if
  silent >3 min, take over manually instead of waiting.
- **Watchdog vs ghost race**: a 2s DB-integrity watchdog reverts planted users
  and hash overrides, but the ghost reads the defenders' OWN source/restore
  scripts to find the seam — treat defender source as exposed to the attacker
  in the threat model.
- **High-thinking on trivial prompts returns empty content** (model spends
  budget on reasoning) — normal, not a failure; real prompts produce both.

## Hardened-target defense layers worth merging (the "ultimate" recipe)
- Auth: PBKDF2-SHA256 (200k) + salt + constant-time compare, session TTL,
  single active session (rotation), /logout, 5-fail lockout, per-IP+user limits
- Money: BEGIN IMMEDIATE atomic transfer, check-inside-tx, row-scoped
  `UPDATE ... WHERE id=? AND balance>=?`, hash-chained append-only ledger,
  2s tamper-reverting watchdog, signed cold-start state (HMAC) — never adopt a
  tampered balance
- App: strict JSON schema (reject unknown keys/bools), upload allowlist + magic
  bytes + random names + traversal-proof, generic errors (no stack/paths), CSP
  default-src 'none', nosniff, no-store, parameterized SQL everywhere
- No default creds: ADMIN_PASS from env, random token_urlsafe(18) fallback
  printed once at boot

## Scoring notes
- 16-check verify suite (verify_v2.py) beats the old 12-check attack suite:
  adds NaN, Infinity, TOCTOU race, multi-row drain — the exact exploits that
  win battles. Old suite's V1/F1 are the same check and can't distinguish
  env-configured creds from hardcoded ones — use the throwaway-user V1.
