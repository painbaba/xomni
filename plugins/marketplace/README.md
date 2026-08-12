# marketplace

The self-hosted marketplace layer for XOMNI (Monetization V2, M2; spec:
docs/MARKETPLACE.md). A catalog of skills / MCP servers / plugins with
Indian-market INR prices, the **15% rails take-rate** with UPI payout math,
publish/install/search operations, and a **verifiable sha256 receipt** for
every side-effect.

**Zero hooks.** This plugin registers no hooks (new-plugin rule) — nothing
sits on the agent hot path. Pure stdlib (`json`, `hashlib`, `time`,
`pathlib`); cold import does no I/O.

## What it does

- **Catalog** — a JSON list of items, seeded at `data/marketplace/catalog.json`
  (module-level `CATALOG_PATH`; `load_catalog(path=None)` /
  `save_catalog(items, path=None)`). Item shape:

  ```json
  {"id": "it-1", "kind": "skill", "name": "gst-receipt-parser",
   "version": "1.0.0", "author": "kulfi-labs", "description": "...",
   "price_inr": 799, "rails_pct": 0.15, "payin_method": "upi",
   "source": "kulfi-labs/xomni", "published_at": "2026-08-12T10:00:00Z",
   "verified": true}
  ```

- **Search** — `search(query='', kind=None, items=None)` filters on
  `name`/`description` (case-insensitive) and/or `kind`
  (`'skill' | 'mcp' | 'plugin'`).

- **Publish** — `publish(item, seller_id, state_dir=None)` auto-assigns the
  id (`it-<n>`, max suffix + 1), stamps `published_at` once, appends the item
  to the catalog, records a `marketplace.publish` event in
  `state_dir/ledger.json`, and returns
  `{'item': ..., 'receipt': {...}}` — the receipt is
  `{'receipt_id': sha256-hex, 'type': 'marketplace.publish', 'item_id',
  'seller_id', 'ts'}`.

- **Install (paid SKU)** — `install(item_id, buyer_id, state_dir=None)`
  records a sale in `state_dir/ledger.json` and returns
  `{'sale': ..., 'receipt': {...}}`. **Double-claim prevention:** the same
  buyer installing the same item twice raises `ValueError`. Unknown item id
  raises `ValueError`. The sale receipt carries the rails math:
  `{'receipt_id': sha256-hex, 'type': 'marketplace.sale', 'item_id',
  'price_inr', 'rails_inr', 'seller_net_inr', 'payin_method': 'upi',
  'buyer_id', 'ts'}`.

- **Reports** — `sales_ledger(state_dir=None)` lists sale rows;
  `rails_report(state_dir=None)` sums
  `{'gross_inr', 'rails_inr', 'seller_net_inr', 'sales_count'}`.

- **Verify** — `verify_receipt(receipt)` recomputes the sha256 over the
  canonical JSON (`json.dumps(dict, sort_keys=True)`) of every payload field
  and returns True iff it matches `receipt['receipt_id']`. Flipping any
  payload field (price, buyer, ts, ...) → False.

## The 15% rails math (docs/MARKETPLACE.md §7)

Take-rate applies to the gross sale price; **UPI is the default payin**
(0% MDR rail). The take is floored (`gross × 15 // 100`, exact integer math),
the seller net is the **residual** — the split always sums exactly to gross.

| price_inr | rails_inr (floor(price × 0.15)) | seller_net_inr (residual) |
|-----------|-------------------------------|---------------------------|
| ₹100      | ₹15                           | ₹85                       |
| ₹500      | ₹75                           | ₹425                      |
| ₹999      | ₹149                          | ₹850                      |

Payouts accrue in the earnings ledger; payout triggers at the ₹500 accrued
threshold via Razorpay Payouts (UPI, free) — TDS rate flagged for CA review
before first payout (docs/UPI.md §4).

## State files

- `state_dir/ledger.json` — append-only JSON list of `marketplace.publish`
  and `marketplace.sale` events (each carrying its `receipt_id`). Default
  `STATE_DIR = ~/.xomni-marketplace`; tests patch `CATALOG_PATH` /
  `STATE_DIR` to temp dirs.
- Catalog — repo `data/marketplace/catalog.json` (module-level
  `CATALOG_PATH`).

## Usage

```bash
cd plugins/marketplace && python -m unittest tests.test_core -q
```

```python
from core import publish, install, search, rails_report, verify_receipt

result = publish({
    "kind": "skill", "name": "test-case-farmer", "version": "1.0.0",
    "author": "kulfi-labs", "description": "writes unit tests from changelogs",
    "price_inr": 499, "source": "kulfi-labs/xomni", "verified": True,
}, seller_id="kulfi-labs")
assert verify_receipt(result["receipt"])          # sha256 recomputed → True

sale = install(result["item"]["id"], buyer_id="dev-42")
assert sale["receipt"]["rails_inr"] == 74 and sale["receipt"]["seller_net_inr"] == 425

print(search("gst", kind="skill"))
print(rails_report())  # {'gross_inr': ..., 'rails_inr': ..., 'seller_net_inr': ..., 'sales_count': ...}
```
