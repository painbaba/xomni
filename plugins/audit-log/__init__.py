"""audit-log — enterprise tamper-evident audit trail.

An append-only JSONL ledger at ``~/.xomni-audit/audit.jsonl`` (override
``XOMNI_AUDIT_FILE``) records one entry per auditable action:
``{id, ts, actor, action, target, result, prev_hash, hash}``. Every record's
``hash`` is the sha256 of the record (minus its own hash field) plus the
previous record's hash — a HASH CHAIN: editing or deleting any earlier
record breaks every later hash, so tampering is always detectable with
``/audit verify``.

Commands:
  /audit                last 25 entries (newest first)
  /audit show <id>      full audit record
  /audit verify         verify the tamper-evident hash chain -> {ok, first_bad_index}

No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/audit                last 25 audit entries (newest first)\n"
    "/audit show <id>      full audit record\n"
    "/audit verify         verify the tamper-evident hash chain\n"
)


def _handle_audit(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""
    if not cmd:
        return core.audit_text(25)
    if cmd == "show":
        if not rest:
            return "usage: /audit show <id>"
        try:
            return core.record_text(core.AuditLog().get(rest))
        except core.AuditError as exc:
            return "/audit show: %s" % exc
    if cmd == "verify":
        return core.verify_text(core.AuditLog().verify_chain())
    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "audit",
        handler=_handle_audit,
        description=(
            "Tamper-evident append-only audit trail (~/.xomni-audit/audit.jsonl): "
            "/audit (last 25), /audit show <id>, /audit verify — sha256 hash "
            "chain so any edit or deletion of a past record is detected."
        ),
        args_hint="[show <id>|verify]",
    )
