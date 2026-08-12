"""audit-log core — tamper-evident append-only audit trail (pure stdlib, zero hooks).

Enterprise compliance demands an audit trail that cannot be silently rewritten.
Every auditable action is appended to a JSONL ledger at
``~/.xomni-audit/audit.jsonl`` (override ``XOMNI_AUDIT_FILE``) as one record:

    {id, ts, actor, action, target, result, meta, prev_hash, hash}

``hash`` is the sha256 of the record's canonical JSON (with its own ``hash``
field removed) concatenated with the previous record's ``hash`` — a HASH
CHAIN. Editing or deleting any earlier record invalidates the hash of that
record and therefore every later record's ``prev_hash`` link, so tampering is
always detectable via ``verify_chain()``.

Append-only by construction: records are only ever written with
``open(path, "a")``; this module has no update or delete path.

Corrupt/torn JSONL lines are skipped (counted via ``corrupt_count()``), so a
torn append never raises and never breaks the ledger. All read-only helpers
(``query`` / ``verify_chain`` / ``corrupt_count`` / ``count`` / ``get``)
never raise.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone

DEFAULT_LEDGER_DIR = os.path.expanduser("~/.xomni-audit")
DEFAULT_LEDGER_PATH = os.path.join(DEFAULT_LEDGER_DIR, "audit.jsonl")


class AuditError(Exception):
    """Loud failure: missing record, unreadable ledger (write-side)."""


def ledger_path() -> str:
    """Ledger file path — ``XOMNI_AUDIT_FILE`` override, else the default."""
    return os.environ.get("XOMNI_AUDIT_FILE") or DEFAULT_LEDGER_PATH


# ─── hash chain ──────────────────────────────────────────────────────────────

def chain_hash(record: dict) -> str:
    """sha256 of (canonical JSON of the record minus its own ``hash`` field
    + the previous record's hash). Deterministic: ``json.dumps`` with sorted
    keys and compact separators, so re-derivation always matches."""
    rec = {k: v for k, v in record.items() if k != "hash"}
    canonical = json.dumps(rec, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    prev = record.get("prev_hash") or ""
    return hashlib.sha256((canonical + prev).encode("utf-8")).hexdigest()


# ─── ledger ──────────────────────────────────────────────────────────────────

class AuditLog:
    """Append-only, tamper-evident JSONL audit ledger."""

    def __init__(self, path: str | None = None):
        self.path = path or ledger_path()

    # write ----------------------------------------------------------------
    def append(self, actor: str, action: str, target: str,
               result: str | None = None, meta: dict | None = None) -> dict:
        """Append one audit record -> the record dict (also the JSONL line).

        ``actor`` is the identity of the acting principal (SSO subject / role
        for enterprise deployments), ``action`` the operation, ``target`` the
        object, ``result`` the outcome, ``meta`` optional structured detail.
        """
        prev = self._tail_hash()
        record = {
            "id": "A%x-%s" % (int(time.time() * 1000), uuid.uuid4().hex[:6]),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "actor": actor,
            "action": action,
            "target": target,
            "result": result if result is not None else "",
            "meta": meta or {},
            "prev_hash": prev,
            "hash": "",
        }
        record["hash"] = chain_hash(record)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return record

    # read (never raise) ---------------------------------------------------
    def _read(self) -> tuple[list[dict], int]:
        """(records, corrupt_lines) — corrupt/torn lines are skipped, never fatal."""
        records, corrupt = [], 0
        if not os.path.isfile(self.path):
            return records, corrupt
        try:
            fh = open(self.path, encoding="utf-8", errors="replace")
        except OSError:
            return records, corrupt
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    corrupt += 1
                    continue
                if isinstance(rec, dict) and rec.get("id"):
                    records.append(rec)
                else:
                    corrupt += 1
        return records, corrupt

    def _tail_hash(self) -> str:
        """Hash of the last well-formed record — chain link for the next append."""
        records, _ = self._read()
        if not records:
            return ""
        return records[-1].get("hash") or ""

    def query(self, actor: str | None = None, action: str | None = None,
              limit: int = 50) -> list[dict]:
        """Newest-first records, optionally filtered by actor/action, capped
        at *limit* (no cap when limit is None or <= 0). Never raises."""
        records, _ = self._read()
        if actor is not None:
            records = [r for r in records if r.get("actor") == actor]
        if action is not None:
            records = [r for r in records if r.get("action") == action]
        if limit and limit > 0:
            records = records[-limit:]
        return records[::-1]

    def get(self, record_id: str) -> dict:
        """Fetch one record by id — loud AuditError when missing."""
        records, _ = self._read()
        for rec in reversed(records):
            if rec.get("id") == record_id:
                return rec
        raise AuditError("audit record not found: %r (ledger: %s)"
                         % (record_id, self.path))

    def count(self) -> int:
        records, _ = self._read()
        return len(records)

    def corrupt_count(self) -> int:
        _, corrupt = self._read()
        return corrupt

    # integrity ------------------------------------------------------------
    def verify_chain(self) -> tuple[bool, int | None]:
        """Re-derive the hash chain -> ``(ok, first_bad_index)``.

        Returns ``(True, None)`` on an intact (or empty) chain; otherwise
        ``(False, i)`` where ``i`` is the 0-based index of the first record
        whose stored hash or ``prev_hash`` link no longer matches — i.e. the
        earliest tampered, deleted, or malformed record. Never raises.
        """
        records, _ = self._read()
        prev = ""
        for i, rec in enumerate(records):
            if not all(k in rec for k in
                       ("id", "ts", "actor", "action", "target",
                        "result", "prev_hash", "hash")):
                return False, i
            if (rec.get("prev_hash") or "") != prev:
                return False, i
            if rec.get("hash") != chain_hash(rec):
                return False, i
            prev = rec.get("hash") or ""
        return True, None


# ─── text renderers (used by /audit) ─────────────────────────────────────────

def audit_text(limit: int = 25, path: str | None = None) -> str:
    log = AuditLog(path)
    recs = log.query(limit=limit)
    if not recs:
        return "no audit entries yet (ledger: %s)" % log.path
    ok, bad = log.verify_chain()
    status = "CHAIN OK" if ok else "CHAIN BROKEN at record %d" % bad
    lines = ["AUDIT — %d total (last %d), %s, ledger: %s"
             % (log.count(), len(recs), status, log.path)]
    for r in recs:
        lines.append("  %s  %s  %-20s %-22s %s"
                     % (r["id"], r["ts"], r["actor"], r["action"],
                        str(r["result"])[:48]))
    lines.append("verify: /audit verify   show: /audit show <id>")
    return "\n".join(lines)


def record_text(record: dict) -> str:
    return "\n".join("%s: %s" % (k, json.dumps(v, ensure_ascii=False)
                                 if isinstance(v, (dict, list)) else v)
                     for k, v in record.items())


def verify_text(result: tuple[bool, int | None]) -> str:
    ok, bad = result
    if ok:
        return "AUDIT CHAIN VERIFY OK — every record re-hashes from genesis"
    return ("AUDIT CHAIN BROKEN at index %d — earlier record was tampered "
            "with, deleted, or malformed" % bad)
