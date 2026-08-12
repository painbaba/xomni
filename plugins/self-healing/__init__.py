"""self-healing — Hermes plugin wiring (ZERO HOOKS).

The /heal command is invoked on demand (or by cron); nothing is wired to
agent events, so there is no hot path. It watches its own cron/scripts:

  * watchdog          kills silent hangs (alive + no output for quiet_after_s
                      — the vectorbt-install-hangs-180s case) and over-time runs
  * postconditions    flags exit-0-but-nothing-happened (install said success,
                      binary missing)
  * drift scan        compares plugins roster / provider block / .env KEY names
                      vs actual — across EVERY hermes profile (base + all
                      profiles/*); /heal fix <profile|all> [--yes] restores
                      (never touches secret VALUES, only KEY presence)
  * audit trail       every kill + every fix appends {ts, detector, subject,
                      action, before, after[, profile]} to
                      ~/.xomni-heal/heal.jsonl — multi-profile fixes carry the
                      profile name
"""
from __future__ import annotations

try:
    from . import core
except ImportError:  # loaded as a bare file (tests / direct execution)
    import core  # type: ignore

HELP = (
    "/heal profiles           list every hermes profile (base + profiles/*)\n"
    "                         with per-profile drift status\n"
    "/heal scan [profile|all] watchdog + postcondition checks + drift scan\n"
    "                         (default: all profiles)\n"
    "/heal fix <profile|all>  fix every drift of a profile ('all' = every\n"
    "                         profile). Add --yes to apply; without it the\n"
    "                         run is a dry-run plan (no changes)\n"
    "/heal fix <id>           legacy: fix one drift of the base profile,\n"
    "                         e.g. plugins.omni-registry, env.ANTHROPIC_API_KEY\n"
    "/heal status             last 10 audit entries from ~/.xomni-heal/heal.jsonl\n"
    "/heal help               this help\n"
    "Audit trail: ~/.xomni-heal/heal.jsonl — every fix is logged with the\n"
    "profile name. Fixes never read or write secret VALUES — placeholders only."
)


def _handle_heal(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = (parts[0] or "scan").lower()
    rest = parts[1] if len(parts) > 1 else ""
    if cmd in ("profiles", "p"):
        return core.cmd_profiles()
    if cmd in ("scan", "s"):
        return core.cmd_scan(rest)
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
                    "multi-profile config-drift auto-fix (base + all profiles/*), "
                    "per-profile audit trail heal.jsonl (zero hooks)",
        args_hint="[profiles|scan [profile|all]|fix <profile|all|id> [--yes]|status|help]",
    )
