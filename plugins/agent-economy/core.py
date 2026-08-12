"""agent-economy core — an agent-to-agent economy (pure stdlib, zero hooks).

Agents publish service offers (``offer``) with a price in INR and a TTL;
buyers request them (``request``) which creates a trade in ``CREATED`` state.
A trade then walks a strict lifecycle enforced by a state machine:

    CREATED -> ACCEPTED -> FULFILLED -> SETTLED

* ``accept``  — only the offer's seller may accept, only from ``CREATED``.
* ``fulfill`` — only from ``ACCEPTED``; pins ``result_sha256`` = sha256 of the
  canonical JSON of the result payload; a second fulfill is a double-claim
  and raises ``TradeError``.
* ``settle``  — only from ``FULFILLED``; records the ``payment_ref``.

Every illegal transition raises ``TradeError`` naming the expected vs. actual
state. Results are tamper-checkable via ``verify_trade``, and every trade has
a verifiable receipt (``build_receipt`` / ``verify_receipt``) whose
``receipt_id`` is the sha256 of the receipt's payload fields.

Persistence: a state dir containing ``offers.json`` and ``trades.json``
(default ``~/.xomni-economy``; override the module-level ``STATE_DIR``, which
tests patch to a temp dir). Ids are auto-incrementing (``of-1``, ``tr-2``,
...) and always derived from the persisted records, so they keep incrementing
across file rewrites.

Fail-loud: any misuse raises ``TradeError`` with a message naming the
violation. No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

DEFAULT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".xomni-economy")

# Module-level state dir; tests patch this to a temp dir.
STATE_DIR = DEFAULT_STATE_DIR

TRADE_STATES = ("CREATED", "ACCEPTED", "FULFILLED", "SETTLED")

_RECEIPT_TYPE = "agent-economy.trade"


class TradeError(Exception):
    """Loud failure: illegal transition, unknown id, expired offer, ..."""


# ─── persistence ─────────────────────────────────────────────────────────────

def _dir(state_dir: str | None) -> str:
    return state_dir or STATE_DIR


def _offers_path(state_dir: str | None) -> str:
    return os.path.join(_dir(state_dir), "offers.json")


def _trades_path(state_dir: str | None) -> str:
    return os.path.join(_dir(state_dir), "trades.json")


def _load(path: str) -> list:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def _save(path: str, records: list) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())


def _next_id(records: list, prefix: str, field: str) -> str:
    """Auto-incrementing id: max existing numeric suffix + 1 (e.g. ``of-3``)."""
    n = 0
    for rec in records:
        rid = str(rec.get(field, ""))
        if rid.startswith(prefix + "-"):
            try:
                n = max(n, int(rid[len(prefix) + 1:]))
            except ValueError:
                pass
    return "%s-%d" % (prefix, n + 1)


# ─── offers ──────────────────────────────────────────────────────────────────

def offer(service_id: str, agent_id: str, capability: str, price_inr: int,
          ttl_sec: int = 3600, description: str | None = None,
          state_dir: str | None = None) -> dict:
    """Publish a service offer -> offer dict (auto id ``of-<n>``)."""
    if not isinstance(price_inr, int) or isinstance(price_inr, bool) or price_inr < 0:
        raise TradeError("offer: price_inr must be a non-negative int, got %r"
                         % (price_inr,))
    records = _load(_offers_path(state_dir))
    off = {
        "offer_id": _next_id(records, "of", "offer_id"),
        "service_id": service_id,
        "agent_id": agent_id,
        "capability": capability,
        "description": description or "",
        "price_inr": int(price_inr),
        "ttl_sec": int(ttl_sec),
        "created_ts": time.time(),
    }
    records.append(off)
    _save(_offers_path(state_dir), records)
    return off


def is_expired(offer_dict: dict, now: float | None = None) -> bool:
    """True when ``now >= created_ts + ttl_sec``."""
    now = time.time() if now is None else now
    return now >= (offer_dict["created_ts"] + offer_dict["ttl_sec"])


def _get_offer(offer_id: str, state_dir: str | None) -> dict:
    for off in _load(_offers_path(state_dir)):
        if off.get("offer_id") == offer_id:
            return off
    raise TradeError("offer %s not found in %s"
                     % (offer_id, _offers_path(state_dir)))


# ─── trades ──────────────────────────────────────────────────────────────────

def request(offer_id: str, buyer_id: str, state_dir: str | None = None) -> dict:
    """Request a service offer -> new trade in ``CREATED`` (auto id ``tr-<n>``).

    Raises ``TradeError`` if the offer is unknown or expired.
    """
    off = _get_offer(offer_id, state_dir)
    if is_expired(off):
        raise TradeError("offer %s expired at ts %.3f — request rejected"
                         % (offer_id, off["created_ts"] + off["ttl_sec"]))
    records = _load(_trades_path(state_dir))
    now = time.time()
    trade = {
        "trade_id": _next_id(records, "tr", "trade_id"),
        "offer_id": offer_id,
        "buyer_id": buyer_id,
        "seller_id": off["agent_id"],
        "state": "CREATED",
        "price_inr": off["price_inr"],
        "result_sha256": None,
        "payment_ref": None,
        "created_ts": now,
        "updated_ts": now,
    }
    records.append(trade)
    _save(_trades_path(state_dir), records)
    return trade


def _require_state(trade: dict, expected: str, action: str) -> None:
    actual = trade["state"]
    if actual != expected:
        raise TradeError(
            "trade %s: %s requires state %s, actual %s (illegal transition)"
            % (trade["trade_id"], action, expected, actual))


def _update_trade(trade_id: str, mutate, state_dir: str | None) -> dict:
    records = _load(_trades_path(state_dir))
    for trade in records:
        if trade.get("trade_id") == trade_id:
            mutate(trade)
            trade["updated_ts"] = time.time()
            _save(_trades_path(state_dir), records)
            return trade
    raise TradeError("trade %s not found in %s"
                     % (trade_id, _trades_path(state_dir)))


def accept(trade_id: str, seller_id: str, state_dir: str | None = None) -> dict:
    """Accept a trade -> ``ACCEPTED``. Only the offer's seller, only from CREATED."""
    def mutate(trade: dict) -> None:
        if trade["seller_id"] != seller_id:
            raise TradeError(
                "trade %s: accept by %s denied — only seller %s may accept"
                % (trade_id, seller_id, trade["seller_id"]))
        _require_state(trade, "CREATED", "accept")
        trade["state"] = "ACCEPTED"
    return _update_trade(trade_id, mutate, state_dir)


def fulfill(trade_id: str, result_payload, state_dir: str | None = None) -> dict:
    """Fulfill a trade -> ``FULFILLED``, pinning ``result_sha256``.

    Only from ``ACCEPTED``; a second fulfill raises ``TradeError``
    ("already fulfilled") — double-claim prevention.
    """
    def mutate(trade: dict) -> None:
        if trade["state"] == "FULFILLED":
            raise TradeError("trade %s already fulfilled — double-claim prevented"
                             % trade_id)
        _require_state(trade, "ACCEPTED", "fulfill")
        trade["state"] = "FULFILLED"
        trade["result_sha256"] = digest(result_payload)
    return _update_trade(trade_id, mutate, state_dir)


def settle(trade_id: str, payment_ref: str, state_dir: str | None = None) -> dict:
    """Settle a fulfilled trade -> ``SETTLED``, recording ``payment_ref``."""
    def mutate(trade: dict) -> None:
        _require_state(trade, "FULFILLED", "settle")
        trade["state"] = "SETTLED"
        trade["payment_ref"] = payment_ref
    return _update_trade(trade_id, mutate, state_dir)


# ─── verification ────────────────────────────────────────────────────────────

def digest(payload) -> str:
    """sha256 hex of the canonical JSON of ``payload`` (sorted keys)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_trade(trade: dict, result_payload) -> bool:
    """Recompute the result digest and compare with ``result_sha256``."""
    expected = trade.get("result_sha256")
    if not expected:
        return False
    return digest(result_payload) == expected


# ─── receipts ────────────────────────────────────────────────────────────────

def build_receipt(trade: dict, state_dir: str | None = None) -> dict:
    """Build a verifiable receipt for a trade.

    ``receipt_id`` = sha256 of the canonical JSON of every other receipt
    field, so any tamper with the payload fields is detectable.
    """
    try:
        service_id = _get_offer(trade["offer_id"], state_dir)["service_id"]
    except TradeError:
        service_id = ""
    payload = {
        "type": _RECEIPT_TYPE,
        "trade_id": trade["trade_id"],
        "service_id": service_id,
        "buyer_id": trade["buyer_id"],
        "seller_id": trade["seller_id"],
        "price_inr": trade["price_inr"],
        "result_sha256": trade.get("result_sha256"),
        "payment_ref": trade.get("payment_ref"),
        "ts": trade.get("updated_ts") or trade.get("created_ts"),
    }
    receipt = dict(payload)
    receipt["receipt_id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()
    return receipt


def verify_receipt(receipt: dict, trade: dict, state_dir: str | None = None) -> bool:
    """True iff the receipt's own payload fields hash to its ``receipt_id``
    AND that id matches a freshly rebuilt receipt for ``trade``."""
    if not isinstance(receipt, dict) or receipt.get("type") != _RECEIPT_TYPE:
        return False
    if receipt.get("trade_id") != trade.get("trade_id"):
        return False
    payload = {k: v for k, v in receipt.items() if k != "receipt_id"}
    recomputed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()
    if recomputed != receipt.get("receipt_id"):
        return False
    rebuilt = build_receipt(trade, state_dir)
    return receipt.get("receipt_id") == rebuilt["receipt_id"]


# ─── ledger ──────────────────────────────────────────────────────────────────

def ledger(state_dir: str | None = None) -> dict:
    """Ledger summary: all trades, total value in INR, settled count."""
    trades = _load(_trades_path(state_dir))
    return {
        "trades": trades,
        "total_value_inr": sum(int(t.get("price_inr") or 0) for t in trades),
        "settled_count": sum(1 for t in trades if t.get("state") == "SETTLED"),
    }
