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
    "/cost caps                show spend caps + rolling status (5h/1d/7d/30d)\n"
    "/cost caps set <period> <limit_usd> <warn|park>   set a rolling spend cap\n"
    "/cost caps clear <period> clear a spend cap\n"
    "/cost caps model <id> <limit_usd>|clear   per-model cap (park at limit)\n"
    "/cost today               calendar-day rollup: calls, tokens, est cost\n"
    "/cost week                ISO-week rollup: calls, tokens, est cost\n"
    "/cost model <id>          per-model spend (all-time + today + week)\n"
    "/cost top                 top-5 models by est. spend (all-time)\n"
    "/cost digest              weekly summary: totals, top 3 models, budget status\n"
    "/cost export <path>       full ledger → CSV (timestamp, model, in, out, est_cost)\n"
    "/cost sync [path]         re-sync the cost table from the omni-registry pinned snapshot"
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
    if cmd == "caps":
        return tr.cmd_caps(rest, ts=time.time())
    if cmd == "today":
        return tr.cmd_today(ts=time.time())
    if cmd == "week":
        return tr.cmd_week(ts=time.time())
    if cmd == "model":
        return tr.cmd_model(rest, ts=time.time())
    if cmd == "top":
        return tr.cmd_top(ts=time.time())
    if cmd == "digest":
        return tr.cmd_digest(ts=time.time())
    if cmd == "export":
        return tr.cmd_export(rest)
    if cmd == "sync":
        return tr.cmd_sync(rest)
    if cmd.startswith(("help", "h")):
        return HELP
    return HELP


def register(ctx) -> None:
    """Register ONLY the /cost command — no hooks, per the zero-hooks rule."""
    ctx.register_command(
        "cost", handler=_handle_cost,
        description="Model cost ledger: sqlite log, budget caps, spend caps, rollups (free forever)",
        args_hint=("[report|budget <daily> [weekly]|budget hard on|off|caps [set <period> <limit> "
                   "<warn|park>|clear <period>|model <id> <limit>]|today|week|model <id>|top|"
                   "digest|export <path>|sync [path]]"),
    )
