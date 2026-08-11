"""omni-skills core — SKILL.md interop: parse, scan, validate, install.

Pure stdlib. Zero hooks. Loads Hermes-format and foreign (SKILL.md) skills
into a target skills surface.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil

# ------------------------------------------------------------------ frontmatter
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S | re.M)


def parse_frontmatter(text: str) -> dict:
    """Parse the YAML-subset frontmatter used by SKILL.md files.

    Handles `key: value` scalars and `key: [a, b]` / block `- item` lists.
    Never raises on malformed input — returns what it could parse.
    """
    m = FM_RE.search(text)
    if not m:
        return {}
    out = {}
    block_list_key = None
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if block_list_key:
                out.setdefault(block_list_key, []).append(line[2:].strip().strip('"').strip("'"))
            continue
        block_list_key = None
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            out[key] = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
        elif val == "":
            block_list_key = key
            out[key] = []
        else:
            out[key] = val.strip('"').strip("'")
    return out


def skill_meta(skill_dir: str) -> dict:
    """Read a skill directory -> {name, description, version, license, tags,
    files, frontmatter_raw}. Returns None keys for missing pieces."""
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    fm = parse_frontmatter(text)
    files = []
    for base, _dirs, names in os.walk(skill_dir):
        for n in sorted(names):
            if n == "SKILL.md":
                continue
            rel = os.path.relpath(os.path.join(base, n), skill_dir).replace("\\", "/")
            files.append(rel)
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    return {
        "name": fm.get("name") or os.path.basename(skill_dir.rstrip("/\\")),
        "description": fm.get("description") or "",
        "version": fm.get("version") or "",
        "license": fm.get("license") or "",
        "tags": tags or [],
        "files": files,
        "frontmatter_raw": m.group(1) if (m := FM_RE.search(text)) else "",
        "has_frontmatter": bool(FM_RE.search(text)),
    }


def scan_skills(root: str) -> list[dict]:
    """Inventory every SKILL.md under root (top-level skill dirs only)."""
    found = []
    if not os.path.isdir(root):
        return found
    for entry in sorted(os.listdir(root)):
        d = os.path.join(root, entry)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "SKILL.md")):
            meta = skill_meta(d)
            if meta:
                meta["dir"] = os.path.abspath(d)
                found.append(meta)
    return found


# ------------------------------------------------------------------ validation
DANGEROUS_PATTERNS = [
    (re.compile(r"\.\./|\.\.\\"), "path escape"),
    (re.compile(r"(?i)(rm\s+-rf|format\s+[a-z]:|del\s+/[fsq])"), "destructive command"),
    (re.compile(r"(?i)base64.*-d\s|powershell.*-enc|cmd\.exe\s+/c\s+.*\bdel\b"), "obfuscated exec"),
]


def validate_skill(skill_dir: str) -> dict:
    """Security-check a skill dir before install. Returns
    {ok, verdict, issues: [(file, reason)]} — fail-closed."""
    issues = []
    meta = skill_meta(skill_dir)
    if meta is None:
        return {"ok": False, "verdict": "REJECT", "issues": [("SKILL.md", "missing")]}
    if not meta["has_frontmatter"]:
        issues.append(("SKILL.md", "no frontmatter"))
    if not meta["name"] or not meta["description"]:
        issues.append(("SKILL.md", "missing name/description"))
    # SKILL.md itself is scanned too — a skill's instructions can carry
    # destructive/obfuscated content, not just its support files.
    scan_targets = ["SKILL.md"] + meta["files"]
    for rel in scan_targets:
        p = os.path.join(skill_dir, rel.replace("/", os.sep))
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            issues.append((rel, "unreadable"))
            continue
        for pat, reason in DANGEROUS_PATTERNS:
            if pat.search(content):
                issues.append((rel, reason))
    verdict = "PASS" if not issues else ("REVIEW" if len(issues) <= 2 else "REJECT")
    return {"ok": verdict == "PASS", "verdict": verdict, "issues": issues}


# ------------------------------------------------------------------ install
def install_skill(skill_dir: str, target_root: str, dry_run: bool = False) -> dict:
    """Copy a skill dir into target_root/<name>/ — validated first.
    dry_run returns the plan without writing."""
    meta = skill_meta(skill_dir)
    if meta is None:
        return {"ok": False, "reason": "no SKILL.md"}
    check = validate_skill(skill_dir)
    if check["verdict"] == "REJECT":
        return {"ok": False, "reason": "REJECT", "issues": check["issues"]}
    name = re.sub(r"[^a-z0-9._-]", "-", meta["name"].lower())
    dest = os.path.join(target_root, name)
    if dry_run:
        return {"ok": True, "verdict": check["verdict"], "dest": dest,
                "files": [name] + meta["files"], "dry_run": True}
    os.makedirs(dest, exist_ok=True)
    shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
    return {"ok": True, "verdict": check["verdict"], "dest": dest, "files": [name] + meta["files"]}


def install_marketplace(root: str, target_root: str, dry_run: bool = False) -> dict:
    """Install every skill dir in a marketplace repo root. Fail-closed per skill."""
    results = []
    for meta in scan_skills(root):
        r = install_skill(meta["dir"], target_root, dry_run=dry_run)
        r["name"] = meta["name"]
        results.append(r)
    ok = [r for r in results if r["ok"]]
    rejected = [r for r in results if not r["ok"]]
    return {"ok": len(ok) > 0, "installed": len(ok), "rejected": len(rejected),
            "results": results, "dry_run": dry_run}


def fingerprint(skill_dir: str) -> str:
    """Content hash of SKILL.md + support files — for dedupe/change detection."""
    h = hashlib.sha256()
    meta = skill_meta(skill_dir)
    if meta is None:
        return ""
    h.update(meta["frontmatter_raw"].encode("utf-8", "replace"))
    for rel in meta["files"]:
        p = os.path.join(skill_dir, rel.replace("/", os.sep))
        try:
            with open(p, "rb") as f:
                h.update(rel.encode())
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()[:16]
