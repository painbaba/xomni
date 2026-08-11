# perkline

PerkLine v2 — the researched "best model" status-line monetization engine:
tiered pricing, local relevance match, signed receipts, escrow caps.

**What it does:** tiered pricing (`cpm` $10–40/1k, `cpc` $1–8, `cpa`
$20–200); relevance match on local stack tags (extension scan only, 5-min
TTL cache — nothing leaves the machine); HMAC-SHA256 receipts per
render/engagement/action (`verify_receipt`); escrow-capped spend ≤ budget
(`escrow_invariant`, 50/50 split); second-price auction for the slot;
syncs counts + receipts only — never prompts/code/paths/tags.

**Commands:** `/perkline [status|engage [id]|complete <id>|pause|resume|
auction|sync]`

**Speed posture:** hooks `pre_llm_call` + `post_tool_call` (render
counting) and `on_session_end` (flush) — all return `None`; in-memory
counting, disk writes ≤1 per 30 s, stack walk cached 300 s. No LLM calls.

**Config:** `~/.perkline/config.json` — sponsors (id/message/url, model
cpm|cpc|cpa, price, budget, targeting), surface, sync_url, auction; state `~/.perkline/state.json` + `current.txt`.

```bash
cd plugins/perkline && python -m unittest tests.test_core -v
```
