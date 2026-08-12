"""agent-economy — an agent-to-agent economy: service offers, trade lifecycle,
and verification receipts (pure stdlib, zero hooks).

Agents publish capability offers (``offer()``) that other agents request
(``request()``) as trades. A trade walks a strict lifecycle

    CREATED -> ACCEPTED -> FULFILLED -> SETTLED

and every illegal transition raises ``TradeError`` naming the violation.
Results are pinned with a sha256 digest (``result_sha256``) and every trade
yields a verifiable receipt (``build_receipt`` / ``verify_receipt``).

State lives in a state dir (default ``~/.xomni-economy``; override the
module-level ``core.STATE_DIR``) as ``offers.json`` + ``trades.json``.

No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

from . import core
from .core import (
    STATE_DIR,
    TradeError,
    accept,
    build_receipt,
    digest,
    fulfill,
    is_expired,
    ledger,
    offer,
    request,
    settle,
    verify_receipt,
    verify_trade,
)

HELP = (
    "/economy ledger        current trade ledger: total value + settled count\n"
    "/economy help          this help\n"
)


def _handle_economy(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    if cmd == "ledger":
        book = core.ledger()
        return "agent-economy ledger: %d trade(s), total value INR %d, settled %d" % (
            len(book["trades"]),
            book["total_value_inr"],
            book["settled_count"],
        )
    return HELP


def register(ctx) -> None:
    """Register the /economy command only — no hooks, zero per-turn cost."""
    ctx.register_command(
        "economy",
        handler=_handle_economy,
        description=(
            "Agent-to-agent economy: /economy ledger shows the trade ledger "
            "(trades, total value INR, settled count). Zero hooks."
        ),
        args_hint="[ledger]",
    )
