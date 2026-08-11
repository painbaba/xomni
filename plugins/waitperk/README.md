# waitperk

WaitPerk-model sponsorship: **one sponsor line while the agent works**,
impression ledger, 50/50 impression-share payout math (PerkLine v2 in
`plugins/perkline` is the researched successor).

**What it does:** counts impressions per work event (LLM/tool call; paused
or >10-min idle gaps skipped); rotates sponsors per session; renders the
line to `~/.waitperk/current.txt` for external statuslines; earnings =
`0.5 × paid × share`, capped so payouts never exceed sponsor paid
(`payout_invariant`); syncs counts + session hash to `sync_url` (dry-run
when unset).

**Commands:** `/sponsor [status|pause|resume|sync|demo]`

**Speed posture:** hooks `on_session_start`/`end`, `pre_llm_call`,
`post_tool_call` — all return `None`, never alter behavior; in-memory
counting, disk writes ≤1 per 30 s + session end. No LLM calls/subprocess.

**Config:** `~/.waitperk/config.json` (sponsors, network_total_impressions,
sync_url, surface); state `~/.waitperk/state.json`, line `current.txt`.

```bash
cd plugins/waitperk && python -m unittest tests.test_core -v
```
