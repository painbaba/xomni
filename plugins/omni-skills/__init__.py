"""omni-skills — XOMNI plugin wiring.

Commands:
  /skills-scan <dir>              inventory SKILL.md skills (parse + validate)
  /skills-install <dir> [--target=<skills_root>] [--dry-run]
  /skills-marketplace <dir>       install every skill in a marketplace repo
Tool:     skills_import(dir, target, dry_run)
No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

import os

from . import core

_CTX = None

DEFAULT_TARGET = os.path.expanduser("~/AppData/Local/hermes/skills")


def _parse_args(raw: str) -> tuple:
    target, dry = DEFAULT_TARGET, False
    parts = (raw or "").split()
    keep = []
    for p in parts:
        if p.startswith("--target="):
            target = p.split("=", 1)[1].strip()
        elif p == "--dry-run":
            dry = True
        else:
            keep.append(p)
    return " ".join(keep).strip(), target, dry


def _handle_scan(raw: str) -> str:
    path = (raw or "").strip().strip('"')
    if not path:
        return "/skills-scan <dir> — inventory SKILL.md skills under a directory."
    if not os.path.isdir(path):
        return f"/skills-scan: not a directory: {path}"
    skills = core.scan_skills(path)
    if not skills:
        return f"/skills-scan: no SKILL.md skills found under {path}"
    lines = [f"SCAN {path} — {len(skills)} skills"]
    for s in skills:
        check = core.validate_skill(s["dir"])
        lines.append(f"  {s['name']:<28} v{s['version'] or '?'}  {check['verdict']}"
                     f"  {len(s['files'])} files  {s['dir']}")
    return "\n".join(lines)


def _handle_install(raw: str) -> str:
    path, target, dry = _parse_args(raw)
    if not path:
        return "/skills-install <dir> [--target=...] [--dry-run]"
    if not os.path.isdir(path):
        return f"/skills-install: not a directory: {path}"
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        r = core.install_skill(path, target, dry_run=dry)
    else:
        r = core.install_marketplace(path, target, dry_run=dry)
    mode = "DRY-RUN " if dry else ""
    if not r["ok"]:
        return f"/skills-install: {mode}FAILED — {r.get('reason', 'see details')}"
    if "installed" in r:  # marketplace
        return (f"/skills-install: {mode}OK — {r['installed']} installed, "
                f"{r['rejected']} rejected -> {target}")
    return f"/skills-install: {mode}OK — {os.path.basename(r['dest'])} -> {target}"


def _tool_skills_import(params: dict) -> str:
    try:
        d = (params or {}).get("dir") or ""
        t = (params or {}).get("target") or DEFAULT_TARGET
        dry = bool((params or {}).get("dry_run"))
        if not os.path.isdir(d):
            return f"skills_import: not a directory: {d}"
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            r = core.install_skill(d, t, dry_run=dry)
            return f"skills_import OK{' (dry-run)' if dry else ''}: {os.path.basename(r['dest'])}"
        r = core.install_marketplace(d, t, dry_run=dry)
        return (f"skills_import OK{' (dry-run)' if dry else ''}: "
                f"{r['installed']} installed, {r['rejected']} rejected")
    except Exception as exc:
        return f"skills_import failed: {exc}"


TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "dir": {"type": "string", "description": "Skill dir or marketplace root containing SKILL.md files"},
        "target": {"type": "string", "description": "Target skills root (default ~/AppData/Local/hermes/skills)"},
        "dry_run": {"type": "boolean", "description": "Validate + plan without writing"},
    },
    "required": ["dir"],
}


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command("skills-scan", handler=_handle_scan,
                         description="Inventory + security-validate SKILL.md skills under a directory.",
                         args_hint="<dir>")
    ctx.register_command("skills-install", handler=_handle_install,
                         description="Install a skill or marketplace (SKILL.md interop) into the skills surface.",
                         args_hint="<dir> [--target=...] [--dry-run]")
    ctx.register_command("skills-marketplace", handler=_handle_install,
                         description="Install every skill in a marketplace repo root (alias of /skills-install).",
                         args_hint="<marketplace_dir> [--target=...] [--dry-run]")
    ctx.register_tool("skills_import", toolset="skills", schema=TOOL_SCHEMA,
                      handler=_tool_skills_import,
                      description="Import SKILL.md skills (single dir or marketplace) into the Hermes skills surface, fail-closed.")
