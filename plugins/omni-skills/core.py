"""omni-skills core — SKILL.md interop: parse, scan, validate, install.

Pure stdlib. Zero hooks. Loads Hermes-format and foreign (SKILL.md) skills
into a target skills surface.
"""
from __future__ import annotations

import datetime
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
    try:
        shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
    except OSError as exc:  # read-only target, missing perms, ... — fail LOUD
        return {"ok": False, "reason": f"copy failed: {exc}",
                "verdict": check["verdict"], "issues": check["issues"]}
    return {"ok": True, "verdict": check["verdict"], "dest": dest, "files": [name] + meta["files"]}


def install_marketplace(root: str, target_root: str, dry_run: bool = False,
                        recursive: bool = False) -> dict:
    """Install every skill dir in a marketplace repo root. Fail-closed per skill.

    Never a silent cancel: when nothing installs, the result carries a
    ``reason`` naming why (no skills found, or every skill rejected with its
    issues).
    """
    results = []
    for meta in scan_skills(root, recursive=recursive):
        try:
            r = install_skill(meta["dir"], target_root, dry_run=dry_run)
        except Exception as exc:
            r = {"ok": False, "reason": f"install error: {exc}",
                 "name": meta["name"]}
        r["name"] = meta["name"]
        results.append(r)
    ok = [r for r in results if r["ok"]]
    rejected = [r for r in results if not r["ok"]]
    out = {"ok": len(ok) > 0, "installed": len(ok), "rejected": len(rejected),
           "results": results, "dry_run": dry_run}
    if not ok:
        if not results:
            out["reason"] = f"no SKILL.md skills found under {root}"
        else:
            detail = "; ".join(
                f"{r.get('name', '?')}: {r.get('reason', 'rejected')}"
                + (f" ({'; '.join(f for f, _ in r['issues'][:3])})"
                   if r.get("issues") else "")
                for r in rejected[:5])
            out["reason"] = (f"all {len(rejected)} skill(s) rejected: {detail}")
    return out


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


def _resolve_exe(name: str) -> str:
    """Resolve *name* to its real executable, honoring .cmd/.bat shims (Windows).

    ``shutil.which`` honors PATHEXT on Windows, so ``npx`` resolves to
    ``npx.CMD``. subprocess with shell=False CAN launch the full path to a
    .cmd/.bat shim, but the bare name raises FileNotFoundError (CreateProcess
    does no PATHEXT search). Plain .exe tools (git.exe) work bare, so we only
    substitute when a shim is actually found.
    """
    found = shutil.which(name)
    if found and os.path.splitext(found)[1].lower() in (".cmd", ".bat"):
        return found
    return name


def _git_clone(url: str, dest: str, timeout: int = 120) -> dict:
    """Shallow clone via `git clone --depth 1 -- <url> <dest>`.

    `--` stops option parsing, and the URL has already passed
    validate_marketplace_url — the argv list is never passed through a shell.
    """
    try:
        proc = subprocess.run(
            [_resolve_exe("git"), "clone", "--depth", "1", "--", url, dest],
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


# ------------------------------------------------------------------ publish
# U11 — cross-session skill market. publish_skill validates, credit-stamps,
# and copies a skill into a repo's skills/ tree — the content model of the
# skills.sh directory ('The Agent Skills Directory', https://skills.sh):
# git repos containing SKILL.md files, source = owner/repo, installable via
# `npx skills add <owner/repo>` or XOMNI's /skills-marketplace.
CREDIT_SOURCE = "xomni"


def _git_config_get(key: str, cwd: str | None = None) -> str | None:
    """`git config --get <key>` (repo-local + global), or None when unset."""
    try:
        cmd = [_resolve_exe("git"), "config", "--get", key]
        if cwd:
            cmd[1:1] = ["-C", cwd]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _origin_from_url(url: str) -> str | None:
    """Normalize a git remote URL to owner/repo — or None when it can't."""
    u = (url or "").strip()
    if not u:
        return None
    u = u.rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    parts = [p for p in re.split(r"[/:]", u) if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[-2], parts[-1]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", owner) or not re.fullmatch(r"[A-Za-z0-9._-]+", repo):
        return None
    return f"{owner}/{repo}"


def detect_origin(skill_dir: str, git_config=None) -> str | None:
    """owner/repo of the git remote the skill lives in, if detectible."""
    getter = git_config or _git_config_get
    try:
        url = str(getter("remote.origin.url", cwd=skill_dir) or "").strip()
    except Exception:
        url = ""
    return _origin_from_url(url)


def derive_author(author: str | None = None, env: dict | None = None,
                  git_config=None) -> str:
    """Publisher identity: explicit author > XOMNI_USER env > git user.name
    > git user.email > 'xomni-user'. Never empty, never None."""
    if author and str(author).strip():
        return str(author).strip()
    env = os.environ if env is None else env
    env_author = str(env.get("XOMNI_USER") or "").strip()
    if env_author:
        return env_author
    getter = git_config or _git_config_get
    for key in ("user.name", "user.email"):
        try:
            val = str(getter(key) or "").strip()
        except Exception:
            val = ""
        if val:
            return val
    return "xomni-user"


def _category_from_meta(meta: dict) -> str:
    """Market category = first frontmatter tag (sanitized), else 'general'."""
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    for t in tags:
        t = re.sub(r"[^a-z0-9._-]", "-", str(t).strip().lower())
        if t:
            return t
    return "general"


def _dir_sha256(skill_dir: str) -> str:
    """Full sha256 over every file's relative path + content in a skill dir."""
    h = hashlib.sha256()
    for base, dirs, names in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d != ".git"]
        for n in sorted(names):
            p = os.path.join(base, n)
            rel = os.path.relpath(p, skill_dir).replace("\\", "/")
            h.update(rel.encode("utf-8", "replace"))
            try:
                with open(p, "rb") as f:
                    h.update(f.read())
            except OSError:
                pass
    return h.hexdigest()


def stamp_credit(skill_dir: str, author: str | None = None,
                 published_at: str | None = None,
                 env: dict | None = None, git_config=None) -> dict:
    """Stamp CREDIT frontmatter into SKILL.md: author (publisher, derived),
    source: xomni, published_at (ISO date), origin (owner/repo if detectible).

    Idempotent — an existing xomni stamp (source + published_at present) is
    returned untouched, never double-stamped. A pre-existing ``author`` key
    naming the skill's original creator is preserved as ``original_author``
    so credit is never destroyed. Returns {ok, stamped, credit, path}."""
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return {"ok": False, "reason": "no SKILL.md", "stamped": False,
                "credit": {}, "path": path}
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
    except OSError as exc:
        return {"ok": False, "reason": f"read failed: {exc}", "stamped": False,
                "credit": {}, "path": path}
    m = FM_RE.search(text)
    if not m:
        return {"ok": False, "reason": "no frontmatter to stamp",
                "stamped": False, "credit": {}, "path": path}
    fm = parse_frontmatter(text)
    if fm.get("source") == CREDIT_SOURCE and fm.get("published_at"):
        credit = {"author": str(fm.get("author") or ""),
                  "source": CREDIT_SOURCE,
                  "published_at": str(fm.get("published_at"))}
        if fm.get("origin"):
            credit["origin"] = str(fm["origin"])
        if fm.get("original_author"):
            credit["original_author"] = str(fm["original_author"])
        return {"ok": True, "stamped": False, "credit": credit, "path": path,
                "reason": "already stamped"}
    pub = published_at or datetime.date.today().isoformat()
    publisher = derive_author(author=author, env=env, git_config=git_config)
    origin = detect_origin(skill_dir, git_config=git_config)
    credit = {"author": publisher, "source": CREDIT_SOURCE, "published_at": pub}
    if origin:
        credit["origin"] = origin
    # A pre-existing scalar `author:` naming the skill's original creator is
    # replaced in place by the publisher and preserved as original_author —
    # credit is never destroyed and the frontmatter never gets duplicate keys.
    orig = fm.get("author")
    orig = str(orig).strip() if isinstance(orig, str) else ""
    if orig and orig != publisher and "original_author" not in fm:
        credit["original_author"] = orig
    newline = "\r\n" if "\r\n" in text else "\n"
    inner = m.group(1)
    if inner.endswith("\r"):
        inner = inner[:-1]  # CRLF file: the \r before the closing \n--- is fence
    replaced = False
    rebuilt = []
    for ln in inner.split(newline):
        key, _, val = ln.partition(":")
        if key.strip() == "author" and val.strip() and not replaced:
            rebuilt.append(f'author: "{publisher}"')
            replaced = True
        else:
            rebuilt.append(ln)
    if replaced:
        inner = newline.join(rebuilt)
    extra = []
    for k in ("author", "source", "published_at", "origin", "original_author"):
        if k not in credit:
            continue
        if k == "author" and replaced:
            continue  # already written in place
        v = credit[k]
        extra.append(f"{k}: {CREDIT_SOURCE}" if k == "source"
                     else f'{k}: "{v}"')
    tail = text[m.end(1):]
    if newline == "\r\n" and tail.startswith("\n"):
        tail = "\r\n" + tail[1:]  # keep CRLF endings consistent
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text[:m.start(1)] + inner + newline + newline.join(extra)
                    + tail)
    except OSError as exc:
        return {"ok": False, "reason": f"write failed: {exc}", "stamped": False,
                "credit": {}, "path": path}
    return {"ok": True, "stamped": True, "credit": credit, "path": path}


def publish_skill(skill_dir: str, target_repo_dir: str,
                  author: str | None = None, published_at: str | None = None,
                  env: dict | None = None, git_config=None) -> dict:
    """Validate + credit-stamp + copy a skill into a repo's skills/ tree at
    <target_repo_dir>/skills/<category>/<name>/ — the skills.sh content model.

    Refuses to publish REJECT skills (reuses validate_skill, fail-closed).
    The stamp happens on the source SKILL.md (idempotent), the copy inherits
    it. Returns a receipt dict: name, sha256 (full), path, author, plus the
    stamp and the git push steps for the target repo."""
    if not os.path.isdir(skill_dir):
        return {"ok": False, "reason": f"skill dir not found: {skill_dir}"}
    check = validate_skill(skill_dir)
    if check["verdict"] == "REJECT":
        return {"ok": False, "reason": "REJECT", "verdict": "REJECT",
                "issues": check["issues"]}
    meta = skill_meta(skill_dir)
    if meta is None:
        return {"ok": False, "reason": "no SKILL.md"}
    if not meta["has_frontmatter"]:
        return {"ok": False, "reason": "no frontmatter to stamp"}
    st = stamp_credit(skill_dir, author=author, published_at=published_at,
                      env=env, git_config=git_config)
    if not st["ok"]:
        return {"ok": False, "reason": st["reason"]}
    category = _category_from_meta(meta)
    name = re.sub(r"[^a-z0-9._-]", "-", meta["name"].lower())
    dest = os.path.join(target_repo_dir, "skills", category, name)
    try:
        os.makedirs(dest, exist_ok=True)
        shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
    except OSError as exc:
        return {"ok": False, "reason": f"copy failed: {exc}"}
    return {
        "ok": True,
        "name": name,
        "category": category,
        "path": os.path.abspath(dest),
        "author": st["credit"]["author"],
        "source": st["credit"]["source"],
        "published_at": st["credit"]["published_at"],
        "origin": st["credit"].get("origin"),
        "original_author": st["credit"].get("original_author"),
        "stamped": st["stamped"],
        "sha256": _dir_sha256(dest),
        "fingerprint": fingerprint(dest),
        "git": {"repo": os.path.abspath(target_repo_dir),
                "add": f"skills/{category}/{name}",
                "commit": f"publish skill: {name}"},
    }
