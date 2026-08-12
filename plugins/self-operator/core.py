"""Self-Operator core: parse -> propose -> approve -> execute -> audit.

A zero-hook, stdlib-only loop engine that drives a backlog of open items.
Nothing is ever executed without explicit human approval (or an explicit
``auto_approve=True`` opt-out at the call site), and every executed item is
appended to a JSON-lines audit trail.

Rules honoured here (XOMNI):
* Zero-hook: no ``register_hook`` anywhere in this module.
* Pure stdlib: only ``json``, ``re``, ``time``, ``pathlib``.
* Fail-loud: rule violations raise :class:`OperatorError` naming the violation.
"""

import json
import re
import time
from pathlib import Path

__all__ = [
    "OperatorError",
    "STATE_DIR",
    "parse_backlog",
    "propose_plan",
    "submit_plan",
    "approve_plan",
    "reject_plan",
    "pending_approvals",
    "execute_approved",
    "audit_trail",
    "run_cycle",
]

# Only unchecked items count as open: "- [ ] " (dash, space, [ ], space).
BACKLOG_ITEM_RE = re.compile(r"^- \[ \] ")
DEFAULT_MAX_ITEMS = 8
APPROVALS_FILE = "approvals.json"
AUDIT_FILE = "operator.jsonl"

# Default state directory. Tests and callers patch this or pass ``state_dir``.
STATE_DIR = Path("state")

_plan_seq = 0  # monotonic plan id source: plan-1, plan-2, ...


class OperatorError(Exception):
    """Raised when a self-operator rule is violated (fail-loud)."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _resolve_state_dir(state_dir):
    """Return a Path for ``state_dir``, falling back to the module STATE_DIR."""
    if state_dir is None:
        return Path(STATE_DIR)
    return Path(state_dir)


def _approvals_path(state_dir):
    return _resolve_state_dir(state_dir) / APPROVALS_FILE


def _audit_path(state_dir):
    return _resolve_state_dir(state_dir) / AUDIT_FILE


def _load_approvals(state_dir):
    """Read approvals.json; return {'plans': [...]} when absent or empty."""
    path = _approvals_path(state_dir)
    if not path.exists():
        return {"plans": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise OperatorError(
            "state file {0} is unreadable: {1}".format(path, exc)
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("plans"), list):
        raise OperatorError(
            "state file {0} is malformed: expected {{'plans': [...]}}".format(path)
        )
    return data


def _write_approvals(state_dir, data):
    path = _approvals_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _find_plan(plan_id, state_dir):
    for record in _load_approvals(state_dir)["plans"]:
        if record.get("plan_id") == plan_id:
            return record
    return None


def _append_audit(state_dir, record):
    path = _audit_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# stage 1: parse
# ---------------------------------------------------------------------------

def parse_backlog(path):
    """Return open items from a BACKLOG markdown file, in file order.

    Each item is ``{'line': int, 'title': str}``. Only lines matching
    ``r'^- \[ \] '`` (unchecked items) are included; ``[x]``, ``[~]``,
    indented and non-list lines are ignored.
    """
    items = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, start=1):
        if BACKLOG_ITEM_RE.match(line):
            items.append({"line": index, "title": line[len("- [ ] "):].strip()})
    return items


# ---------------------------------------------------------------------------
# stage 2: propose
# ---------------------------------------------------------------------------

def propose_plan(items, max_items=DEFAULT_MAX_ITEMS):
    """Propose a plan from open items, preserving file order, capped.

    Returns ``{'plan_id': 'plan-<n>', 'items': [titles], 'count': n,
    'proposed_at': float}``. An empty backlog yields a zero-item plan.
    """
    global _plan_seq
    _plan_seq += 1
    titles = [item["title"] for item in items[:max_items]]
    return {
        "plan_id": "plan-{0}".format(_plan_seq),
        "items": titles,
        "count": len(titles),
        "proposed_at": time.time(),
    }


# ---------------------------------------------------------------------------
# stage 3: approve (human gate)
# ---------------------------------------------------------------------------

def submit_plan(plan, state_dir=None):
    """Persist a proposed plan to ``state_dir/approvals.json`` as 'pending'.

    Raises :class:`OperatorError` if the plan id was already submitted.
    """
    plan_id = plan["plan_id"]
    if _find_plan(plan_id, state_dir) is not None:
        raise OperatorError("plan {0} already submitted".format(plan_id))
    state = _load_approvals(state_dir)
    record = {
        "plan_id": plan_id,
        "items": list(plan.get("items", [])),
        "count": plan.get("count", len(plan.get("items", []))),
        "proposed_at": plan.get("proposed_at", time.time()),
        "status": "pending",
    }
    state["plans"].append(record)
    _write_approvals(state_dir, state)
    return record


def _transition(plan_id, state_dir, new_status):
    """Move a plan to ``new_status``; only 'pending' plans may transition."""
    state = _load_approvals(state_dir)
    for record in state["plans"]:
        if record.get("plan_id") == plan_id:
            if record["status"] != "pending":
                raise OperatorError(
                    "plan {0} cannot be {1}: current status is {2!r} "
                    "(only 'pending' plans may transition)".format(
                        plan_id, new_status, record["status"]
                    )
                )
            record["status"] = new_status
            _write_approvals(state_dir, state)
            return new_status
    raise OperatorError("unknown plan {0}".format(plan_id))


def approve_plan(plan_id, state_dir=None):
    """Approve a pending plan; returns 'approved'. Fail-loud otherwise."""
    return _transition(plan_id, state_dir, "approved")


def reject_plan(plan_id, state_dir=None):
    """Reject a pending plan; returns 'rejected'. Fail-loud otherwise."""
    return _transition(plan_id, state_dir, "rejected")


def pending_approvals(state_dir=None):
    """Return the list of plans whose status is still 'pending'."""
    return [
        record
        for record in _load_approvals(state_dir)["plans"]
        if record["status"] == "pending"
    ]


# ---------------------------------------------------------------------------
# stage 4: execute
# ---------------------------------------------------------------------------

def execute_approved(plan_id, state_dir=None, runner=None):
    """Run an approved plan's items through ``runner(item_title)``.

    The runner returns a dict; each outcome is normalized to
    ``{'item', 'ok': bool, 'note': str}`` and one JSON line per item is
    appended to ``state_dir/operator.jsonl`` (audit trail).

    Raises :class:`OperatorError` unless the plan is 'approved' — the
    human-approval gate. A plan that was never submitted is also a violation.
    """
    record = _find_plan(plan_id, state_dir)
    if record is None:
        raise OperatorError(
            "human approval required for plan {0}: plan was never submitted".format(
                plan_id
            )
        )
    if record["status"] != "approved":
        raise OperatorError(
            "human approval required for plan {0}: status is {1!r}, "
            "not 'approved'".format(plan_id, record["status"])
        )
    if runner is None:
        runner = _default_runner
    results = []
    for title in record.get("items", []):
        outcome = runner(title)
        ok = bool(outcome.get("ok", False))
        note = str(outcome.get("note", ""))
        results.append({"item": title, "ok": ok, "note": note})
        _append_audit(
            state_dir,
            {
                "ts": time.time(),
                "plan_id": plan_id,
                "item": title,
                "ok": ok,
                "note": note,
            },
        )
    return results


def _default_runner(item_title):
    """Default runner: never touches the system, always succeeds (dry-run)."""
    return {"ok": True, "note": "dry-run"}


# ---------------------------------------------------------------------------
# stage 5: audit
# ---------------------------------------------------------------------------

def audit_trail(state_dir=None):
    """Parse ``state_dir/operator.jsonl`` back into a list of records."""
    path = _audit_path(state_dir)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise OperatorError(
                "audit file {0} is corrupt at line: {1}".format(path, exc)
            ) from exc
    return records


# ---------------------------------------------------------------------------
# loop
# ---------------------------------------------------------------------------

def run_cycle(backlog_path, state_dir=None, runner=None, auto_approve=False):
    """Run one operator loop: parse -> propose -> (approve) -> execute.

    * If a plan is already awaiting a human decision and ``auto_approve`` is
      False, the cycle returns ``{'status': 'awaiting_approval', 'plan_id':
      ...}`` without piling up new plans.
    * Otherwise the fresh plan is submitted; without ``auto_approve`` it
      waits for the human (same 'awaiting_approval' result).
    * With ``auto_approve=True`` the plan is approved and executed with
      ``runner`` (default: dry-run) and the cycle returns
      ``{'status': 'executed', 'results': [...]}``.
    """
    state_dir = _resolve_state_dir(state_dir)
    pending = pending_approvals(state_dir)
    if pending and not auto_approve:
        return {"status": "awaiting_approval", "plan_id": pending[0]["plan_id"]}

    items = parse_backlog(backlog_path)
    plan = propose_plan(items)
    submit_plan(plan, state_dir)

    if not auto_approve:
        return {"status": "awaiting_approval", "plan_id": plan["plan_id"]}

    approve_plan(plan["plan_id"], state_dir)
    results = execute_approved(plan["plan_id"], state_dir, runner)
    return {"status": "executed", "results": results}
