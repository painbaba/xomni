"""self-healing — Hermes plugin wiring (ZERO HOOKS).

The /heal command is invoked on demand (or by cron); nothing is wired to
agent events, so there is no hot path. It watches its own cron/scripts:

  * watchdog          kills silent hangs (alive + no output for quiet_after_s
                      — the vectorbt-install-hangs-180s case) and over-time runs
  * postconditions    flags exit-0-but-nothing-happened (install said success,
                      binary missing)
  * drift scan        compares plugins roster / provider block / .env KEY names
                      vs actual; /heal fix <id> restores (never touches secret
                      VALUES, only KEY presence)
  * audit trail       every kill + every fix appends {ts, detector, subject,
                      action, before, after} to ~/.xomni-heal/heal.jsonl
"""
from __future__ import annotations

try:
    from . import core
except ImportError:  # loaded as a bare file (tests / direct execution)
    import core  # type: ignore

HELP = (
    "/heal scan               run watchdog + postcondition checks + drift scan\n"
    "/heal fix <id>           fix one drift (e.g. plugins.omni-registry,\n"
    "                         env.ANTHROPIC_API_KEY); 'all' fixes every drift\n"
    "/heal status             last 10 audit entries from ~/.xomni-heal/heal.jsonl\n"
    "/heal help               this help\n"
    "Audit trail: ~/.xomni-heal/heal.jsonl — every kill/fix is logged."
)


def _handle_heal(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = (parts[0] or "scan").lower()
    rest = parts[1] if len(parts) > 1 else ""
    if cmd in ("scan", "s"):
        return core.cmd_scan()
    if cmd == "fix":
        return core.cmd_fix(rest)
    if cmd in ("status", "st"):
        return core.cmd_status()
    return HELP


def register(ctx) -> None:
    """Register ONLY the /heal command — no hooks (zero-hooks rule)."""
    ctx.register_command(
        "heal", handler=_handle_heal,
        description="Self-healing: watchdog kills silent hangs, postcondition checks, "
                    "config-drift auto-fix, audit trail heal.jsonl (zero hooks)",
        args_hint="[scan|fix <id>|status|help]",
    )
