"""model-router — Hermes plugin wiring (automatic per-task model routing).

ONE deterministic hook (legacy-style, ci_gate-legal): `pre_llm_call`
classifies the user prompt task type with KEYWORDS ONLY and, when
`model-router.auto_route` is enabled (default true) and the classified model
differs from the configured model, records the suggestion — in memory
(last_suggestion + a pending-telemetry queue) and, on the next /route
command, into the cost-tracker-compatible ledger (~/.xomni-cost/route.db).

The hook is PURE CPU: zero model-API calls, zero network, zero subprocess,
zero disk I/O — it runs in well under 1ms (ci_gate FORBIDDEN_IN_HOOK_RE +
the <1ms budget are asserted by the tests). It never switches the model
itself: the host may apply the override if its per-call API allows it;
otherwise the hook annotates ctx.model_router_suggestion so the host's model
selection sees it. /route stays advisory — it prints what the hook would do.

Commands:
  /route <prompt>              auto-detect task type (quick|reasoning|vision|
                               heavy|default), pick the best free model from
                               real registry capabilities, show reason + the
                               config command to switch ('hermes config set
                               model <id>') + provider hint. ADVISORY only —
                               never switches the model by itself.
  /route telemetry             last 10 routed calls (model, ms, $, task type)
                               from the cost-tracker-compatible ledger —
                               auto-includes every call the hook classified.
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

# ctx captured at register() time (same pattern as context-compact/waitperk);
# None until register(ctx) is called — hook still works, just without the
# ctx annotation.
_CTX = None


def _auto_route_enabled(ctx) -> bool:
    """Read the model-router.auto_route config flag (default: True unset)."""
    if ctx is None:
        return core.AUTO_ROUTE_DEFAULT
    cfg = getattr(ctx, "config", None)
    if cfg is None:
        return core.AUTO_ROUTE_DEFAULT
    getter = getattr(cfg, "get", None)
    if not callable(getter):
        return core.AUTO_ROUTE_DEFAULT
    try:
        section = getter("model-router")
    except Exception:
        section = None
    if isinstance(section, dict) and "auto_route" in section:
        return bool(section["auto_route"])
    try:
        flat = getter("model-router.auto_route")
    except Exception:
        flat = None
    if flat is not None:
        return bool(flat)
    return core.AUTO_ROUTE_DEFAULT


def _configured_model(ctx, kwargs: dict) -> str | None:
    """Current model: per-call kwargs['model'] > ctx.model > ctx.config['model']."""
    m = kwargs.get("model")
    if isinstance(m, str) and m:
        return m
    if ctx is not None:
        m = getattr(ctx, "model", None)
        if isinstance(m, str) and m:
            return m
        cfg = getattr(ctx, "config", None)
        getter = getattr(cfg, "get", None)
        if callable(getter):
            try:
                m = getter("model")
            except Exception:
                m = None
            if isinstance(m, str) and m:
                return m
    return None


def _on_pre_llm_call(**kwargs) -> dict | None:
    """Deterministic routing-suggestion hook (pre_llm_call).

    Classifies the user message task type with keywords only and records the
    suggestion in memory. PURE CPU: never invokes the model API, never
    touches the network, never spawns a process, never writes to disk —
    well under 1ms. When auto_route is enabled (default) and the classified
    model differs from the configured model, the hook annotates
    ctx.model_router_suggestion and returns a structured hint the host may
    apply if its per-call model-override API supports it. The hook itself
    only ever SUGGESTS — /route and the hook never switch the model on their
    own.
    """
    global _CTX
    raw = kwargs.get("user_message")
    if not isinstance(raw, str) or not raw.strip():
        return None
    ctx = _CTX
    if not _auto_route_enabled(ctx):
        return None
    sug = core.classify_suggestion(raw, configured_model=_configured_model(ctx, kwargs))
    core.record_suggestion(sug)  # in-memory only — the hook does no I/O
    if ctx is not None:
        ctx.model_router_suggestion = sug  # host annotation (no override API)
    if not sug["differs"]:
        return None
    return {"model_router": {
        "suggested_model": sug["suggested_model"],
        "task_type": sug["task_type"],
        "config_command": "hermes config set model %s" % sug["suggested_model"],
    }}


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
    """Register the /route command (advisory) + ONE deterministic hook.

    The hook is legacy-style and ci_gate-legal: deterministic keyword
    classification only, no model-API/network/subprocess/disk in the handler
    (<1ms). /route remains advisory — it prints what the hook would do and
    never enforces a switch.
    """
    global _CTX
    _CTX = ctx
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
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
