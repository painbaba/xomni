"""receipts core — receipts-by-default JSONL ledger (pure stdlib, zero hooks).

Owner demand: *receipts by default* — every external side-effect (HTTP POST,
file write, deploy) automatically returns a verifiable handle, so "it works"
is always backed by proof, never claims. This module provides:

  - ``ReceiptLedger``: an append-only JSONL ledger at
    ``~/.xomni-receipts/receipts.jsonl`` (override ``XOMNI_RECEIPTS_FILE``).
    ``issue()`` appends ``{id, ts, action, target, result, handle, meta}``;
    ``verify()`` re-checks the handle and returns ``{ok, evidence}``.
  - Three verifiable handle kinds:
      * ``sha256:<hex>``      — sha256 of the target file (exists + hash match)
      * ``url:<url>``         — the URL returns HTTP 200 (live GET re-check)
      * ``exit:<code>:<tail>`` — exit code + output tail (recheckable when
                                ``meta['command']`` is recorded)
  - Never-raising helpers (``try_issue`` / ``try_file_receipt`` /
    ``try_url_receipt`` / ``try_exit_receipt``) for integration sites: the
    receipts plugin is optional — if the ledger cannot be written the caller
    behaves exactly as before.

Corrupt JSONL lines are skipped (counted via ``corrupt_count()``) — a torn
append never breaks the ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

DEFAULT_LEDGER_DIR = os.path.expanduser("~/.xomni-receipts")
DEFAULT_LEDGER_PATH = os.path.join(DEFAULT_LEDGER_DIR, "receipts.jsonl")
URL_TIMEOUT = 10          # seconds for url-handle verification
EXIT_RECHECK_TIMEOUT = 60  # seconds for exit-handle command re-runs
TAIL_LEN = 300            # output tail kept in exit handles


class ReceiptError(Exception):
    """Loud failure: missing receipt, malformed handle, unreadable ledger."""


def ledger_path() -> str:
    """Ledger file path — ``XOMNI_RECEIPTS_FILE`` override, else the default."""
    return os.environ.get("XOMNI_RECEIPTS_FILE") or DEFAULT_LEDGER_PATH


# ─── handle builders ─────────────────────────────────────────────────────────

def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    """sha256 hex of a file's bytes, as a ``sha256:<hex>`` handle."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return "sha256:" + h.hexdigest()


def file_handle(path: str) -> str:
    """Verifiable handle for a written file (sha256 of its bytes)."""
    return sha256_file(path)


def url_handle(url: str) -> str:
    """Verifiable handle for a returned URL — ``url:<url>`` (verify re-checks HTTP 200)."""
    return "url:" + url


def exit_handle(code: int, tail: str = "") -> str:
    """Verifiable handle for a command run — ``exit:<code>:<quoted tail>``."""
    return "exit:%d:%s" % (int(code), urllib.parse.quote((tail or "")[-TAIL_LEN:], safe=""))


def parse_handle(handle: str) -> dict:
    """Split a handle into ``{kind, ...}``. Raises ReceiptError when malformed."""
    if not isinstance(handle, str) or not handle:
        raise ReceiptError("empty handle")
    if handle.startswith("sha256:"):
        digest = handle[len("sha256:"):].lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ReceiptError("malformed sha256 handle: %r" % handle)
        return {"kind": "sha256", "digest": digest}
    if handle.startswith("url:"):
        url = handle[len("url:"):]
        if not url.startswith(("http://", "https://")):
            raise ReceiptError("malformed url handle: %r" % handle)
        return {"kind": "url", "url": url}
    if handle.startswith("exit:"):
        rest = handle[len("exit:"):]
        code_s, _, tail_q = rest.partition(":")
        try:
            code = int(code_s)
        except ValueError:
            raise ReceiptError("malformed exit handle: %r" % handle)
        return {"kind": "exit", "code": code, "tail": urllib.parse.unquote(tail_q)}
    raise ReceiptError("unknown handle kind: %r" % handle)


# ─── handle verification ─────────────────────────────────────────────────────

def _verify_sha256(target: str, digest: str) -> dict:
    if not target or not os.path.isfile(target):
        return {"ok": False, "evidence": {"kind": "sha256",
                                          "error": "file missing: %s" % target}}
    try:
        actual = sha256_file(target).split(":", 1)[1]
    except OSError as exc:
        return {"ok": False, "evidence": {"kind": "sha256", "error": str(exc)}}
    return {"ok": actual == digest,
            "evidence": {"kind": "sha256", "path": target,
                         "expected": digest, "actual": actual}}


def _verify_url(url: str, timeout: int = URL_TIMEOUT) -> dict:
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "xomni-receipts/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            return {"ok": status == 200,
                    "evidence": {"kind": "url", "url": url, "status": status}}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "evidence": {"kind": "url", "url": url,
                                          "status": exc.code, "error": str(exc)}}
    except Exception as exc:
        return {"ok": False, "evidence": {"kind": "url", "url": url,
                                          "error": str(exc)}}


def _verify_exit(code: int, tail: str, meta: dict) -> dict:
    """Exit-code handle: the code + tail are the recorded proof; the handle is
    recheckable when the issuing command was recorded in ``meta['command']``
    (re-run with ``verify(..., recheck_exit=True)``)."""
    command = (meta or {}).get("command") if isinstance(meta, dict) else None
    return {"ok": True,
            "evidence": {"kind": "exit", "code": code, "tail": tail,
                         "recheckable": bool(command)}}


def _recheck_exit(expected_code: int, meta: dict,
                  timeout: int = EXIT_RECHECK_TIMEOUT) -> dict:
    """Re-run the recorded command and compare its exit code."""
    command = (meta or {}).get("command") if isinstance(meta, dict) else None
    if not command:
        return {"ok": True, "evidence": {"kind": "exit", "code": expected_code,
                                         "error": "no meta['command'] recorded to re-run"}}
    argv = command if isinstance(command, (list, tuple)) else shlex.split(command)
    try:
        proc = subprocess.run(argv, shell=False, capture_output=True,
                              text=True, timeout=timeout)
        actual = proc.returncode
        tail = ((proc.stdout or "") + (proc.stderr or "")).strip()[-TAIL_LEN:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "evidence": {"kind": "exit",
                                          "expected": expected_code,
                                          "error": "re-run failed: %s" % exc}}
    return {"ok": actual == expected_code,
            "evidence": {"kind": "exit", "expected": expected_code,
                         "actual": actual, "tail": tail}}


# ─── ledger ──────────────────────────────────────────────────────────────────

class ReceiptLedger:
    """Append-only JSONL ledger of verifiable receipts."""

    def __init__(self, path: str | None = None):
        self.path = path or ledger_path()

    # write ----------------------------------------------------------------
    def issue(self, action: str, target: str, result: str, handle: str,
              meta: dict | None = None) -> dict:
        """Record one side-effect -> receipt dict (also the JSONL line)."""
        receipt = {
            "id": "R%x-%s" % (int(time.time() * 1000), uuid.uuid4().hex[:6]),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "action": action,
            "target": target,
            "result": result,
            "handle": handle,
            "meta": meta or {},
        }
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return receipt

    # read -----------------------------------------------------------------
    def _read(self) -> tuple[list[dict], int]:
        """(records, corrupt_lines) — corrupt/torn lines are skipped, never fatal."""
        records, corrupt = [], 0
        if not os.path.isfile(self.path):
            return records, corrupt
        with open(self.path, encoding="utf-8", errors="replace") as f:
            for line in f:
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

    def get(self, receipt_id: str) -> dict:
        """Fetch one receipt by id — loud ReceiptError when missing."""
        records, _ = self._read()
        for rec in reversed(records):
            if rec.get("id") == receipt_id:
                return rec
        raise ReceiptError("receipt not found: %r (ledger: %s)"
                           % (receipt_id, self.path))

    def recent(self, limit: int = 10) -> list[dict]:
        """Newest-first receipts, capped at *limit*."""
        records, _ = self._read()
        return records[-limit:][::-1]

    def count(self) -> int:
        records, _ = self._read()
        return len(records)

    def corrupt_count(self) -> int:
        _, corrupt = self._read()
        return corrupt

    # verify ---------------------------------------------------------------
    def verify(self, receipt_id: str, recheck_exit: bool = False) -> dict:
        """Re-check the receipt's verifiable handle -> {ok, evidence, receipt_id}.

        Raises ReceiptError when the receipt id is unknown (loud, never silent).
        """
        rec = self.get(receipt_id)
        try:
            parsed = parse_handle(rec.get("handle"))
        except ReceiptError as exc:
            return {"ok": False, "receipt_id": receipt_id,
                    "evidence": {"kind": "handle", "error": str(exc)}}
        kind = parsed["kind"]
        if kind == "sha256":
            res = _verify_sha256(rec.get("target"), parsed["digest"])
        elif kind == "url":
            res = _verify_url(parsed["url"])
        else:
            res = _verify_exit(parsed["code"], parsed["tail"], rec.get("meta"))
            if recheck_exit:
                res = _recheck_exit(parsed["code"], rec.get("meta"))
        res["receipt_id"] = receipt_id
        return res


# ─── never-raising helpers for integration sites ─────────────────────────────
# The receipts plugin is optional: if the ledger cannot be written, these
# return None and the caller's behavior is unchanged.

def try_issue(action: str, target: str, result: str, handle: str,
              meta: dict | None = None, path: str | None = None):
    """Issue a receipt, never raising. Returns the receipt dict or None."""
    try:
        return ReceiptLedger(path).issue(action, target, result, handle, meta)
    except Exception:
        return None


def try_file_receipt(action: str, target: str, result: str,
                     meta: dict | None = None, path: str | None = None):
    """Issue a sha256-handled receipt for a written file; None on any failure."""
    try:
        handle = sha256_file(target)
    except Exception:
        return None
    return try_issue(action, target, result, handle, meta, path)


def try_url_receipt(action: str, target: str, result: str, url: str,
                    meta: dict | None = None, path: str | None = None):
    """Issue a url-handled receipt; None on any failure."""
    return try_issue(action, target, result, url_handle(url), meta, path)


def try_exit_receipt(action: str, target: str, result: str, code: int,
                     tail: str = "", meta: dict | None = None,
                     path: str | None = None):
    """Issue an exit-code-handled receipt; None on any failure."""
    return try_issue(action, target, result, exit_handle(code, tail), meta, path)


# ─── text renderers (used by /receipts) ──────────────────────────────────────

def ledger_text(limit: int = 10, path: str | None = None) -> str:
    ledger = ReceiptLedger(path)
    recs = ledger.recent(limit)
    if not recs:
        return "no receipts yet (ledger: %s)" % ledger.path
    lines = ["RECEIPTS — %d total (last %d), ledger: %s"
             % (ledger.count(), len(recs), ledger.path)]
    for r in recs:
        lines.append("  %s  %s  %-24s %s" % (r["id"], r["ts"], r["action"],
                                             str(r["result"])[:64]))
    lines.append("verify: /receipts verify <id>   show: /receipts show <id>")
    return "\n".join(lines)


def receipt_text(receipt: dict) -> str:
    return "\n".join("%s: %s" % (k, json.dumps(v, ensure_ascii=False) if k in
                                 ("meta",) else v) for k, v in receipt.items())


def verify_text(result: dict) -> str:
    verdict = "VERIFY OK" if result.get("ok") else "VERIFY FAILED"
    return "%s — %s: %s" % (verdict, result.get("receipt_id"),
                            json.dumps(result.get("evidence", {}), ensure_ascii=False))


# ─── /receipts audit — mutating-path coverage report (grep-based) ────────────
# Every mutating command across the CLI + plugins is listed with the receipt
# action it MUST emit. Coverage is decided by grepping the command's own
# function body for a receipt-issuing call (`issue(`, try_*_receipt,
# _receipt_*). A second, write-primitive scan flags any *unlisted* handler
# that writes files/config without a receipt marker — so new mutating paths
# surface loudly instead of silently shipping receipt-less.

#: (command, source file relative to repo root, function, expected receipt action)
MUTATING_PATHS = [
    ("xomni plugins install",       "xomni_cli/__init__.py",             "cmd_plugins_install", "plugin.install"),
    ("xomni skill install",         "xomni_cli/__init__.py",             "cmd_skill_install",   "skill.install"),
    ("xomni providers add",         "xomni_cli/__init__.py",             "cmd_providers_add",   "provider.add"),
    ("xomni add <stack>",           "xomni_cli/__init__.py",             "cmd_add",             "stack.add"),
    ("/mcp add <path> (import)",    "plugins/mcp-catalog/__init__.py",   "_cmd_add",            "mcp.catalog.import"),
    ("/mcp add <name> (install)",   "plugins/mcp-catalog/__init__.py",   "_cmd_install",        "mcp.server.install"),
    ("/skills-install",             "plugins/omni-skills/__init__.py",   "_handle_install",     "skill.install"),
    ("/skills-marketplace",         "plugins/omni-skills/__init__.py",   "_handle_marketplace", "skill.marketplace"),
    ("/skills publish",             "plugins/omni-skills/__init__.py",   "_handle_publish",     "skill.publish"),
    ("skills_import (tool)",        "plugins/omni-skills/__init__.py",   "_tool_skills_import", "skill.install"),
    ("/skill save",                 "plugins/skill-drafter/__init__.py", "_handle_save",        "skill.draft.save"),
    ("/skill from-session",         "plugins/skill-drafter/core.py",      "lifecycle",           "skill.save"),
    ("/skill sync",                 "plugins/skill-drafter/__init__.py",  "_handle_sync",        "skill.sync"),
    ("/statusline on|off",          "plugins/title-statusline/__init__.py", "_handle_title",    "statusline.state"),
]

_RECEIPT_MARKER = re.compile(
    r"(issue\(|try_file_receipt|try_url_receipt|try_exit_receipt|try_issue|_receipt_)")
_WRITE_MARKER = re.compile(
    r"(open\([^)]*[\"'](?:w|a)[\"']|copyfile|copytree|\.write\(|os\.write|"
    r"shutil\.(?:move|rmtree)|json\.dump\()")
_HANDLER_NAME = re.compile(r"^(cmd_|_handle_|_cmd_|_tool_)")


def _repo_root() -> str:
    """Repo root = three dirs up from plugins/receipts/core.py."""
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


def _func_body(path: str, func: str) -> list[str]:
    """Body lines of a top-level function ([] when the file/function is missing)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^def %s\b" % re.escape(func), line):
            start = i + 1
            break
    if start is None:
        return []
    body = []
    for line in lines[start:]:
        if re.match(r"^(def |class |@)", line):
            break
        body.append(line)
    return body


def _has_receipt(path: str, func: str) -> tuple[bool, str]:
    """(covered, marker) — does the function body issue a receipt?"""
    for line in _func_body(path, func):
        m = _RECEIPT_MARKER.search(line)
        if m:
            return True, m.group(0).rstrip("(")
    return False, ""


def _scan_unlisted_writes(repo_root: str) -> list[dict]:
    """Handler-shaped functions (cmd_/_handle_/_cmd_/_tool_) that write files
    but contain no receipt-issuing call — new mutating paths that escaped the
    inventory. Reported loudly by the audit."""
    files = ["xomni_cli/__init__.py"]
    plugins_dir = os.path.join(repo_root, "plugins")
    if os.path.isdir(plugins_dir):
        files += [os.path.join("plugins", d, "__init__.py")
                  for d in sorted(os.listdir(plugins_dir))
                  if os.path.isfile(os.path.join(plugins_dir, d, "__init__.py"))]
    flagged = []
    for rel in files:
        path = os.path.join(repo_root, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            continue
        try:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        funcs: dict[str, list[str]] = {}
        cur: str | None = None
        for line in lines:
            m = re.match(r"^def (\w+)\(", line)
            if m:
                cur = m.group(1)
                funcs[cur] = []
            elif cur is not None:
                if re.match(r"^(def |class |@)", line):
                    cur = None
                else:
                    funcs[cur].append(line)
        for name, body in funcs.items():
            if not _HANDLER_NAME.match(name):
                continue
            writes = [ln for ln in body if _WRITE_MARKER.search(ln)]
            if writes and not any(_RECEIPT_MARKER.search(ln) for ln in body):
                flagged.append({"func": name, "file": rel,
                                "write": writes[0].strip()[:80]})
    return flagged


def audit_coverage(repo_root: str | None = None,
                   inventory: list | None = None) -> dict:
    """Grep-based coverage audit of every mutating command.

    Returns ``{rows, covered, total, unlisted, repo_root}`` where each row is
    ``{command, file, func, action, covered, marker}`` and *unlisted* lists
    handler functions that write files/config WITHOUT any receipt marker
    (missing-path detection — loud by design).
    """
    root = repo_root or _repo_root()
    rows = []
    for command, rel, func, action in (inventory if inventory is not None
                                       else MUTATING_PATHS):
        path = os.path.join(root, rel.replace("/", os.sep))
        covered, marker = _has_receipt(path, func)
        rows.append({"command": command, "file": rel, "func": func,
                     "action": action, "covered": covered, "marker": marker})
    covered = sum(1 for r in rows if r["covered"])
    return {"rows": rows, "covered": covered, "total": len(rows),
            "unlisted": _scan_unlisted_writes(root), "repo_root": root}


def audit_text(result: dict) -> str:
    """Render the audit report as a coverage table; gaps are loud."""
    rows = result.get("rows", [])
    lines = ["RECEIPTS AUDIT — mutating-path coverage: %d/%d commands emit a receipt"
             % (result.get("covered", 0), result.get("total", 0)),
             "  repo: %s" % result.get("repo_root", "")]
    lines.append("  %-28s %-7s %-20s %s" % ("command", "receipt", "action", "evidence"))
    for r in rows:
        flag = "OK " if r["covered"] else "GAP"
        lines.append("  %-28s %-7s %-20s %s" % (r["command"][:28], flag,
                                                r["action"],
                                                r["marker"] or "— no issue( call"))
    unlisted = result.get("unlisted", [])
    if unlisted:
        lines.append("  ! UNLISTED WRITE PATHS — handlers that write without a receipt:")
        for f in unlisted:
            lines.append("    ! %s — %s (%s)" % (f["func"], f["write"], f["file"]))
    else:
        lines.append("  unlisted write paths: none")
    lines.append("verify per receipt: /receipts verify <id>")
    return "\n".join(lines)
