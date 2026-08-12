"""XOMNI self-hosted marketplace — core (stdlib only, zero hooks).

The marketplace is the paid layer over the free skills registry
(docs/MARKETPLACE.md): listing, discovery, install, and the 15% take-rate
rail with UPI payout math. Every money-adjacent side-effect issues a
verifiable receipt whose id is the sha256 of the canonical JSON payload
(``json.dumps(dict, sort_keys=True)``).

Item shape::

    {'id', 'kind': 'skill'|'mcp'|'plugin', 'name', 'version', 'author',
     'description', 'price_inr': int, 'rails_pct': 0.15,
     'payin_method': 'upi', 'source', 'published_at', 'verified': bool}

Rails math (docs/MARKETPLACE.md §7.3): the take is rounded
(``round(price_inr * 0.15)``), the seller net is the residual
(``price_inr - rails_inr``) — the split always sums exactly to gross.

State files: ``state_dir/ledger.json`` — an append-only JSON list of
publish/sale events (sales are ``type == 'marketplace.sale'``).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

# Repo data catalog: <repo>/data/marketplace/catalog.json (seed catalog).
CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "marketplace" / "catalog.json"
# Local state: ledger of publish/sale events (tests patch both of these).
STATE_DIR = Path.home() / ".xomni-marketplace"

RAILS_PCT = 0.15
PAYIN_METHOD = "upi"
KINDS = ("skill", "mcp", "plugin")
_REQUIRED_ITEM_FIELDS = ("kind", "name", "price_inr")


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

def _canonical(payload):
    """Canonical JSON of a payload — the exact bytes the receipt hash covers."""
    return json.dumps(payload, sort_keys=True)


def _receipt_id(payload):
    """sha256 hex of the canonical JSON payload (handle kind ``sha256:<hex>``)."""
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def verify_receipt(receipt):
    """Recompute the sha256 over a receipt's payload fields and compare.

    Returns True iff ``receipt['receipt_id']`` equals the sha256 hex of the
    canonical JSON of every other field in the receipt. Any tampering with a
    payload field (price, buyer, ts, ...) breaks the match.
    """
    if not isinstance(receipt, dict) or "receipt_id" not in receipt:
        return False
    payload = {k: v for k, v in receipt.items() if k != "receipt_id"}
    try:
        return _receipt_id(payload) == receipt["receipt_id"]
    except (TypeError, ValueError):
        return False


def _now_iso():
    """UTC timestamp in the receipts-plugin style (``2026-08-12T14:02:11Z``)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Catalog I/O
# ---------------------------------------------------------------------------

def load_catalog(path=None):
    """Load the catalog list. Defaults to the module-level CATALOG_PATH.

    Fail-loud: a missing or unparseable catalog raises ValueError naming the
    cause — never silently returns an empty list.
    """
    p = Path(path) if path else CATALOG_PATH
    if not p.exists():
        raise ValueError(f"load_catalog failed: catalog file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"load_catalog failed: cannot parse catalog {p}: {e}") from e
    if isinstance(data, dict):
        data = data.get("items", data.get("catalog", []))
    if not isinstance(data, list):
        raise ValueError(
            f"load_catalog failed: {p} must contain a JSON list of items, "
            f"got {type(data).__name__}"
        )
    return data


def save_catalog(items, path=None):
    """Persist the catalog list. Defaults to the module-level CATALOG_PATH."""
    p = Path(path) if path else CATALOG_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(items, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as e:
        raise ValueError(f"save_catalog failed: cannot write catalog {p}: {e}") from e
    return p


# ---------------------------------------------------------------------------
# Search / discovery
# ---------------------------------------------------------------------------

def search(query="", kind=None, items=None):
    """Filter the catalog on query (name/description substring) and kind.

    ``items`` defaults to the loaded catalog (CATALOG_PATH). Query matching
    is case-insensitive; an empty query matches everything of the given kind.
    """
    catalog = items if items is not None else load_catalog()
    q = (query or "").strip().lower()
    out = []
    for item in catalog:
        if kind is not None and item.get("kind") != kind:
            continue
        if q:
            haystack = " ".join(
                str(item.get(field, "")) for field in ("name", "description")
            ).lower()
            if q not in haystack:
                continue
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

def _next_id(catalog):
    """Next auto id ``it-<n>`` = max existing numeric suffix + 1 (else len+1)."""
    nums = []
    for item in catalog:
        iid = item.get("id", "")
        if isinstance(iid, str) and iid.startswith("it-") and iid[3:].isdigit():
            nums.append(int(iid[3:]))
    return f"it-{max(nums) + 1 if nums else len(catalog) + 1}"


def publish(item, seller_id, state_dir=None):
    """Add an item to the catalog and return it plus a verifiable receipt.

    The item id is auto-assigned (``it-<n>``) and ``published_at`` is stamped
    once. A ``marketplace.publish`` event (with the same receipt id) is
    appended to ``state_dir/ledger.json`` for the audit trail. Fails loud
    (ValueError naming the cause) on invalid items.
    """
    sd = Path(state_dir) if state_dir else STATE_DIR
    if not seller_id:
        raise ValueError("publish failed: seller_id is required")
    missing = [k for k in _REQUIRED_ITEM_FIELDS if not item.get(k)]
    if missing:
        raise ValueError(
            f"publish failed: item missing required field(s): {', '.join(missing)}"
        )
    if item.get("kind") not in KINDS:
        raise ValueError(
            f"publish failed: kind must be one of {KINDS}, got {item.get('kind')!r}"
        )
    try:
        price = int(item["price_inr"])
    except (TypeError, ValueError) as e:
        raise ValueError(f"publish failed: price_inr must be an int, got {item['price_inr']!r}") from e
    if price <= 0:
        raise ValueError(f"publish failed: price_inr must be positive, got {price}")

    catalog = load_catalog()
    new_item = dict(item)
    new_item["id"] = _next_id(catalog)
    new_item["kind"] = item["kind"]
    new_item["price_inr"] = price
    new_item.setdefault("rails_pct", RAILS_PCT)
    new_item.setdefault("payin_method", PAYIN_METHOD)
    new_item.setdefault("verified", False)
    new_item.setdefault("version", "1.0.0")
    new_item.setdefault("author", seller_id)
    new_item.setdefault("description", "")
    new_item.setdefault("source", "")
    new_item["published_at"] = _now_iso()

    ts = new_item["published_at"]
    payload = {
        "type": "marketplace.publish",
        "item_id": new_item["id"],
        "seller_id": seller_id,
        "ts": ts,
    }
    rid = _receipt_id(payload)
    receipt = dict(payload)
    receipt["receipt_id"] = rid

    catalog.append(new_item)
    save_catalog(catalog)
    _append_ledger(sd, dict(payload, receipt_id=rid))
    return {"item": new_item, "receipt": receipt}


# ---------------------------------------------------------------------------
# Install (paid SKU purchase → sale)
# ---------------------------------------------------------------------------

def _rails_split(price_inr):
    """15% rails split on integer INR: take floored, net = residual.

    Exact integer math (``gross * 15 // 100``, no float): a ₹999 sale takes
    floor(149.85) = ₹149 and nets ₹850 — the M2 acceptance values. The split
    always sums exactly to gross and net can never exceed gross.
    """
    rails = price_inr * 15 // 100
    net = price_inr - rails
    return rails, net


def install(item_id, buyer_id, state_dir=None):
    """Record a paid install (sale) for ``item_id`` by ``buyer_id``.

    Fail-loud (ValueError) if the item is unknown or the buyer already owns
    it (double-claim prevention). On success appends a ``marketplace.sale``
    row to ``state_dir/ledger.json`` and returns
    ``{'sale': sale, 'receipt': receipt}`` where the receipt carries the
    rails math: ``rails_inr = round(price_inr * 0.15)`` and
    ``seller_net_inr = price_inr - rails_inr``.
    """
    sd = Path(state_dir) if state_dir else STATE_DIR
    if not buyer_id:
        raise ValueError("install failed: buyer_id is required")

    catalog = load_catalog()
    item = next((it for it in catalog if it.get("id") == item_id), None)
    if item is None:
        raise ValueError(f"install failed: no marketplace item with id {item_id!r} in catalog")

    ledger = _read_ledger(sd)
    duplicate = next(
        (
            s
            for s in ledger
            if s.get("type") == "marketplace.sale"
            and s.get("item_id") == item_id
            and s.get("buyer_id") == buyer_id
        ),
        None,
    )
    if duplicate is not None:
        raise ValueError(
            f"install failed: item {item_id!r} already installed by buyer {buyer_id!r} "
            "(double claim prevented — one sale per buyer per item)"
        )

    price = int(item["price_inr"])
    rails, net = _rails_split(price)
    ts = _now_iso()

    sale = {
        "type": "marketplace.sale",
        "item_id": item_id,
        "item_name": item.get("name"),
        "seller_id": item.get("author") or item.get("seller_id"),
        "buyer_id": buyer_id,
        "price_inr": price,
        "rails_inr": rails,
        "seller_net_inr": net,
        "payin_method": item.get("payin_method", PAYIN_METHOD),
        "ts": ts,
    }
    payload = {
        "type": "marketplace.sale",
        "item_id": item_id,
        "price_inr": price,
        "rails_inr": rails,
        "seller_net_inr": net,
        "payin_method": sale["payin_method"],
        "buyer_id": buyer_id,
        "ts": ts,
    }
    rid = _receipt_id(payload)
    receipt = dict(payload)
    receipt["receipt_id"] = rid
    sale["receipt_id"] = rid

    ledger.append(sale)
    _write_ledger(sd, ledger)
    return {"sale": sale, "receipt": receipt}


# ---------------------------------------------------------------------------
# Ledger + reports
# ---------------------------------------------------------------------------

def _ledger_path(sd):
    return Path(sd) / "ledger.json"


def _read_ledger(sd):
    p = _ledger_path(sd)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"ledger read failed: cannot parse {p}: {e}") from e
    if not isinstance(data, list):
        raise ValueError(
            f"ledger read failed: {p} must contain a JSON list, got {type(data).__name__}"
        )
    return data


def _write_ledger(sd, ledger):
    p = _ledger_path(sd)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as e:
        raise ValueError(f"ledger write failed: cannot write {p}: {e}") from e


def _append_ledger(sd, entry):
    ledger = _read_ledger(sd)
    ledger.append(entry)
    _write_ledger(sd, ledger)


def sales_ledger(state_dir=None):
    """List of sale records (type == 'marketplace.sale') from the ledger."""
    sd = Path(state_dir) if state_dir else STATE_DIR
    return [e for e in _read_ledger(sd) if e.get("type") == "marketplace.sale"]


def rails_report(state_dir=None):
    """Sum the rails math across all sales in the ledger.

    Returns ``{'gross_inr', 'rails_inr', 'seller_net_inr', 'sales_count'}``.
    Invariant: gross == rails + seller_net (the residual split, §7.3).
    """
    sales = sales_ledger(state_dir)
    return {
        "gross_inr": sum(int(s.get("price_inr", 0)) for s in sales),
        "rails_inr": sum(int(s.get("rails_inr", 0)) for s in sales),
        "seller_net_inr": sum(int(s.get("seller_net_inr", 0)) for s in sales),
        "sales_count": len(sales),
    }
