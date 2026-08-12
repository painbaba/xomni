# perkline

PerkLine v2 — the researched "best model" status-line monetization engine:
tiered pricing, local relevance match, signed receipts, escrow caps.
**Sponsorship 2.0 (Monetization V2 P1):** contextual session slots + auction
floor + house campaigns (docs/MONETIZATION-V2.md §3.3).

**What it does:**

- **Tiered pricing** — `cpm` $10–40/1k, `cpc` $1–8, `cpa` $20–200.
- **Relevance match (v1)** — local stack tags (extension scan only, 5-min TTL
  cache — nothing leaves the machine).
- **Contextual slots (2.0 delta 2)** — sponsors may carry a `tags` list
  (e.g. `["codex"]`, `["media", "omni"]`) matched against a caller-supplied
  session-context string (`eligible_sponsors(led, repo_tags, context)` /
  `record_render(..., context=...)`). No tags = context-agnostic (v1
  behavior). Still local-only, still receipted — prompts/code are never read.
- **Auction floor + house campaigns (2.0 delta 1)** — `run_auction(led, bids,
  floor)` discards bids below the floor (CPM $10 min per slot-tier); the
  winner pays `max(second_price, floor)`. Unsold slots auto-fill with XOMNI's
  own house campaign (`house_campaigns` in config) at the floor price —
  impressions stay counted, dev earnings stay $0 for house fills, and the
  ledger stays honest. `floor` defaults to 0.0 = exact v1 behavior.
- **HMAC-SHA256 receipts** per render/engagement/action (`verify_receipt`);
  escrow-capped spend ≤ budget (`escrow_invariant`, 50/50 split);
  syncs counts + receipts only — never prompts/code/paths/tags.

**Commands:** `/perkline [status|engage [id]|complete <id>|pause|resume|
auction|sync]` — `/perkline auction` runs the second-price auction with the
configured `auction.floor`.

**Speed posture:** hooks `pre_llm_call` + `post_tool_call` (render counting)
and `on_session_end` (flush) — all return `None`; in-memory counting, disk
writes ≤1 per 30 s, stack walk cached 300 s. No LLM calls.

**Config:** `~/.perkline/config.json` — sponsors (id/message/url, model
cpm|cpc|cpa, price, budget, targeting, tags), house_campaigns, surface,
sync_url, auction (enabled/bids/floor); state `~/.perkline/state.json` +
`current.txt`.

```bash
cd plugins/perkline && python -m unittest tests.test_core -v
```
