"""omni-skills — XOMNI plugin wiring.

Commands:
  /skills-scan <dir>              inventory SKILL.md skills (parse + validate)
  /skills-install <dir> [--target=<skills_root>] [--dry-run]
  /skills-marketplace <url-or-dir> [--target=<skills_root>] [--dry-run]
                                  install every skill from a git marketplace
                                  URL (https:// or git://, shallow clone) or a
                                  local repo dir
  /skills publish <dir> [--yes] [--author=NAME] [--repo=<target-repo-dir>]
                                  [--to=github|clawhub] [--dry-run]
                                  credit-stamp (idempotent) then DELEGATE the
                                  publish to the host `hermes skills publish
                                  --to <target>`; repo-copy fallback only when
                                  the host CLI is missing
Tool:     skills_import(dir, target, dry_run)
No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

import os

from . import core

_CTX = None

DEFAULT_TARGET = os.path.expanduser("~/AppData/Local/hermes/skills")


# ─── receipts-by-default (U7) ────────────────────────────────────────────────
# Every successful install issues a verifiable receipt into the JSONL ledger
# (plugins/receipts: sha256 of the installed SKILL.md). The receipts plugin
# is optional — if it cannot be loaded or the ledger cannot be written,
# installs behave exactly as before.
_RECEIPTS = None


def _receipts_core():
    """Lazily resolve receipts.core (installed package, else XOMNI checkout)."""
    global _RECEIPTS
    if _RECEIPTS is None:
        mod = None
        try:
            from receipts import core as mod
        except Exception:
            mod = None
        if mod is None:
            try:
                import importlib.util
                import sys as _sys
                home = os.environ.get("XOMNI_HOME", "")
                if not home:
                    home = os.path.abspath(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "..", ".."))
                cand = os.path.join(home, "plugins", "receipts", "core.py")
                if os.path.isfile(cand):
                    fspec = importlib.util.spec_from_file_location("receipts_core", cand)
                    mod = importlib.util.module_from_spec(fspec)
                    _sys.modules["receipts_core"] = mod
                    fspec.loader.exec_module(mod)
            except Exception:
                mod = None
        _RECEIPTS = mod if mod is not None else False
    return _RECEIPTS or None


def _receipt_for_install(r: dict, action: str, base: str) -> int:
    """Issue one sha256-handled receipt per installed skill (never raises).

    Returns the number of receipts issued; 0 when nothing was installed,
    when dry-running, or when the receipts plugin is unavailable.
    """
    if not r or not r.get("ok") or r.get("dry_run"):
        return 0
    mod = _receipts_core()
    if mod is None:
        return 0
    n = 0
    results = r.get("results")
    if results:  # marketplace: one receipt per installed skill
        for res in results:
            if res.get("ok") and res.get("dest"):
                if mod.try_file_receipt(action, os.path.join(res["dest"], "SKILL.md"),
                                        "%s %s" % (res.get("verdict", "OK"),
                                                   res.get("name", "")),
                                        {"skill": res.get("name", ""), "source": base}):
                    n += 1
        return n
    dest = r.get("dest")
    if dest:
        if mod.try_file_receipt(action, os.path.join(dest, "SKILL.md"),
                                r.get("verdict", "OK"), {"skill": base}):
            n += 1
    return n


def _receipt_for_publish(r: dict, skill_dir: str) -> int:
    """Issue a sha256-handled receipt for a published skill (never raises).

    Host-delegated publish: the side-effect is the credit stamp written into
    the source SKILL.md. Repo-copy fallback: the copied SKILL.md under
    ``r['path']``. Dry runs and failures issue nothing.
    """
    if not r or not r.get("ok") or r.get("dry_run"):
        return 0
    mod = _receipts_core()
    if mod is None:
        return 0
    target, result = None, ""
    if r.get("delegated"):
        target = os.path.join(skill_dir, "SKILL.md")
        result = "delegated to %s (--to %s)" % (r.get("host", "hermes"),
                                                r.get("target", "github"))
    elif r.get("path"):
        target = os.path.join(r["path"], "SKILL.md")
        result = "repo-copy fallback publish (host publish preferred)"
    if not target or not os.path.isfile(target):
        return 0
    if mod.try_file_receipt("skill.publish", target, result,
                            {"skill": r.get("name", ""),
                             "delegated": bool(r.get("delegated"))}):
        return 1
    return 0


def _parse_args(raw: str) -> tuple:
    """Parse shared flags. Returns (path, target, dry_run, yes).

    --yes / -y (U3 — non-interactive): accepted and stripped; these commands
    never prompt, and the flag guarantees no confirmation is ever requested.
    """
    target, dry, yes = DEFAULT_TARGET, False, False
    parts = (raw or "").split()
    keep = []
    for p in parts:
        if p.startswith("--target="):
            target = p.split("=", 1)[1].strip()
        elif p == "--dry-run":
            dry = True
        elif p in ("--yes", "-y"):
            yes = True
        else:
            keep.append(p)
    return " ".join(keep).strip(), target, dry, yes


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


def _handle_search(raw: str) -> str:
    query = (raw or "").strip()
    if not query:
        return "/skills-search <query> — search the skills DB and installed skill trees."
    hits = core.search_skills(query)
    if not hits:
        return f"/skills-search \"{query}\" — 0 hits (try broader terms, or /skills-scan <dir>)"
    lines = [f"SEARCH \"{query}\" — {len(hits)} hits"]
    for h in hits:
        rank = f"#{h.get('rank')} " if h.get("rank") not in (None, "", "?") else ""
        cat = h.get("category", "")
        desc = h.get("description", "")
        lines.append(f"  {rank}{h['name']:<28} [{cat}] {desc}")
    lines.append("Install: /skills-install <dir> — or `xomni skill install <dir>` in a terminal.")
    return "\n".join(lines)


def _handle_list(raw: str) -> str:
    plugins = core.list_plugins()
    if not plugins:
        return "/plugins-list: no plugins found"
    lines = [f"PLUGINS — {len(plugins)}"]
    for p in plugins:
        lines.append(f"  {p['name']:<20} {'hooks' if p['has_hooks'] else 'zero-hooks'}")
    return "\n".join(lines)


def _handle_status(raw: str) -> str:
    st = core.env_status()
    lines = [f"XOMNI ENV — home: {st['xomni_home'] or '(not a checkout)'}"]
    lines.append(f"  plugins : {st['plugins_total']} "
                 f"({', '.join(p['name'] for p in st['plugins'][:8])}"
                 f"{'…' if st['plugins_total'] > 8 else ''})")
    lines.append(f"  skills  : {st['skills_total']} in skill trees")
    for k, v in st["data"].items():
        lines.append(f"  data    : {k} = {v}")
    lines.append("  models  : 25 verified free models (provider-pool) + any Hermes provider "
                 "(see /providers)")
    return "\n".join(lines)


def _handle_install(raw: str) -> str:
    path, target, dry, _yes = _parse_args(raw)
    if not path:
        return "/skills-install <dir> [--yes] [--target=...] [--dry-run]"
    if not os.path.isdir(path):
        return f"/skills-install: not a directory: {path}"
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        r = core.install_skill(path, target, dry_run=dry)
    else:
        r = core.install_marketplace(path, target, dry_run=dry)
    mode = "DRY-RUN " if dry else ""
    if not r["ok"]:
        return f"/skills-install: {mode}FAILED — {r.get('reason', 'see details')}"
    _receipt_for_install(r, action="skill.install", base=os.path.basename(path))
    if "installed" in r:  # marketplace
        return (f"/skills-install: {mode}OK — {r['installed']} installed, "
                f"{r['rejected']} rejected -> {target}")
    return f"/skills-install: {mode}OK — {os.path.basename(r['dest'])} -> {target}"


def _handle_marketplace(raw: str) -> str:
    """/skills-marketplace <url-or-dir> — git URL (https/git, shallow clone,
    cached under ~/.xomni-marketplaces) or a local marketplace dir."""
    path, target, dry, _yes = _parse_args(raw)
    if not path:
        return ("/skills-marketplace <url-or-dir> [--yes] [--target=...] [--dry-run] — "
                "install every skill from a git marketplace URL (https:// or "
                "git://, shallow clone) or a local repo dir.")
    mode = "DRY-RUN " if dry else ""
    if path.startswith(("https://", "git://")) or "://" in path:
        # anything scheme-like goes through the strict URL gate (fail-closed)
        r = core.install_marketplace_url(path, target, dry_run=dry)
        if not r["ok"]:
            return f"/skills-marketplace: {mode}FAILED — {r.get('reason', 'see details')}"
        _receipt_for_install(r, action="skill.marketplace", base=path)
        return (f"/skills-marketplace: {mode}OK — {r['installed']} installed, "
                f"{r['rejected']} rejected (cached {r.get('cache_dir', '')}) -> {target}")
    if not os.path.isdir(path):
        return f"/skills-marketplace: not a directory or git URL: {path}"
    r = core.install_marketplace(path, target, dry_run=dry)
    if not r["ok"]:
        return f"/skills-marketplace: {mode}FAILED — {r.get('reason', 'see details')}"
    _receipt_for_install(r, action="skill.marketplace", base=os.path.basename(path))
    return (f"/skills-marketplace: {mode}OK — {r['installed']} installed, "
            f"{r['rejected']} rejected -> {target}")


def _handle_publish(raw: str) -> str:
    """/skills publish <dir> [--yes] [--author=NAME] [--repo=<target-repo-dir>]
    [--to=github|clawhub] [--dry-run] — credit-stamp a skill
    (author/source/published_at/origin, idempotent) then DELEGATE the actual
    publish to the host CLI `hermes skills publish --to <target>` (single
    publish path). Falls back to the repo-copy path only when the host CLI is
    missing, with a loud note that host publish is preferred."""
    parts = (raw or "").split()
    author, repo, target, dry = None, "", "github", False
    keep = []
    for p in parts:
        if p.startswith("--author="):
            author = p.split("=", 1)[1].strip() or None
        elif p.startswith("--repo="):
            repo = p.split("=", 1)[1].strip()
        elif p.startswith("--to="):
            target = p.split("=", 1)[1].strip().lower() or "github"
        elif p == "--dry-run":
            dry = True
        elif p in ("--yes", "-y"):
            # U3 — non-interactive: accepted and stripped; /skills publish
            # never prompts, and the flag guarantees no confirmation is ever
            # requested (must never be misread as the skill dir).
            continue
        else:
            keep.append(p)
    path = " ".join(keep).strip().strip('"')
    if not path:
        return ("/skills publish <dir> [--yes] [--author=NAME] "
                "[--repo=<target-repo-dir>] [--to=github|clawhub] [--dry-run] "
                "— credit-stamp then delegate publish to the host "
                "(`hermes skills publish --to <target>`); repo-copy fallback "
                "only when the host CLI is missing.")
    if target not in core.HOST_PUBLISH_TARGETS:
        return (f"/skills publish: unknown --to target '{target}' — use one "
                f"of {', '.join(core.HOST_PUBLISH_TARGETS)}")
    fallback_repo = repo or core.find_xomni_home() or os.getcwd()
    r = core.publish_via_host(path, target=target, author=author,
                              fallback_repo=fallback_repo, dry_run=dry)
    if not r["ok"]:
        detail = ""
        if r.get("issues"):
            detail = " (" + "; ".join(f for f, _ in r["issues"][:3]) + ")"
        return f"/skills publish: FAILED — {r.get('reason', 'see details')}{detail}"
    _receipt_for_publish(r, path)
    mode = "DRY-RUN " if dry else ""
    credit_lines = [f"  author       : {r['author']}",
                    f"  source       : {r['source']}",
                    f"  published_at : {r['published_at']}"]
    if r.get("origin"):
        credit_lines.append(f"  origin       : {r['origin']}")
    if r.get("original_author"):
        credit_lines.append(f"  original_author (preserved): {r['original_author']}")
    lines = [f"/skills publish: {mode}OK — {r['name']} "
             f"(credit {'stamped' if r['stamped'] else 'already present, untouched'})",
             "CREDIT", *credit_lines]
    if r.get("delegated"):
        lines += ["",
                  f"DELEGATED to host ({r.get('host', 'hermes')}) — single publish path:",
                  f"  {' '.join(r['command'])}"]
        if r.get("host_output"):
            lines += ["host output:",
                      *[f"  {ln}" for ln in r["host_output"].splitlines()[:6]]]
        target_origin = r.get("origin")
        npx_target = target_origin or "<owner/repo>"
        lines += ["",
                  "SKILLS.SH SUBMISSION: once the host publish lands and the repo is",
                  "indexed by the directory (https://skills.sh), anyone installs via:",
                  f"  npx skills add {npx_target}",
                  "  or XOMNI: /skills-marketplace <git-url>  (shallow clone, fail-closed)"]
        receipt = (f"RECEIPT: name={r['name']} delegated={r['delegated']} "
                   f"target={r.get('target', 'github')} "
                   f"author={r['author']} stamped={r['stamped']}")
    else:
        lines += ["",
                  f"NOTE: host publish ({r.get('host', 'hermes')} skills publish) "
                  "unavailable — used repo-copy fallback. HOST PUBLISH IS PREFERRED.",
                  f"copied to : {r['path']}"]
        git = r["git"]
        target_origin = core.detect_origin(git["repo"]) or r.get("origin")
        npx_target = target_origin or "<owner/repo>"
        lines += ["",
                  "PUSH (from the target repo):",
                  f"  cd {git['repo']}",
                  f"  git add {git['add']}",
                  f"  git commit -m '{git['commit']}'",
                  "  git push",
                  "",
                  "SKILLS.SH SUBMISSION: once the repo is public and indexed by the",
                  "directory (https://skills.sh — 'The Agent Skills Directory'), anyone",
                  "installs it via:",
                  f"  npx skills add {npx_target}",
                  "  or XOMNI: /skills-marketplace <git-url>  (shallow clone, fail-closed)"]
        receipt = (f"RECEIPT: name={r['name']} sha256={r['sha256']} "
                   f"path={r['path']} author={r['author']} "
                   f"delegated={r['delegated']}")
    lines += ["", receipt]
    return "\n".join(lines)


def _tool_skills_import(params: dict) -> str:
    try:
        d = (params or {}).get("dir") or ""
        t = (params or {}).get("target") or DEFAULT_TARGET
        dry = bool((params or {}).get("dry_run"))
        if not os.path.isdir(d):
            return f"skills_import: not a directory: {d}"
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            r = core.install_skill(d, t, dry_run=dry)
            _receipt_for_install(r, action="skill.install", base=os.path.basename(d))
            return f"skills_import OK{' (dry-run)' if dry else ''}: {os.path.basename(r['dest'])}"
        r = core.install_marketplace(d, t, dry_run=dry)
        _receipt_for_install(r, action="skill.marketplace", base=os.path.basename(d))
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
    ctx.register_command("skills-search", handler=_handle_search,
                         description="Search the skills DB + installed skill trees by keyword.",
                         args_hint="<query>")
    ctx.register_command("skills-list", handler=_handle_list,
                         description="List all XOMNI plugins and their hook posture.",
                         args_hint="")
    ctx.register_command("xomni-status", handler=_handle_status,
                         description="XOMNI environment summary: plugins, skills, data, models.",
                         args_hint="")
    ctx.register_command("skills-install", handler=_handle_install,
                         description="Install a skill or marketplace (SKILL.md interop) into the skills surface.",
                         args_hint="<dir> [--yes] [--target=...] [--dry-run]")
    ctx.register_command("skills-marketplace", handler=_handle_marketplace,
                         description="Install every skill from a git marketplace URL (https/git, shallow clone, cached) or a local repo dir.",
                         args_hint="<url-or-dir> [--yes] [--target=...] [--dry-run]")
    ctx.register_command("skills-publish", handler=_handle_publish,
                         description="Credit-stamp (author/source/published_at/origin, idempotent) a skill then delegate the publish to the host CLI (hermes skills publish --to github|clawhub); repo-copy fallback only when the host CLI is missing.",
                         args_hint="<dir> [--yes] [--author=NAME] [--repo=<target-repo-dir>] [--to=github|clawhub] [--dry-run]")
    ctx.register_tool("skills_import", toolset="skills", schema=TOOL_SCHEMA,
                      handler=_tool_skills_import,
                      description="Import SKILL.md skills (single dir or marketplace) into the Hermes skills surface, fail-closed.")
