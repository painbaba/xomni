# XOMNI — Marketplace Live (M2 shipped)

**Status:** LIVE (2026-08-13) · **Plugin:** `plugins/marketplace` · **Spec:** docs/MARKETPLACE.md (P2-23) · **Backlog:** docs/BACKLOG.md P2-23 (M2)

What was built: a **self-hosted marketplace plugin** (stdlib only: `json`, `hashlib`, `time`, `pathlib`) with a seed catalog of 7 items (3 skills, 2 MCPs, 2 plugins) at `data/marketplace/catalog.json`, publish/install/search operations, the **15% rails take-rate + UPI payout math**, and a **verifiable sha256 receipt** for every side-effect. **Zero hooks** (new-plugin rule) — nothing on the agent hot path; cold import does no I/O.

## API (`plugins/marketplace/core.py`)

- `load_catalog(path=None)` / `save_catalog(items, path=None)` — catalog I/O; defaults to module-level `CATALOG_PATH` (repo `data/marketplace/catalog.json`).
- `search(query='', kind=None, items=None)` — filters on `name`/`description` (case-insensitive) and/or `kind` (`skill` | `mcp` | `plugin`).
- `publish(item, seller_id, state_dir=None)` — auto-id `it-<n>`, stamps `published_at` once, appends to catalog, records a `marketplace.publish` event in `state_dir/ledger.json`; returns `{'item', 'receipt'}`.
- `install(item_id, buyer_id, state_dir=None)` — records a `marketplace.sale` in `state_dir/ledger.json`; **double-claim prevention** (same buyer + item → `ValueError`); unknown id → `ValueError`; returns `{'sale', 'receipt'}`.
- `sales_ledger(state_dir=None)` / `rails_report(state_dir=None)` — sale rows / `{'gross_inr', 'rails_inr', 'seller_net_inr', 'sales_count'}`.
- `verify_receipt(receipt)` — recomputes sha256 over the canonical JSON (`json.dumps(dict, sort_keys=True)`) of all payload fields; `True` iff it matches `receipt['receipt_id']`.

Defaults: `CATALOG_PATH` and `STATE_DIR` (`~/.xomni-marketplace`) are module-level so tests patch them to temp dirs.

## 15% rails math (docs/MARKETPLACE.md §7)

Take-rate applies to gross; **UPI = 0% MDR default payin**. The take is floored (`gross × 15 // 100`, exact integer math — ₹999 → floor(149.85) = ₹149), seller net is the **residual** — the split always sums exactly to gross.

| price_inr | rails_inr | seller_net_inr |
|-----------|-----------|----------------|
| ₹100      | ₹15       | ₹85            |
| ₹500      | ₹75       | ₹425           |
| ₹999      | ₹149      | ₹850           |

Payout trigger stays ₹500 accrued via Razorpay Payouts (UPI, free); TDS rate remains flagged for CA review before first payout (docs/UPI.md §4).

## Receipt format

```
publish: {"receipt_id": sha256hex, "type": "marketplace.publish", "item_id": "it-8", "seller_id": "kulfi-labs", "ts": "2026-08-13T..."}
sale:    {"receipt_id": sha256hex, "type": "marketplace.sale", "item_id": "it-6", "price_inr": 999,
          "rails_inr": 149, "seller_net_inr": 850, "payin_method": "upi", "buyer_id": "dev-42", "ts": "2026-08-13T..."}
```

`verify_receipt` returns False if any payload field is flipped (price, buyer, ts, ...).

## Usage

```bash
cd plugins/marketplace && python -m unittest tests.test_core -q   # 13 tests, green
```

```python
from core import publish, install, search, rails_report, verify_receipt
pub = publish({"kind": "skill", "name": "x", "price_inr": 299, ...}, seller_id="kulfi-labs")
assert verify_receipt(pub["receipt"])
sale = install(pub["item"]["id"], buyer_id="dev-42")
assert sale["receipt"]["rails_inr"] == 44 and sale["receipt"]["seller_net_inr"] == 255
print(search("gst", kind="skill")); print(rails_report())
```

## Notes / deviations

- Receipt id = sha256 over the receipt payload fields (canonical JSON) — matches the `sha256:` handle kind of `plugins/receipts`; wire-in to the receipts JSONL ledger is a follow-up (out of M2 scope).
- `marketplace.publish` events also land in `state_dir/ledger.json` (audit trail); `sales_ledger`/`rails_report` filter `type == 'marketplace.sale'`.
- Money math is in integer INR per item (task spec); the spec's paise-level math (docs/MARKETPLACE.md §7.3) is preserved by construction at the anchored prices.
