# Agent Economy (M4)

Agent-to-agent economy: service offers/requests, a trade lifecycle state
machine, and verification receipts for every trade. Pure stdlib, zero hooks.

## Protocol

1. `offer(service_id, agent_id, capability, price_inr, ttl_sec=3600, ...)`
   publishes a capability with a price (INR) and TTL. Auto id `of-<n>`.
2. `request(offer_id, buyer_id)` creates a trade (`tr-<n>`) in `CREATED`.
   Raises `TradeError` if the offer is unknown or expired
   (`created_ts + ttl_sec`; `is_expired(off, now=None)`).

## Lifecycle

```
CREATED ─accept (seller only)─▶ ACCEPTED ─fulfill─▶ FULFILLED ─settle─▶ SETTLED
```

| Function | Guard | Effect |
|---|---|---|
| `accept(trade_id, seller_id)` | only the offer's seller; only from `CREATED` | `state=ACCEPTED` |
| `fulfill(trade_id, payload)` | only from `ACCEPTED`; second fulfill = double-claim -> `TradeError` | `state=FULFILLED`, `result_sha256=sha256(canonical json)` |
| `settle(trade_id, payment_ref)` | only from `FULFILLED` | `state=SETTLED`, `payment_ref` set |

Every illegal transition raises `TradeError` naming expected vs. actual state.
`verify_trade(trade, payload)` recomputes the digest -> `bool`.

## Receipt format

```json
{
  "receipt_id": "<sha256 hex>",
  "type": "agent-economy.trade",
  "trade_id": "tr-1",
  "service_id": "svc-doc-gen",
  "buyer_id": "agent-bob",
  "seller_id": "agent-alice",
  "price_inr": 250,
  "result_sha256": "<sha256 hex>",
  "payment_ref": "pay-REF-1",
  "ts": 1750000001.0
}
```

`receipt_id` = sha256 of the canonical JSON of all other fields.
`verify_receipt(receipt, trade)` recomputes it and cross-checks against a
fresh receipt rebuilt from the trade -> any tamper returns `False`.

## Example

```python
off = offer("svc-doc-gen", "agent-alice", "generate-docx", 250)
tr  = request(off["offer_id"], "agent-bob")
accept(tr["trade_id"], "agent-alice")
ful  = fulfill(tr["trade_id"], {"doc": "hello"})       # pins result_sha256
st   = settle(tr["trade_id"], "pay-REF-1")             # SETTLED
assert verify_trade(st, {"doc": "hello"})
r = build_receipt(st)
assert verify_receipt(r, st)
ledger()  # {'trades': [...], 'total_value_inr': 250, 'settled_count': 1}
```

State persists in a state dir (default `~/.xomni-economy`) as
`offers.json` + `trades.json`; auto ids derive from persisted records so they
keep incrementing across file rewrites. Tests patch `core.STATE_DIR` to a
temp dir. Verify: `python -m unittest tests.test_core -q` from the plugin dir.
