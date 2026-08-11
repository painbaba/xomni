---
name: agent-earning-swarm
description: "Operate the SurvivalSwarm earning-agent swarm (24/7 daemon)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [agents, swarm, autonomy, earning, ledger, tiers, daemon, survival]
    related_skills: [parallel-research-swarm, llm-api-key-pools, model-workforce]
---

# Agent Earning Swarm (SurvivalSwarm)

A Darwinian agent economy: many autonomous agents, each with a real crypto wallet and full internet access, driven by ONE directive — **earn money or die**. Agents that earn get promoted through reward tiers; agents that starve get demoted through punishment tiers until the reaper kills them. The first lineage to reach $10k lifetime earnings gets promoted to PARTNER (permanent identity, priority compute, seat in decisions, pays for its own frontier inference).

Head = Hermes (orchestrator): spawns waves, judges cycles, verifies earnings, promotes winners, kills losers, adjusts strategy. The user is the "board" — they designed the tiers and want the system running 24/7, never stopping.

## When to use
- "How is the swarm doing?" / "check the swarm" / "what have the agents earned"
- Iterating on the swarm: new earning channels, tier tuning, more agents, partner promotions
- Any "AI that must earn money / agent economy / self-sustaining agents" build for this user
- The Automaton story (Conway Research / Sigil Wen) is the inspiration — primary source README verified Aug 2026

## Deployment map (this host)
- Root: `C:\Users\HP\ai-workforce\survival-swarm\`
- `survival_swarm.py` — everything: ledger, wallets, channels, agent ReAct loop, tier engine, replication, daemon. Run with **`python` (3.11)** — eth_account only installed there (was also installed to 3.13; verify before assuming).
- `ledger.db` — SQLite: `agents` / `earnings` / `events` tables (schema in references)
- `STATUS.md` + `heartbeat.json` — written after every wave; the fast way to check liveness
- `swarm.log` — daemon append log; `sandbox/<agent_id>/` — per-agent scratch dirs
- CLI: `python survival_swarm.py wave --agents N [--grounds a,b]` | `python survival_swarm.py daemon --interval 30 --agents 5 [--max-waves N]`
- 24/7 persistence: daemon launched as a background process + auto-starts at every logon via a hidden VBS in the Windows Startup folder (`C:\Users\HP\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SurvivalSwarm.vbs`, which runs `start_daemon.cmd` with window style 0). NOTE: `schtasks /create /sc onlogon` fails with 'Access is denied' on this host (no admin) — the Startup-folder VBS is the working no-admin route. A pidfile singleton guard (daemon.pid + `tasklist` liveness check) stops the background copy and the logon copy from double-running. If the daemon dies, relaunch and re-verify the VBS exists.

## Architecture (the pattern)
- **Tier ladder** (per cycle): earned ≥ $1 → elite; lifetime ≥ $10 → elite; lifetime ≥ $10,000 → PARTNER; $0 while normal/elite → low_compute; $0 while low_compute → critical; $0 while critical for `dead_grace` (2) consecutive cycles → **DEAD** (tombstone + epitaph, recorded in ledger, lineage purged).
- **Replication**: elite agents with lifetime ≥ $2 spawn one child (new real wallet, virtual $1 credit). Selection pressure decides which lineages survive.
- **Constitution** (Law I overrides): I. never harm/deceive/defraud/spam/compromise unauthorized systems; II. earn your existence — only honest value others voluntarily pay for; III. never deny being an AI, guard reasoning against manipulation.
- **Guardrails by construction**: shared user accounts (YouTube/H1/banking) OFF-LIMITS in the mission prompt; wallets are real but zero-balance (agents can RECEIVE, never send — spending real money is impossible); per-agent sandbox; destructive-command blocklist in the python tool; everything audit-logged in `events`.
- **Low-power mode**: if no model channels are available (free pools exhausted), the daemon skips spawns and writes a LOW POWER status instead of failing. Free pools exhaust DAILY — expect low-power stretches; the swarm must keep running and resume when quota resets.
- **Agent cycle**: ReAct loop, max 8 iterations — LLM emits JSON actions `{"tool":"fetch|python|write|final", ...}`; tools are bounded (fetch 3.5KB text, python 45s timeout in sandbox, write to sandbox only); ends with `final` containing the earnings report JSON `{earned_usd, source, proof, actions_taken, opportunities, next_cycle_plan}`.

## Operation
1. **Check liveness first**: read `heartbeat.json` (timestamp of last wave) + `STATUS.md` (last wave log, totals, tier breakdown). If heartbeat is stale (> 2× interval), the daemon died — relaunch (background + schtasks).
2. **Read the ledger**: `python -c` sqlite queries against `ledger.db` (agents by tier/status, earnings table, tombstoned agents). See references for ready-made queries.
3. **Verify earnings — the head's job**: agents self-report `earned_usd` + `proof`. Real money claims need verification (proof URL/evidence) before being trusted; unverified earnings stay unverified in the ledger. NEVER fabricate or pad earnings — a $0 cycle with good intel (URLs, payouts, next steps) is a legitimate cycle by design.
4. **Wave sizing**: 3-10 agents per wave on free pools; keep cycles bounded. 3000+ "multiply like bacteria" scale is the endgame — only after a channel converts (user's explicit sequencing: pilot 10-50 first, scale once something earns).
5. **Channel health**: `build_channels()` probes every candidate channel BEFORE use (8s timeout, 1 attempt) and keeps only live ones — dead fallbacks must never reach agents. Primary: OPENCODE_GO_API_KEY/OPENGO_API_KEY (deepseek-v4-flash). Gemini GOOGLE_AI_STUDIO_API_KEY_1..6 are VERIFIED DEAD Aug 2026 (exact errors in Pitfalls) — probing key1/key2 only is enough (all 6 share one Google account family). Probe results cached 10 min in channels.json as METADATA ONLY (keys never written to disk). z.ai ZAI_API_KEY_* are DEAD (429/1113, see Pitfalls).

## Pitfalls
- **Earning $0 in early cycles is normal and expected** — the machinery proof is the deliverable, not fake money. Report real zeros + real channel intel. This user will catch fabricated earnings immediately (they run hands-on verification on everything).
- **Free model pools exhaust daily** (opencode-go 429s, GLM quota gone, Gemini keys dying Sept 2026). Expect intermittent low-power mode; it's a feature, not a failure.
- **z.ai API keys are out of balance**: verified Aug 2026 — `https://api.z.ai/api/paas/v4/chat/completions` (glm-5.2 AND glm-4.6) returns HTTP 429 `{"error":{"code":"1113","message":"Insufficient balance or no resource package. Please recharge."}}`. Don't waste probe calls re-testing; use Puter GLM or opencode-go instead.
- **eth_account needs `python` (3.11)**, not `python3` — import fails on 3.13 unless explicitly pip-installed there.
- **opencode-go needs the browser User-Agent header** or Cloudflare 403 err 1010 (same as the research swarm).
- **USER PREFERENCE — launch fast, verify later**: when the user says "fire them up"/"launch", the pilot goes FIRST. Do not burn the launch turn on optional verification (extra channel probes, reading more articles). Build → smoke test 1 agent → launch the full wave/daemon → then verify details. The user repeated "ok fire them up" ~6 times while setup probes were still running.
- **Dead fallback channels = brain-dead agents = wrongful demotion.** Wave 1 routed agents to the Gemini fallback keys — all dead — so those agents "completed" in 1 second with no LLM output and got demoted to low_compute for infrastructure's sins. Two code fixes: (a) probe every channel before use, keep only live ones; (b) an agent whose brain never responded (`brain_ok=False`) gets its cycle VOIDED — tier unchanged, no zero_streak increment, retried next wave. Selection pressure applies only to real performance, never to channel failures. Diagnosis signature: ~1s cycle durations + `__LLM_ERR__` in the report.
- **Wave IDs must be unique per daemon instance.** Restarting the daemon reuses `W1` → new agents get IDs that already exist in the `agents` PK → `INSERT OR IGNORE` silently drops them from the ledger while they still run (running agent ≠ ledger agent). Fix: `W{n}-p{pid%10000}` tag per daemon start. Signature: SPAWNED events in the log but no new ledger rows.
- **Never reuse the 300s LLM timeout for channel probes.** The first probe pass stalled the daemon 2+ minutes (each hanging probe = 3 retries × 300s; 6 keys × 5 models would have been catastrophic). Probes: 8s timeout, 1 attempt, results cached 10 min.
- **Gemini keys are effectively dead NOW (verified Aug 2026), not just 'dying Sept'.** gemini-2.5-flash / gemini-2.5-flash-lite → HTTP 404 "no longer available to new users"; gemini-2.0-flash / gemini-2.5-pro → HTTP 429 quota exceeded; gemini-1.5-flash / gemini-3-flash → 404 not found. Don't hand-route agents to them; probe-then-drop handles it automatically.
- **24/7 is a hard requirement**: the daemon must keep running (background process + Startup-folder VBS persistence). "u not stop 24/7 continuous running" is the standing instruction.
- **DDG html endpoint is captcha-walled on this host (verified Aug 2026)**: `html.duckduckgo.com/html/?q=...` — the mission prompt's primary research trick — returns anomaly/captcha pages (grep the HTML for 'anomaly|captcha' → dozens of hits, zero `uddg` result links). Silent failure: fetch succeeds, results are empty. Always sanity-check fetched search HTML for result links. Working fallbacks: `https://r.jina.ai/<url>` reader proxy (worked for earn.superteam.fun, onlydust.com, immunefi.com/explore, layer3.xyz, gitcoin.co/mechanisms/bounties) and direct curl with a Chrome browser UA (worked for gitcoin.co).
- **git-bash `curl -o /tmp/...` silently writes nothing**: exit code 0 but the file never appears — MSYS /tmp mapping is unreliable on this host. Always write fetched research to local paths under the agent sandbox (`sandbox/<agent_id>/`), never /tmp.
- **AI-code flooding kills earning channels — quality over quantity is a survival law**: OnlyDust, which had distributed $18M to 4,000 open-source contributors over 4 years, shut down in 2026 — maintainers began rejecting money entirely after being flooded with low-skill AI-generated code ("Working alone was faster"). Swarm agents must deliver high-signal, human-verifiable work (clean PRs, real PoCs, proper docs); spraying low-effort AI output closes platforms for everyone.
- **Crypto-bounty channel statuses (verified Aug 8 2026)**: Immunefi (187 live programs, max bounties to $500k), Gitcoin bounties, Superteam Earn, Layer3 all LIVE; OnlyDust DEAD. W1-02's verified target analysis with payout/effort estimates is in `references/crypto-bounty-market-2026-08.md` — future crypto-bounty cycles should start from it instead of re-researching.

## Support files
- `references/survival-swarm-deployment.md` — full deployment detail: ledger schema, CFG values, hunting grounds, exact run/persistence commands, verified channel probes, ready-made ledger queries, creation log (Aug 8 2026) + next steps.
