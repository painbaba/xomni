# agent-economy

An agent-to-agent economy plugin for XOMNI: **service offers/requests, a trade
lifecycle state machine, and verification receipts for every trade**.
Pure stdlib (`json`, `hashlib`, `time`, `pathlib`/`os`), **zero hooks**, cold
import well under 90 ms.

## Protocol

1. **Offer** — an agent publishes a capability:

   ```python
   off = offer("svc-doc-gen", "agent-alice", "generate-docx", price_inr=250,
               ttl_sec=3600, description="...")
   # {'offer_id': 'of-1', 'service_id': 'svc-doc-gen', 'agent_id': 'agent-alice',
   #  'capability': 'generate-docx', 'price_inr': 250, 'ttl_sec': 3600,
   #  'created_ts': 1750000000.0, ...}
   ```

   Offers carry a TTL (`created_ts + ttl_sec`); `is_expired(off)` checks it and
   `request()` on an expired offer raises `TradeError`.

2. **Request** — a buyer creates a trade:

   ```python
   tr = request(off["offer_id"], "agent-bob")
   # {'trade_id': 'tr-1', 'offer_id': 'of-1', 'buyer_id': 'agent-bob',
   #  'seller_id': 'agent-alice', 'state': 'CREATED', 'price_inr': 250,
   #  'result_sha256': None, 'payment_ref': None, ...}
   ```

## Trade lifecycle

```
CREATED ──accept (seller only)──▶ ACCEPTED ──fulfill──▶ FULFILLED ──settle──▶ SETTLED
```

| Transition | Function | Guard |
|---|---|---|
| `CREATED` -> `ACCEPTED` | `accept(trade_id, seller_id)` | only the offer's seller, only from `CREATED` |
| `ACCEPTED` -> `FULFILLED` | `fulfill(trade_id, result_payload)` | only from `ACCEPTED`; pins `result_sha256`; a second fulfill is a **double-claim** -> `TradeError` |
| `FULFILLED` -> `SETTLED` | `settle(trade_id, payment_ref)` | only from `FULFILLED`; records `payment_ref` |

Every illegal transition raises `TradeError` naming expected vs. actual state.
`verify_trade(trade, payload)` recomputes the digest and detects any tampering
of the result payload.

## Receipts

`build_receipt(trade)` returns a verifiable receipt:

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

`receipt_id` is the sha256 of the canonical JSON of all other fields —
`verify_receipt(receipt, trade)` recomputes it (and cross-checks it against a
fresh receipt rebuilt from the trade), so tampering any field is detected.

## Ledger

`ledger()` -> `{'trades': [...], 'total_value_inr': <int>, 'settled_count': <int>}`.
Command: `/economy ledger`.

## State & configuration

State persists in a state dir (default `~/.xomni-economy`) as `offers.json`
and `trades.json`; auto-incrementing ids (`of-1`, `tr-2`, ...) are derived
from the persisted records so they keep incrementing across file rewrites.
Override the module-level `core.STATE_DIR` (tests patch it to a temp dir) or
pass `state_dir=` to any function.

## Tests

```bash
cd plugins/agent-economy
python -m unittest tests.test_core -q
```
