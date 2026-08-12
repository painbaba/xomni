"""receipts — receipts-by-default: every external side-effect is backed by
proof, never claims.

A JSONL ledger at ``~/.xomni-receipts/receipts.jsonl`` records one receipt
per side-effect: ``{id, ts, action, target, result, handle, meta}`` where
``handle`` is the verifiable artifact — sha256 of the written file, the
returned URL (re-checked via HTTP 200), or exit code + output tail.
``verify()`` re-checks the handle and returns ``{ok, evidence}``.

Commands:
  /receipts                 last 10 receipts (newest first)
  /receipts show <id>       full receipt record
  /receipts verify <id>     re-check the verifiable handle -> {ok, evidence}
  /receipts audit           mutating-path coverage report: every mutating
                            command across CLI + plugins, and whether it
                            emits a receipt (grep-based, gaps loud)

The mutating paths that issue receipts: skill install (omni-skills +
`xomni skill install`), MCP catalog add / server install (mcp-catalog),
`xomni plugins install`, `xomni add <stack>`, `xomni providers add`,
`/skills publish`, `/skill save`, `/statusline on|off`. The receipts plugin
is optional at every site — if it is unavailable, those paths behave exactly
as before.

No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/receipts                last 10 receipts (newest first)\n"
    "/receipts show <id>      full receipt record\n"
    "/receipts verify <id>    re-check the verifiable handle -> {ok, evidence}\n"
    "/receipts audit          mutating-path coverage report (gaps loud)\n"
)


def _handle_receipts(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""
    if not cmd:
        return core.ledger_text(10)
    if cmd == "show":
        if not rest:
            return "usage: /receipts show <id>"
        try:
            return core.receipt_text(core.ReceiptLedger().get(rest))
        except core.ReceiptError as exc:
            return "/receipts show: %s" % exc
    if cmd == "verify":
        if not rest:
            return "usage: /receipts verify <id>"
        try:
            return core.verify_text(core.ReceiptLedger().verify(rest))
        except core.ReceiptError as exc:
            return "/receipts verify: %s" % exc
    if cmd == "audit":
        return core.audit_text(core.audit_coverage())
    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "receipts",
        handler=_handle_receipts,
        description=(
            "Receipts-by-default JSONL ledger: /receipts (last 10), "
            "/receipts show <id>, /receipts verify <id>, /receipts audit — "
            "every external side-effect carries a verifiable handle "
            "(sha256 / URL 200 / exit code); audit lists mutating-path coverage."
        ),
        args_hint="[show <id>|verify <id>|audit]",
    )
