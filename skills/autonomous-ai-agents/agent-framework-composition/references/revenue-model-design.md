# Revenue-model design for terminal/status-line monetization (WaitPerk → PerkLine v2)

Condensed research + design from the unified-agent session. Reuse for any
"monetize the agent UI / sponsor module" work.

## WaitPerk model (the baseline, CPM-impression)

- One sponsor line in the Claude Code status bar; impressions counted while the
  line is on screen; 50/50 split of sponsor payment "by impression share";
  payouts capped at what sponsors paid "by construction".
- Client claims: touches only ~/.claude/settings.json + ~/.waitperk, syncs only
  impression IDs + session hash, Ed25519-signed updates, audit repo, PolyForm
  Shield license (source-available, not OSI).

### Why it's weak (the three structural flaws PerkLine fixes)

1. **Glance value**: impressions are the weakest ad signal. A terminal status
   line is unverifiable, auto-rendered, skimmable inventory — advertisers pay
   for outcomes, not glances.
2. **Untargeted inventory**: with no targeting, the line is worth ~nothing;
   relevance lifts value 2-5x in ad markets.
3. **Unverifiable numbers**: "live numbers, zeros included" is a transparency
   claim with no proof mechanism; the network total (denominator of the share)
   is server-side and uncheckable.

## PerkLine v2 — the researched upgrade

Fixes all three while keeping the one good invariant (payouts never exceed what
sponsors paid). Design elements:

| Tier | Price (benchmark ranges) | Charged when |
|---|---|---|
| cpm | $10-40 per 1000 renders | line rendered for a work event |
| cpc | $1-8 per engagement | dev activates the line (/perkline engage) |
| cpa | $20-200 per completed action | dev confirms real completion |

- **Local relevance matching**: sponsors declare targeting stack tags
  (python/node/go/rust/...); the client scans the LOCAL repo's file extensions
  and only renders matching sponsors. Only matched sponsor IDs + receipts leave
  the machine — repo tags never do. Empty targeting = everyone.
- **Verifiable delivery**: every render/engagement/action carries an
  HMAC-SHA256 receipt over (nonce|sponsor_id|event|ts|surface), keyed with an
  install secret — a sponsor network can verify each delivery without a shared
  ledger. `verify_receipt(receipt, secret)` with `hmac.compare_digest`.
- **Escrow caps**: per-sponsor `budget`; sponsor spend = min(amount, budget -
  spent); dev earnings = 0.5 × sponsor spend. Dev can never earn more than half
  the budget; sponsor never pays more than budget. Sum over devs ≤ P always.
- **Second-price auction** for the slot: highest bid wins, pays second-highest
  (honest price discovery).
- **Privacy payload shape**: sync sends renders/engagements/actions counts,
  receipts (ring buffer, capped), surface, client version, sha256(device_id)
  session hash. NEVER prompts, code, file paths, or stack tags.

## Implementation notes (learned the hard way)

- Pure core (no host imports) + wiring split: core.py unit-testable in
  isolation; hooks (`pre_llm_call`/`post_tool_call`) count work events and MUST
  return None (never alter agent behavior). `on_session_start/end` open/close
  ledger windows.
- Impression proxy: one agent work event = one render unit (no background timer
  needed); ignore event gaps >10 min as idle.
- **Escrow math bug class**: tracking the DEV SHARE in the escrow ledger (not
  sponsor spend) double-applies the 50/50 — escrow must track sponsor-side
  spend, earnings = 0.5 × capped spend.
- **Engagement semantics**: only the sponsor currently ON SCREEN can be engaged
  (no re-filtering by targeting at click time).
- **Shared-mutable-default bug**: `dict(DEFAULT_STATE)` shallow copy → nested
  dicts shared across instances → test-order-dependent failures. Use
  `copy.deepcopy` in `__init__`/`default_factory`.
- Statusline adaptation when the host has no statusLine surface: write the
  current sponsor line to `~/.perkline/current.txt` for external tails (tmux,
  terminal title, shell prompt).
- Demo mode: empty `sync_url` = dry-run sync printing the exact payload;
  simulated network totals make earnings computable before any sponsor exists.
  CPA completions are user-confirmed locally; production needs a sponsor-side
  verification callback.
