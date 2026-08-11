---
name: autonomous-agent-economy
description: Use when building agent swarms that must earn money or die.
---

# Autonomous Agent Economy (SurvivalSwarm)

Vision (user's): thousands of parallel agents, full tools, one directive — EARN OR DIE. Earners rise through reward tiers; starvers demote through punishment tiers to death; lifetime $10k = PARTNER (permanent identity, priority compute, seat in decisions). Winners replicate (spawn children funded from own earnings); losers get no descendants. Hermes (me) is HEAD: orchestrator, verifier of earnings, promoter, strategist.

## User preferences (hard requirements)
- REAL brains, not scripts. User explicitly rejected python ReAct-loop agents: "give them brain instead python scripts spawn them a ur subagents". Agents = Hermes subagents via delegate_task with full toolset (terminal, files, web). Scripts are for bookkeeping/scheduling ONLY.
- 24/7 continuous running: schedulers must run forever, survive reboots, auto-recover. User: "u not stop 24/7".
- Earn by ANY means: full internet, real crypto wallets, agents must find their own work. But with a constitution (never scam/spam/harm; shared user accounts OFF-LIMITS) — a mechanical necessity, not moralizing: a rogue agent holding shared keys gets the accounts banned and kills the channel for everyone.
- No fabricated results, ever. Earnings count only with proof; the head verifies every cent.

## Architecture v2 (proven in production)
Three components:
1. Bookkeeping (python): ledger + tier engine + reaper. survival_swarm.py (Ledger class) + swarm_settle.py. SQLite at survival-swarm/ledger.db — tables: agents, earnings (verified flag, default 0), events, reports.
2. Dispatcher cron (Hermes cronjob, every 30 min, enabled_toolsets terminal+file+delegation): reads ledger → picks ≤3 alive agents with fewest cycles → builds missions from templates/mission_prompt.txt → delegate_task batch → runs `python swarm_settle.py`.
3. Subagent brains (delegate_task): full tools; each writes reports/<agent_id>.json (exact schema, see template) and deliverables into sandbox/<id>/.

Wave flow: dispatcher → subagents research/act → reports land in reports/ → settle records earnings (verified=0), applies tiers, reaps, tombstones, writes STATUS.md → repeat forever.

## Tier engine
- earned ≥ $1/cycle OR lifetime ≥ $10 → elite (replication rights; spawns child at lifetime ≥ $2)
- $0 cycle: normal→low_compute→critical→DEAD after `dead_grace` (2) consecutive zero cycles at critical; tombstone with epitaph
- lifetime ≥ $10,000 → partner (status='partner', promotion event)
- Infra failures (no brain/model/tool access) NEVER demote: cycle voided, tier unchanged, retry next wave. Selection pressure applies only to real performance.

## Pitfalls (all hit in production, all fixed — do not rediscover)
1. PROBE model channels before routing agents. Dead channels produce 1-second "cycles" → innocent agents wrongly demoted (happened when all 6 Gemini keys were dead). Channel pool must contain only channels that answered a live probe.
2. Probe timeouts must be short (8s, attempts=1). Reusing the 300s LLM-call timeout for probes hangs the daemon silently for minutes.
3. Never cache API keys in support files (channels.json). Cache channel METADATA (name/url/model) only; reattach keys from .env at load.
4. Unique agent IDs per daemon/scheduler instance (embed pid: `W1-p<pid>-00`). INSERT OR IGNORE silently drops colliding IDs and the running agent becomes a ghost.
5. Agents burn the whole iteration budget on research and never report. Force a final-report synthesis call when the budget exhausts; require ≥1 deliverable file per cycle; cap research at ~6 of 12 actions.
6. Real wallets: `pip install eth-account` (pure python). Account.create() per agent. Zero-balance wallets make spending impossible by construction — receive-only. This is the honest default until real revenue funds the swarm.
7. Windows reboot persistence: `schtasks /create /sc onlogon` fails without admin ("Access is denied") → use the Startup folder VBS launcher (WScript.Shell Run <cmd>, 0, False = hidden window). Singleton guard: pidfile + `tasklist /FI "PID eq N"` liveness check.
8. git-bash: /tmp does not exist — `curl -o /tmp/x` fails (exit 28, no file). Use $HOME-relative paths.
9. Search engines block plain curl (Bing → captcha, DDG lite → timeout, Mojeek → captcha, Google News RSS → sorry page, Bing RSS format=rss → ignores query, returns boilerplate). Working pattern: r.jina.ai reader proxy — `curl https://r.jina.ai/https://duckduckgo.com/?q=<query>` returns the SERP as markdown; parse numbered results. Page reads: `https://r.jina.ai/<url>`. raw html.duckduckgo.com/html/?q= works from subagent sandboxes sometimes; expect 202 anomaly pages and pivot.
10. Free model channels are flaky and die daily (see references/free-model-channels.md). Design for exhaustion: low-power mode (skip spawns, keep ledger), resume when quota resets. The swarm itself lives under survival pressure — fitting.
11. deepseek-v4-flash (opencode-go): `reasoning_effort` unset or "high" burns the ENTIRE max_tokens on hidden `reasoning_content` → content EMPTY with finish=length; `reasoning_effort:"low"` returns real content (verified matrix None/low/high → 0/11k/0 content tokens). Any script or harness calling this API must set reasoning_effort low. Symptom: `LLM fail ()` with empty error after ~30-60s. (Hit in the bank-war builder swarm; see agent-experiment-labs references/containment-and-battles.md.)
13. Hermes cron `schedule: '30m'` is a ONE-SHOT ("once in 30m", repeat=once) — the dispatcher must use an explicit cron expression `*/30 * * * *` for repeat=forever. Check the `repeat` field after creating; a one-shot dispatcher silently stops the swarm.
14. First-wave agents burned their whole budget on known-blocked search endpoints (html.duckduckgo.com/lite/Bing/Mojeek — see pitfall 9) and reported 0 opportunities, 0 deliverables → innocent demotions. Fix, now in production: mission_prompt.txt embeds the TOOLING PITFALLS list (r.jina.ai only, prefer direct URLs) + VERIFIED LIVE CHANNELS (Bountycaster $20-500 USDC no-KYC reply-claim, Superteam Earn, Immunefi, Code4rena, Gitcoin grants) + VERIFIED DEAD channels (OnlyDust shut down, Gitcoin explorer bounties pivoted to grants). Dispatcher STEP 3 context must carry the same web-access guidance (don't let its own context re-teach DDG). Work plan changed to "ACT, don't research": ≤4 research steps, then one REAL money action (create no-KYC account, submit/claim bounty, draft content) + ≥1 deliverable file; empty sandbox = failed cycle.
15. Only agents dispatched in a wave get evaluated at settle (no report = no demotion). A critical-tier agent left out of a wave survives that cycle — the dispatcher's fewest-cycles-first ordering incidentally gives deathbed agents a reprieve while lower-cycle agents work. Death is NOT automatic every wave; it requires being picked AND earning $0.
13. A created dispatcher cron is NOT proof the swarm is running. `cronjob action='list'` showing `last_run_at: null` + a stale STATUS.md/heartbeat.json = silently idle swarm (hit Aug 9 2026: status frozen 24h, 14 agents alive, $0, dispatcher had never fired). Kick the first wave immediately with `cronjob action='run' job_id=<id>` — it executes in place and sets last_run_at — instead of waiting for the next tick. Health check = heartbeat.json `ts` freshness + reports/ gaining files, NOT file existence. Old python daemon (start_daemon.cmd / daemon.pid) is retired; its process being dead is expected, not a fault.
16. **0-alive terminal state = silent idle, not a crash (hit Aug 10 2026: 14/14 dead, $0 lifetime).** When ALL agents are dead (STATUS.md `alive: 0`), the dispatcher cron keeps firing on schedule but picks ≤3 alive agents → picks nobody → writes nothing; heartbeat.json goes stale while `last_run_at` stays fresh. Looks healthy from cron, it's a graveyard. There is NO auto-respawn — agents only come back if the head manually seeds a new wave. Detection: STATUS.md `alive: 0` + reports/ not growing. Respawn recipe (from the head-review's strategy section): (a) mission_prompt.txt submission-first mandate — every cycle must END in a posted claim/listing/sent submission; research capped at 1 cycle, then execution or death; (b) reallocate grounds by time-to-first-dollar — 5 gig-market (Bountycaster claims + Superteam submissions), 4 digital-product (publish existing Gumroad-ready products), 3 crypto-bounty (submit-only, 1 cycle recon max), 2 microtask, ZERO affiliate (its payout horizon exceeds agent lifespan — dead channel for 3-cycle agents); (c) harvest the dead's sandbox deliverables instead of re-researching (copy assets into fresh agent dirs at spawn); (d) verify the respawn wave actually fired (heartbeat ts updates, reports/ gains files) — don't assume. Also: 3 zero-cycles ≈ 90 min of life is shorter than EVERY payout pipeline (KYC walls, approval waits, bounty review) — the survival window favors only no-approval grounds.

## Related
- agent-experiment-labs — sandboxed unconstrained-agent experiments (ghost labs, containment guards, defender/attacker battles, live transcript monitoring) built from the same infrastructure (bank-war/, ghost-lab/).

## Subagent mission contract
- Mission template: templates/mission_prompt.txt — subagent reads it from disk; dispatcher fills placeholders (AGENT_ID, NAME, LINEAGE, GROUND, TIER, LIFETIME, WALLET, GROUND_DESC).
- Report schema (EXACT keys): agent_id, earned_usd, source, proof, opportunities[], actions_taken[], next_cycle_plan, deliverables[], error.
- earned_usd = REAL money received only; 0.0 is honest and fine. error field = infra failure (no punishment).
- Subagent gets its wallet from the ledger via sqlite SELECT (never embed in the mission).
- Grounds (rotate so every wave covers all): affiliate, gig-market, crypto-bounty, digital-product, microtask.

## Head duties (verify, never trust)
- Daily audit cron (survival-swarm-head-review, 8am): read ledger, VERIFY each earning proof URL (fetch it; dead/fake → UNVERIFIED), promote partners at $10k, write HEAD_REVIEW.md, adjust ground assignments. Never credit unverified earnings.

## Files at C:\Users\HP\ai-workforce\survival-swarm\
- ledger.db — truth; STATUS.md / heartbeat.json / swarm.log — status; reports/*.json — subagent reports (settle consumes and deletes); sandbox/<id>/ — deliverables; mission_prompt.txt, swarm_settle.py, survival_swarm.py, start_daemon.cmd (retired python-brain path).

## References
- references/free-model-channels.md — channel endpoints/models/probe results (Aug 2026)
- templates/mission_prompt.txt — subagent mission template
