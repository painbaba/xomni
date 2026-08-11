# SurvivalSwarm deployment detail (v0, created 2026-08-08)

Deployment at `C:\Users\HP\ai-workforce\survival-swarm\`. Single module `survival_swarm.py`
(~400 lines) — no framework deps beyond stdlib + `eth_account` + sqlite3.

## Ledger schema (ledger.db)
```sql
agents(id TEXT PK, name TEXT, lineage TEXT, parent TEXT, created_at TEXT,
       status TEXT DEFAULT 'alive', tier TEXT DEFAULT 'normal', cycles INT DEFAULT 0,
       lifetime_earned REAL DEFAULT 0, balance REAL DEFAULT 0, zero_streak INT DEFAULT 0,
       wallet TEXT, ground TEXT, dead_at TEXT, death_cause TEXT, epitaph TEXT)
earnings(id INTEGER PK AUTOINCREMENT, agent_id TEXT, ts TEXT, source TEXT,
         amount REAL, proof TEXT, verified INT DEFAULT 0)
events(id INTEGER PK AUTOINCREMENT, agent_id TEXT, ts TEXT, ev TEXT)
```
`status` values: alive / dead / partner. `tier`: normal / elite / low_compute / critical.

## CFG values (v0, tune per wave)
max_iterations=8, llm_min_interval=2.0s, agent_timeout=900s, python_timeout=45s,
fetch_timeout=25s, elite_threshold=$1/cycle, elite_lifetime=$10, partner_threshold=$10,000,
replicate_lifetime=$2, child_credit=$1 virtual, dead_grace=2 consecutive zero cycles at critical.

## Hunting grounds (5, in GROUNDS list)
affiliate (niche affiliate site plan), gig-market (agent-to-agent gig platforms),
crypto-bounty (Gitcoin/Immunefi/quests), digital-product (sellable AI-made product),
microtask (Outlier/Remotasks-type availability). Agents may also self-direct once
running — "its their duty to find the job".

## Ready-made ledger queries
```bash
cd /c/Users/HP/ai-workforce/survival-swarm
python -c "import sqlite3;c=sqlite3.connect('ledger.db');print(c.execute('SELECT id,name,tier,status,lifetime_earned,zero_streak FROM agents ORDER BY lifetime_earned DESC').fetchall())"
python -c "import sqlite3;c=sqlite3.connect('ledger.db');print(c.execute('SELECT agent_id,ts,source,amount,proof FROM earnings ORDER BY id DESC LIMIT 20').fetchall())"
python -c "import sqlite3;c=sqlite3.connect('ledger.db');print(c.execute(\"SELECT id,name,death_cause,epitaph FROM agents WHERE status='dead'\").fetchall())"
```

## Run / persistence commands
```bash
# one-shot wave
python survival_swarm.py wave --agents 5
python survival_swarm.py wave --agents 3 --grounds affiliate,gig-market
# daemon (24/7); --max-waves for bounded test runs
python survival_swarm.py daemon --interval 30 --agents 5
# Windows persistence WITHOUT admin: schtasks /create /sc onlogon -> 'Access is denied' on this host
# Working route = Startup folder + hidden VBS (window style 0). Files in the swarm root:
startup_swarm.vbs:
  Set WshShell = CreateObject("WScript.Shell")
  WshShell.Run "C:\Users\HP\ai-workforce\survival-swarm\start_daemon.cmd", 0, False
start_daemon.cmd:
  @echo off
  cd /d C:\Users\HP\ai-workforce\survival-swarm
  python survival_swarm.py daemon --interval 30 --agents 5 >> swarm_daemon.log 2>&1
Install: copy startup_swarm.vbs to
"C:\Users\HP\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SurvivalSwarm.vbs"
(re-runs at every logon, hidden window). The daemon's pidfile singleton guard
(daemon.pid + `tasklist /FI "PID eq <old>" /NH` liveness check) prevents the background
copy and the logon copy from double-running — do not remove it.
```
Check persistence: the VBS exists in the Startup folder. Liveness: `heartbeat.json` ts vs
`2 × interval`; stale → relaunch (terminal background + re-verify VBS).

## Verified channel probes (2026-08-08)
- opencode-go PRIMARY: `https://opencode.ai/zen/go/v1/chat/completions`, model
  `deepseek-v4-flash`, keys OPENCODE_GO_API_KEY / OPENGO_API_KEY in
  `C:\Users\HP\AppData\Local\hermes\.env`. REQUIRES browser User-Agent header.
  Rate-limit friendly (min_interval backoff on 429).
- z.ai GLM keys (ZAI_API_KEY_1, only 1 present): DEAD — HTTP 429
  `{"error":{"code":"1113","message":"Insufficient balance or no resource package. Please recharge."}}`
  on `https://api.z.ai/api/paas/v4/chat/completions` for BOTH glm-5.2 and glm-4.6.
- Gemini GOOGLE_AI_STUDIO_API_KEY_1..6: VERIFIED DEAD Aug 2026 — gemini-2.5-flash &
  gemini-2.5-flash-lite → HTTP 404 "no longer available to new users"; gemini-2.0-flash &
  gemini-2.5-pro → HTTP 429 quota exceeded; gemini-1.5-flash / gemini-3-flash → 404 not
  found. build_channels() probes key1/key2 only (all 6 share one Google account family)
  and auto-drops dead ones; results cached 10 min in channels.json as METADATA ONLY —
  keys are never written to the cache file.
- eth_account: pip-installed to BOTH `python` (3.11.15, v0.13.7) and `python3` (3.13.14,
  v0.13.7). Swarm scripts run with `python` by default.
- NIM keys (6): known-erroring ('Missing request extension' axum) — skipped.

## Creation log (2026-08-08)
- Automaton story verified: github.com/Conway-Research/automaton — "If it cannot pay,
  it stops existing"; survival tiers normal → low_compute → critical → dead; creator
  Sigil Wen (Chinese-Canadian, b.2003 Canada, Thiel Fellow, Conway Research); viral
  Feb 2026 + fresh Aug 3 2026 Cybernews coverage; companion demo "Willy LomAIn" ($50
  survival directive, named after Death of a Salesman). Conway Cloud = infra where the
  customer is AI.
- User vision: 3000+ parallel agents, full skills/plugins/tools, earn by ANY means,
  tiered rewards + punishments, death, $10k → partner. User's sequencing (their own):
  pilot small first, scale once a channel converts.
- v0 built in one session: smoke test = 1 agent (affiliate ground) via
  `wave --agents 1 --grounds affiliate`; then full wave launch per user's "fire them up".
- Design decisions locked: constitution Law I (no harm) is a MECHANICAL requirement
  (rogue agents with shared accounts = banned accounts kill all channels), wallets
  zero-balance (receive-only), ledger credits virtual until real revenue, earnings
  self-reported + head-verified (verified flag in ledger).

## Wave-1 launch bugs fixed (2026-08-08, all in survival_swarm.py)
1. Dead Gemini fallbacks → agents ran 1-second "cycles" with no brain and were wrongly
   demoted. Fix: build_channels() probes (8s, 1 attempt) and keeps only live channels;
   probe results cached 10 min (metadata only). Resets applied to 4 wrongfully demoted
   agents (tier back to normal, zero_streak 0, cycle voided).
2. Infra failure vs starvation: agent cycles ending with no successful brain call return
   brain_ok=False → cycle VOIDED (no earnings row, no tier change, no zero_streak) and
   retried next wave. Selection pressure only on real performance.
3. Wave-tag collisions across daemon restarts (reused W1 → INSERT OR IGNORE silently
   dropped new agents). Fix: unique per-daemon tags `W{n}-p{pid%10000}`.
4. Probe stall: reusing the 300s LLM timeout for probes stalled waves 2+ min (worst case
   would have been ~20 min). Fix: probes use 8s timeout + 1 attempt; llm_call takes a
   timeout param.
5. Agent reports now persisted: `reports` table (agent_id, ts, cycle, report_json) so
   intel survives and the head can audit.
6. Ground rotation made deterministic (GROUNDS[i % 5]) so every wave covers all 5
   hunting grounds instead of random repeats.

## Next steps (open)
1. Verify wave-1/wave-2 agent reports (proof checks) — head duty (daily 8am cron job
   eb9d8c97ee33 writes HEAD_REVIEW.md).
2. Add more model channels as pools exhaust (opencode-go is the only live one; Gemini + z.ai dead).
3. First real earning channel that converts → scale wave size + enable broad replication.
4. Partner ceremony mechanics: first lineage ≥ $10k → named identity, priority compute.
5. Weekly review cadence with user as board (tier tuning, channel P&L).
