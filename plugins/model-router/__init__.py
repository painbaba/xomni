"""model-router — Hermes plugin wiring (automatic per-task model routing).

ZERO HOOKS (new-plugin rule): this plugin registers no hooks. /route is a
pure command — routing reads the omni-registry capabilities on demand, and
telemetry is written by explicit calls (/route record, core.record_call) into
the cost-tracker-compatible ledger (~/.xomni-cost/route.db). Nothing is wired
to agent events, so there is no hot path to slow down.

Commands:
  /route <prompt>              auto-detect task type (quick|reasoning|vision|
                               heavy|default), pick the best free model from
                               real registry capabilities, show reason + the
                               config command to switch ('hermes config set
                               model <id>') + provider hint.
  /route telemetry             last 10 routed calls (model, ms, $, task type)
                               from the cost-tracker-compatible ledger.
  /route record <model> <ms> [est_cost] [task_type]
                               manually log one routed call (command-based
                               telemetry — no hooks).
"""
from __future__ import annotations

from . import core

HELP = (
    "/route <prompt>                   auto-pick the best free model for the task "
    "(quick/reasoning/vision/heavy) — shows reason + switch command\n"
    "/route telemetry                  last 10 routed calls (model, ms, $, task type)\n"
    "/route record <model> <ms> [est_cost] [task_type]\n"
    "                                 manually log a routed call into the ledger"
)


def _handle_route(raw: str) -> str:
    arg = (raw or "").strip()
    # strict help match — "hello there" is a task prompt, not help
    if not arg or arg.lower() in ("help", "h", "?") or arg.lower().startswith("help "):
        return HELP
    low = arg.lower()
    if low == "telemetry":
        return core.route_telemetry_text()
    if low.startswith("record"):
        parts = arg.split()
        if len(parts) < 3:
            return ("usage: /route record <model> <latency_ms> [est_cost] "
                    "[task_type]")
        model = parts[1]
        try:
            latency = int(parts[2])
        except ValueError:
            return f"usage: /route record <model> <latency_ms> [est_cost] [task_type] — '{parts[2]}' is not an int"
        est_cost = None
        task_type = ""
        if len(parts) > 3:
            try:
                est_cost = float(parts[3])
            except ValueError:
                return f"usage: /route record <model> <latency_ms> [est_cost] [task_type] — '{parts[3]}' is not a number"
        if len(parts) > 4:
            task_type = parts[4]
        res = core.record_call(model, latency_ms=latency, est_cost=est_cost,
                               task_type=task_type)
        return ("recorded routed call: %s %dms $%.6f [%s] id=%d%s"
                % (res["model"], res["latency_ms"], res["est_cost"],
                   res["task_type"] or "-", res["id"],
                   " (fallback rate)" if res["flagged"] else ""))
    # anything else is a task prompt
    res = core.route(arg)
    return core.route_text(res)


def register(ctx) -> None:
    """Register ONLY the /route command — no hooks, per the zero-hooks rule."""
    ctx.register_command(
        "route",
        handler=_handle_route,
        description=(
            "Automatic per-task model routing: pick the best free model for "
            "the task (quick/reasoning/vision/heavy) from omni-registry "
            "capabilities; telemetry via the cost-tracker ledger"
        ),
        args_hint="<prompt> | telemetry | record <model> <ms> [est_cost] [task_type]",
    )
