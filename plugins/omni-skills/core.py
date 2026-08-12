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
import subprocess

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


def scan_skills(root: str, recursive: bool = False) -> list[dict]:
    """Inventory every SKILL.md under root (top-level skill dirs only, or
    any depth when recursive=True — root itself included)."""
    found = []
    if not os.path.isdir(root):
        return found
    if recursive:
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d != ".git"]  # never descend into .git
            if "SKILL.md" in names:
                meta = skill_meta(base)
                if meta:
                    meta["dir"] = os.path.abspath(base)
                    found.append(meta)
        found.sort(key=lambda m: m["dir"])
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


def install_marketplace(root: str, target_root: str, dry_run: bool = False,
                        recursive: bool = False) -> dict:
    """Install every skill dir in a marketplace repo root. Fail-closed per skill."""
    results = []
    for meta in scan_skills(root, recursive=recursive):
        r = install_skill(meta["dir"], target_root, dry_run=dry_run)
        r["name"] = meta["name"]
        results.append(r)
    ok = [r for r in results if r["ok"]]
    rejected = [r for r in results if not r["ok"]]
    return {"ok": len(ok) > 0, "installed": len(ok), "rejected": len(rejected),
            "results": results, "dry_run": dry_run}


# ------------------------------------------------------------------ git marketplace
CACHE_ROOT = os.path.expanduser("~/.xomni-marketplaces")

# Shell metacharacters + whitespace are never legal inside a git URL we will
# pass to subprocess — reject them before anything touches the filesystem.
_URL_META = re.compile(r"[;&|`$<>\"'()\[\]{}\s\\]")


def validate_marketplace_url(url: str) -> tuple[bool, str]:
    """Fail-closed URL gate: https:// or git:// only. Returns (ok, reason)."""
    if not isinstance(url, str) or not url.strip():
        return False, "empty URL"
    u = url.strip()
    if _URL_META.search(u):
        return False, "shell metacharacters or whitespace in URL"
    if not (u.startswith("https://") or u.startswith("git://")):
        return False, "scheme must be https:// or git:// (file://, ssh, http rejected)"
    return True, ""


def _marketplace_name(url: str) -> str:
    """Cache dir name from a validated URL — last path segment, sanitized."""
    u = url.rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    name = u.rsplit("/", 1)[-1] or u
    return re.sub(r"[^A-Za-z0-9._-]", "-", name) or "marketplace"


def _git_clone(url: str, dest: str, timeout: int = 120) -> dict:
    """Shallow clone via `git clone --depth 1 -- <url> <dest>`.

    `--` stops option parsing, and the URL has already passed
    validate_marketplace_url — the argv list is never passed through a shell.
    """
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--", url, dest],
            capture_output=True, text=True, timeout=timeout,
        )
    except Exception as exc:  # FileNotFoundError, TimeoutExpired, ...
        return {"ok": False, "reason": f"git clone error: {exc}"}
    if proc.returncode != 0:
        err = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        return {"ok": False, "reason": f"git clone failed: {err[:200]}"}
    return {"ok": True}


def install_marketplace_url(url: str, target_dir: str, dry_run: bool = False,
                            cache_root: str | None = None,
                            _runner=None) -> dict:
    """Shallow-clone a git marketplace URL, then install every skill found
    (any dir with SKILL.md) into target_dir. Fail-closed: an invalid URL,
    failed clone, or unexpected error aborts before target_dir is touched,
    and any partially-cloned cache dir is removed. Valid clones are cached
    at <cache_root>/<name> (~/.xomni-marketplaces by default) and reused."""
    ok, reason = validate_marketplace_url(url)
    if not ok:
        return {"ok": False, "reason": f"invalid URL: {reason}", "url": url,
                "dry_run": dry_run}
    cache_root = cache_root or CACHE_ROOT
    cache_dir = os.path.join(cache_root, _marketplace_name(url))
    if not (os.path.isdir(cache_dir) and os.listdir(cache_dir)):
        # Fresh clone — on any failure remove the partial dir (fail-closed).
        try:
            os.makedirs(cache_root, exist_ok=True)
            r = (_runner or _git_clone)(url, cache_dir)
        except Exception as exc:
            shutil.rmtree(cache_dir, ignore_errors=True)
            return {"ok": False, "reason": f"clone error: {exc}", "url": url,
                    "dry_run": dry_run}
        if not r["ok"]:
            shutil.rmtree(cache_dir, ignore_errors=True)
            return {"ok": False, "reason": r["reason"], "url": url,
                    "dry_run": dry_run}
    try:
        res = install_marketplace(cache_dir, target_dir, dry_run=dry_run,
                                  recursive=True)
    except Exception as exc:
        return {"ok": False, "reason": f"install error: {exc}", "url": url,
                "dry_run": dry_run}
    res["url"] = url
    res["cache_dir"] = cache_dir
    return res


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


# ------------------------------------------------------------------ search
def find_xomni_home() -> str:
    """XOMNI checkout root (env XOMNI_HOME, else ../.. from the plugin dir)."""
    env = os.environ.get("XOMNI_HOME")
    if env and os.path.isdir(env):
        return env
    cand = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", ".."))
    return cand if os.path.isdir(os.path.join(cand, "plugins")) else ""


def search_skills(query: str, limit: int = 20) -> list[dict]:
    """Search curated DB (checkout) then fall back to skill trees. Returns
    [{name, rank?, category?, source?, description?}]."""
    q = (query or "").lower()
    if not q:
        return []
    hits = []
    home = find_xomni_home()
    db = os.path.join(home, "data", "curated-skills.json") if home else ""
    if db and os.path.isfile(db):
        try:
            for s in json.load(open(db, encoding="utf-8")):
                hay = " ".join(str(s.get(k, "")) for k in
                               ("name", "category", "description", "purpose",
                                "content", "source", "tags")).lower()
                if q in hay:
                    hits.append({"name": s.get("name", "?"),
                                 "rank": s.get("rank", "?"),
                                 "category": s.get("category", ""),
                                 "description": str(s.get("description", ""))[:90],
                                 "source": "curated-db"})
                    if len(hits) >= limit:
                        return hits
        except (OSError, ValueError):
            pass
    for label, root in (("hermes-skills", os.path.expanduser("~/AppData/Local/hermes/skills")),
                        ("checkout-skills", os.path.join(home, "skills") if home else "")):
        if not root or not os.path.isdir(root):
            continue
        for base, _dirs, files in os.walk(root):
            if "SKILL.md" not in files:
                continue
            path = os.path.join(base, "SKILL.md")
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if q in text.lower():
                hits.append({"name": os.path.basename(base), "rank": "",
                             "category": label, "description": "", "source": label,
                             "path": path})
                if len(hits) >= limit:
                    return hits
    return hits


def list_plugins(plugins_dir: str | None = None) -> list[dict]:
    """Inventory plugin packages -> [{name, has_hooks, tests?}]."""
    d = plugins_dir or os.path.join(find_xomni_home() or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), "plugins")
    out = []
    if not os.path.isdir(d):
        return out
    for entry in sorted(os.listdir(d)):
        p = os.path.join(d, entry)
        if not (os.path.isdir(p) and os.path.isfile(os.path.join(p, "__init__.py"))):
            continue
        src = open(os.path.join(p, "__init__.py"), encoding="utf-8", errors="ignore").read()
        out.append({"name": entry, "has_hooks": "register_hook" in src})
    return out


def env_status() -> dict:
    """XOMNI environment summary (plugins, skills, data, models)."""
    home = find_xomni_home()
    plugins = list_plugins()
    skills_count = 0
    for root in (os.path.join(home, "skills"), os.path.expanduser("~/AppData/Local/hermes/skills")):
        if os.path.isdir(root):
            skills_count += sum(1 for e in os.listdir(root)
                                if os.path.isfile(os.path.join(root, e, "SKILL.md")))
    data = {}
    for f in ("curated-skills.json", "mcps.json"):
        p = os.path.join(home, "data", f)
        if os.path.isfile(p):
            try:
                data[f] = len(json.load(open(p, encoding="utf-8")))
            except (OSError, ValueError):
                data[f] = "?"
    return {"xomni_home": home, "plugins": plugins,
            "plugins_total": len(plugins), "skills_total": skills_count, "data": data}
