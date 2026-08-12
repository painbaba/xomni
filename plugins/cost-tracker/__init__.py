"""cost-tracker — Hermes plugin wiring.

ZERO HOOKS (new-plugin rule): this plugin registers no hooks. The /cost
command reads the sqlite ledger on demand; the ``cost_track`` tool is called
explicitly by provider-pool (or any agent caller) when a model call completes
— nothing is wired to agent events, so there is no hot path to slow down.

Data: ~/.xomni-cost/costs.db (sqlite, append-only ledger + budget config).
Commands: /cost report, /cost budget <daily> [weekly], /cost budget hard on|off.
"""
from __future__ import annotations

import time

from . import core

HELP = (
    "/cost                     show the cost report (top models, totals, budget status)\n"
    "/cost budget <daily> [weekly]   set budget caps in USD (0 = no cap)\n"
    "/cost budget hard on|off  enable/disable the hard-stop (block new calls over cap)\n"
    "/cost digest              weekly summary: totals, top 3 models, budget status\n"
    "/cost export <path>       full ledger → CSV (timestamp, model, in, out, est_cost)"
)


def _handle_cost(raw: str) -> str:
    args = (raw or "").strip()
    parts = args.split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    tr = core.CostTracker()
    if not cmd or cmd.startswith(("report", "show", "?")):
        return tr.cmd_report(ts=time.time())
    if cmd == "budget":
        return tr.cmd_budget(rest, ts=time.time())
    if cmd == "digest":
        return tr.cmd_digest(ts=time.time())
    if cmd == "export":
        return tr.cmd_export(rest)
    if cmd.startswith(("help", "h")):
        return HELP
    return HELP


def register(ctx) -> None:
    """Register ONLY the /cost command — no hooks, per the zero-hooks rule."""
    ctx.register_command(
        "cost", handler=_handle_cost,
        description="Model cost ledger: sqlite log, budget caps, hard-stop (free forever)",
        args_hint="[report|digest|export <path>|budget <daily> [weekly]|budget hard on|off]",
    )
