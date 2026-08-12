"""Self-Operator: a zero-hook, human-gated improvement loop engine.

Loop: parse backlog -> propose plan -> human approval -> execute -> audit.
Stdlib only. Never registers hooks, never creates cron jobs.
"""

from .core import (
    OperatorError,
    STATE_DIR,
    approve_plan,
    audit_trail,
    execute_approved,
    parse_backlog,
    pending_approvals,
    propose_plan,
    reject_plan,
    run_cycle,
    submit_plan,
)

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
