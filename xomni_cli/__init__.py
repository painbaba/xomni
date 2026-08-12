"""xomni — the XOMNI CLI.

One agent. Every feature. Every free model.

Installed via ``pip install .`` from the repo root. Commands:

  xomni                      launch the host (Hermes with XOMNI plugins)
  xomni plugins list         list the 23 plugins + test counts
  xomni plugins install [n]  copy plugin dirs into the Hermes plugins dir
  xomni skill search <q>     search skills (DB in checkout, else installed tree)
  xomni skill install <dir>  install a SKILL.md skill/marketplace (fail-closed)
  xomni providers            provider coverage table (all Hermes providers)
  xomni doctor               environment health check
  xomni stacks               list one-command vertical stacks
  xomni add <stack>          install a stack's MCPs by appending host config
                             (--yes/-y no-prompt guarantee; --dry-run preview,
                             --smoke live check)
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(ROOT, "plugins")
SKILLS_DIR = os.path.join(ROOT, "skills")
DATA_DIR = os.path.join(ROOT, "data")

HERMES_HOME = os.environ.get("HERMES_HOME",
                             os.path.expanduser("~/AppData/Local/hermes"))
HERMES_PLUGINS_DIR = os.path.join(HERMES_HOME, "plugins")
HERMES_SKILLS_DIR = os.path.join(HERMES_HOME, "skills")

# Canonical Hermes provider catalog (env var | base_url | notes) — the full set
# Hermes supports; connect any of them via config.yaml + .env.
PROVIDERS = [
    ("Zen gateway (opencode.ai)", "OPENCODE_GO_API_KEY", "https://opencode.ai/zen/go/v1",
     "25 verified free models — the XOMNI default"),
    ("OpenRouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1",
     "all models incl. :free tier; BYO-key"),
    ("Anthropic (Claude)", "ANTHROPIC_API_KEY", "https://api.anthropic.com",
     "claude-* models; ANTHROPIC_BASE_URL override"),
    ("OpenAI", "OPENAI_API_KEY", "https://api.openai.com/v1",
     "gpt-*; OPENAI_BASE_URL override"),
    ("Google AI Studio (Gemini)", "GOOGLE_API_KEY", "https://generativelanguage.googleapis.com/v1beta",
     "gemini-3.6-flash family incl. vision; AI Studio keys"),
    ("DeepSeek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1",
     "deepseek-chat/reasoner"),
    ("xAI (Grok)", "XAI_API_KEY", "https://api.x.ai/v1",
     "grok-* models"),
    ("Groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1",
     "fast open-weight inference: llama-*, qwen-*"),
    ("Mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1",
     "mistral-* models"),
    ("Together AI", "TOGETHER_API_KEY", "https://api.together.xyz/v1",
     "open-weights hosting"),
    ("Fireworks AI", "FIREWORKS_API_KEY", "https://api.fireworks.ai/inference/v1",
     "open-weights hosting"),
    ("Cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1",
     "fast inference"),
    ("Azure OpenAI", "AZURE_OPENAI_API_KEY", "https://<res>.openai.azure.com/",
     "enterprise; AZURE_OPENAI_ENDPOINT + api-version"),
    ("Nous Portal", "NOUS_PORTAL_API_KEY", "https://portal.nousresearch.com/v1",
     "Nous models; OAuth alternative"),
    ("OpenAI-compatible local (Ollama)", "XOMNI_OLLAMA", "http://127.0.0.1:11434/v1",
     "qwen2.5:3b etc.; zero-install via ollama/start-ollama.ps1"),
    ("OpenAI-compatible local (LM Studio)", "LMSTUDIO", "http://127.0.0.1:1234/v1",
     "any GGUF model"),
    ("OpenAI-compatible custom", "CUSTOM_API_KEY", "any https base_url",
     "BYO-provider: any OpenAI-compatible endpoint via config.yaml"),
    # India channels (backlog 08) — see docs/PROVIDERS.md → "India channels"
    ("Sarvam AI (India)", "SARVAM_API_KEY", "https://api.sarvam.ai",
     "100 free credits on signup; Sarvam-105B/30B chat, TTS bulbul:v3 (11 Indic langs), ASR"),
    ("Bhashini (MeitY, India)", "BHASHINI_API_KEY", "https://api.bhashini.gov.in",
     "gov ASR/TTS/MT 22+ langs; registration-gated (userid + subscription-id)"),
    ("Krutrim Cloud (Ola, India)", "KRUTRIM_API_KEY", "https://cloud.olakrutrim.com/v1",
     "OpenAI-compatible; INR billing, India data residency; free start, no card"),
]

PLUGIN_TESTS = {  # from docs/TEST-MATRIX.md
    "context-compact": 31, "context-loader": 69, "gh-ops": 99, "local-models": 87,
    "mcp-catalog": 26, "omni-design": 8, "omni-media": 27, "omni-memory": 26,
    "omni-parallel": 20, "omni-skills": 17, "perkline": 27, "provider-pool": 36,
    "repomap": 42, "sandbox-gate": 67, "title-statusline": 32, "verify-runner": 38,
    "waitperk": 34, "omni-registry": 15, "codebase-index": 18, "omni-tools": 18,
    "bharat-pack": 12, "cost-tracker": 14, "receipts": 16,
}


def _plugins() -> list[str]:
    """Plugin names: from the checkout plugins/ dir, else from installed packages."""
    if os.path.isdir(PLUGINS_DIR):
        return sorted(p for p in os.listdir(PLUGINS_DIR)
                      if os.path.isdir(os.path.join(PLUGINS_DIR, p))
                      and os.path.isfile(os.path.join(PLUGINS_DIR, p, "__init__.py")))
    import importlib.util
    found = []
    for name in sorted(PLUGIN_TESTS):
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            spec = None
        if spec and spec.submodule_search_locations:
            found.append(name)
    return found


def _plugin_dir(name: str) -> str:
    """Resolve a plugin's directory (checkout or installed site-packages)."""
    if os.path.isdir(PLUGINS_DIR):
        d = os.path.join(PLUGINS_DIR, name)
        return d if os.path.isdir(d) else ""
    import importlib.util
    spec = importlib.util.find_spec(name)
    if spec and spec.submodule_search_locations:
        return list(spec.submodule_search_locations)[0]
    return ""


def cmd_plugins_list() -> int:
    print(f"XOMNI plugins ({len(_plugins())}):")
    for name in _plugins():
        tests = PLUGIN_TESTS.get(name, "?")
        has_hooks = "hooks" if os.path.exists(os.path.join(PLUGINS_DIR, name, "__init__.py")) and \
            "register_hook" in open(os.path.join(PLUGINS_DIR, name, "__init__.py"),
                                    encoding="utf-8", errors="ignore").read() else "zero-hooks"
        print(f"  {name:<20} {tests:>4} tests  {has_hooks}")
    return 0


def cmd_plugins_install(names: list[str]) -> int:
    if not os.path.isdir(HERMES_PLUGINS_DIR):
        os.makedirs(HERMES_PLUGINS_DIR)
    # --yes / -y: accepted everywhere (U3 — non-interactive; no prompt exists,
    # and the flag guarantees none is ever shown). Any mutating CLI command
    # must accept it and never block on a prompt.
    targets = [n for n in names if n not in ("--yes", "-y")]
    if not targets:
        targets = _plugins()
    ok = 0
    failed = 0
    for name in targets:
        src = _plugin_dir(name)
        if not src:
            print(f"  ! failed: {name}: unknown plugin (not in {PLUGINS_DIR})")
            failed += 1
            continue
        try:
            shutil.copytree(src, os.path.join(HERMES_PLUGINS_DIR, name), dirs_exist_ok=True)
        except OSError as exc:
            print(f"  ! failed: {name}: {exc}")
            failed += 1
            continue
        print(f"  installed: {name} -> {HERMES_PLUGINS_DIR}")
        _receipt_file("plugin.install",
                      os.path.join(HERMES_PLUGINS_DIR, name, "__init__.py"),
                      f"installed {name} -> {HERMES_PLUGINS_DIR}",
                      {"plugin": name, "source": src})
        ok += 1
    if failed:
        print(f"{ok} plugin(s) installed, {failed} FAILED ({', '.join(targets)}). "
              "Restart the host after a successful re-run.")
        return 1
    print(f"{ok} plugin(s) installed. Restart the host to load them.")
    return 0


def _search_curated_db(query: str) -> list[dict]:
    """Search data/curated-skills.json when running from a checkout."""
    path = os.path.join(DATA_DIR, "curated-skills.json")
    if not os.path.isfile(path):
        return []
    q = query.lower()
    out = []
    for s in json.load(open(path, encoding="utf-8")):
        hay = " ".join(str(s.get(k, "")) for k in ("name", "category", "description",
                                                   "purpose", "content", "source")).lower()
        if q in hay:
            out.append(s)
    return out


def _search_skill_tree(root: str, query: str) -> list[dict]:
    q = query.lower()
    hits = []
    if not os.path.isdir(root):
        return hits
    for base, _dirs, files in os.walk(root):
        if "SKILL.md" not in files:
            continue
        path = os.path.join(base, "SKILL.md")
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if q in text.lower():
            name = os.path.basename(base)
            hits.append({"name": name, "path": path,
                         "description": (text.split("description:", 1)[1][:100]
                                         if "description:" in text else "")})
    return hits


def cmd_skill_search(query: str) -> int:
    if not query:
        print("usage: xomni skill search <query>")
        return 1
    hits = _search_curated_db(query)
    print(f"SKILL SEARCH \"{query}\" — {len(hits)} curated DB hits"
          + (" (from checkout data/)" if hits else " (no checkout data/ — scanning trees)"))
    for s in hits[:20]:
        print(f"  {s.get('name','?'):<32} rank {s.get('rank','?')}  {s.get('category','')}")
    if not hits:
        for label, root in (("hermes-skills", HERMES_SKILLS_DIR), ("checkout-skills", SKILLS_DIR)):
            tree = _search_skill_tree(root, query)
            print(f"  {label}: {len(tree)} hit(s)")
            for t in tree[:10]:
                print(f"    {t['name']:<30} {t['path']}")
    return 0


def _load_omni_skills_core():
    """Load plugins/omni-skills/core.py (checkout, dashed dir) or the installed package."""
    import importlib.util
    p = os.path.join(PLUGINS_DIR, "omni-skills", "core.py")
    if not os.path.isfile(p):
        # installed mode: dashed dirs resolve via find_spec, not `import`
        spec = importlib.util.find_spec("omni-skills")
        if spec and spec.submodule_search_locations:
            p = os.path.join(list(spec.submodule_search_locations)[0], "core.py")
    if not os.path.isfile(p):
        raise ImportError("omni-skills core not found (checkout or installed)")
    fspec = importlib.util.spec_from_file_location("omni_skills_core", p)
    mod = importlib.util.module_from_spec(fspec)
    sys.modules["omni_skills_core"] = mod
    fspec.loader.exec_module(mod)
    return mod


def _load_receipts_core():
    """Load plugins/receipts/core.py (checkout or installed) — None on failure.

    Receipts-by-default (U7): the ledger is optional — when unavailable,
    every mutating command behaves exactly as before.
    """
    import importlib.util
    p = os.path.join(PLUGINS_DIR, "receipts", "core.py")
    if not os.path.isfile(p):
        try:
            spec = importlib.util.find_spec("receipts")
        except (ImportError, ValueError):
            spec = None
        if spec and spec.submodule_search_locations:
            p = os.path.join(list(spec.submodule_search_locations)[0], "core.py")
    if not os.path.isfile(p):
        return None
    fspec = importlib.util.spec_from_file_location("receipts_core", p)
    mod = importlib.util.module_from_spec(fspec)
    sys.modules["receipts_core"] = mod
    try:
        fspec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _receipt_file(action: str, target: str, result: str, meta: dict | None = None):
    """Issue a sha256-handled receipt; never raises, never breaks the caller."""
    mod = _load_receipts_core()
    if mod is None:
        return None
    try:
        return mod.try_file_receipt(action, target, result, meta)
    except Exception:
        return None


def _receipt_skill_install(r: dict) -> int:
    """Issue one sha256-handled receipt per installed skill (never raises)."""
    if not r or not r.get("ok"):
        return 0
    n = 0
    results = r.get("results")
    if results:  # marketplace: one receipt per installed skill
        for res in results:
            if res.get("ok") and res.get("dest"):
                if _receipt_file("skill.install",
                                 os.path.join(res["dest"], "SKILL.md"),
                                 f"{res.get('verdict', 'OK')} {res.get('name', '')}",
                                 {"skill": res.get("name", "")}):
                    n += 1
        return n
    dest = r.get("dest")
    if dest:
        if _receipt_file("skill.install", os.path.join(dest, "SKILL.md"),
                         r.get("verdict", "OK"),
                         {"skill": os.path.basename(dest)}):
            n += 1
    return n


def cmd_skill_install(path: str) -> int:
    """Install a SKILL.md skill or marketplace dir into the Hermes skills dir (fail-closed).

    Accepts --yes / -y (U3 — non-interactive); every failure prints the cause
    and exits non-zero. Never prompts.
    """
    path = (path or "").strip()
    for flag in ("--yes", "-y"):
        if path == flag or path.startswith(flag + " "):
            path = path[len(flag):].strip()
    if not path or not os.path.isdir(path):
        print(f"usage: xomni skill install <dir>  ({path!r} is not a directory)")
        return 1
    omni_skills_core = _load_omni_skills_core()
    os.makedirs(HERMES_SKILLS_DIR, exist_ok=True)
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        r = omni_skills_core.install_skill(path, HERMES_SKILLS_DIR)
        if not r.get("ok"):
            print(f"FAILED — {r.get('reason', 'install failed')}")
            for f, reason in r.get("issues", []):
                print(f"  ! {f}: {reason}")
            return 1
        print(f"  {r['verdict'] if 'verdict' in r else '?'} -> {r.get('dest', '?')}")
        _receipt_skill_install(r)
        return 0
    r = omni_skills_core.install_marketplace(path, HERMES_SKILLS_DIR)
    print(f"  {r['installed']} installed, {r['rejected']} rejected -> {HERMES_SKILLS_DIR}")
    if not r["ok"]:
        print(f"FAILED — {r.get('reason', 'nothing installed')}")
        return 1
    _receipt_skill_install(r)
    return 0


def cmd_providers() -> int:
    print(f"XOMNI PROVIDERS — {len(PROVIDERS)} channels (connect any via config.yaml + .env):")
    print(f"  {'provider':<40} {'env var':<26} base_url")
    for name, env, base, _note in PROVIDERS:
        print(f"  {name:<40} {env:<26} {base}")
    print("\nHow to connect: set the key in ~/AppData/Local/hermes/.env, then add a")
    print("providers.<id> block in config.yaml (see docs/PROVIDERS.md).")
    return 0


def cmd_doctor() -> int:
    issues = 0
    print(f"XOMNI DOCTOR  (XOMNI_HOME={ROOT})")
    hermes = shutil.which("hermes")
    print(f"  hermes binary : {'OK: ' + str(hermes) if hermes else 'MISSING — install Hermes first'}")
    issues += 0 if hermes else 1
    print(f"  plugins       : {len(_plugins())} in checkout; "
          f"{len(os.listdir(HERMES_PLUGINS_DIR)) if os.path.isdir(HERMES_PLUGINS_DIR) else 0} installed")
    print(f"  skills dir    : {HERMES_SKILLS_DIR} {'exists' if os.path.isdir(HERMES_SKILLS_DIR) else 'absent'}")
    for env in ("OPENCODE_GO_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(env)
        if val:
            print(f"  {env:<26} set")
    env_file = os.path.join(HERMES_HOME, ".env")
    if os.path.isfile(env_file):
        found = [l.split("=")[0] for l in open(env_file, encoding="utf-8", errors="ignore")
                 if "=" in l and "KEY" in l]
        print(f"  .env keys     : {len(found)} key(s) present")
    print("  verdict       : " + ("OK" if not issues else "fix issues above"))
    return issues


def _resolve_exe(name: str) -> str:
    """Resolve *name* to its real executable, honoring .cmd/.bat shims (Windows).

    shutil.which honors PATHEXT on Windows, so npx resolves to npx.CMD.
    subprocess with shell=False CAN launch the full path to a .cmd/.bat shim,
    but the bare name raises FileNotFoundError (CreateProcess does no PATHEXT
    search). Plain .exe tools (hermes.exe) work bare, so we only substitute
    when a shim is actually found.
    """
    found = shutil.which(name)
    if found and os.path.splitext(found)[1].lower() in (".cmd", ".bat"):
        return found
    return name


# ---------------------------------------------------------------------------
# Vertical stacks — `xomni add <stack>` (U1). One command installs a curated
# set of MCP servers by APPENDING to the host's config.yaml mcp_servers block
# (never invoking the interactive `hermes mcp add`). Stack defs: data/stacks/
# ---------------------------------------------------------------------------
STACKS_DIR = os.path.join(DATA_DIR, "stacks")
MCP_CATALOG = os.path.join(DATA_DIR, "mcp", "catalog.json")
CURATED_SKILLS = os.path.join(DATA_DIR, "curated-skills.json")


def _resolve_data_dir() -> str:
    """Checkout data/ first, else the packaged site-packages copy (installed mode)."""
    if os.path.isdir(DATA_DIR):
        return DATA_DIR
    # pip records where a local install came from (direct_url.json)
    try:
        import json
        from importlib import metadata
        dist = metadata.distribution("xomni")
        for f in dist.files or ():
            if f.name == "direct_url.json":
                path = os.path.join(str(dist.locate_file("")), str(f))
                info = json.load(open(path, encoding="utf-8"))
                url = info.get("url", "")
                if url.startswith("file://"):
                    repo = url[len("file://"):].lstrip("/").replace("/", os.sep)
                    if os.path.isdir(os.path.join(repo, "data")):
                        return os.path.join(repo, "data")
    except Exception:
        pass
    env = os.environ.get("XOMNI_HOME")
    if env and os.path.isdir(os.path.join(env, "data")):
        return os.path.join(env, "data")
    pkg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "xomni", "data")
    return pkg if os.path.isdir(pkg) else DATA_DIR

STACKS_DIR = os.path.join(_resolve_data_dir(), "stacks")
MCP_CATALOG = os.path.join(_resolve_data_dir(), "mcp", "catalog.json")
CURATED_SKILLS = os.path.join(_resolve_data_dir(), "curated-skills.json")


def _config_path() -> str:
    """Host config.yaml: XOMNI_HERMES_CONFIG override, else HERMES_HOME/config.yaml."""
    return os.environ.get("XOMNI_HERMES_CONFIG",
                          os.path.join(HERMES_HOME, "config.yaml"))


def _load_catalog() -> dict:
    """MCP catalog as {name: entry} from data/mcp/catalog.json."""
    if not os.path.isfile(MCP_CATALOG):
        raise FileNotFoundError(f"MCP catalog missing: {MCP_CATALOG}")
    return {e["name"]: e for e in json.load(open(MCP_CATALOG, encoding="utf-8"))}


def _list_stacks() -> list[str]:
    """Stack ids = data/stacks/*.json filename stems."""
    if not os.path.isdir(STACKS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(STACKS_DIR) if f.endswith(".json"))


def _load_stack(name: str) -> dict:
    """Load one stack def by id. Raises ValueError if unknown."""
    path = os.path.join(STACKS_DIR, name + ".json")
    if not os.path.isfile(path):
        raise ValueError(f"unknown stack: {name!r} "
                         f"(available: {', '.join(_list_stacks()) or 'none'})")
    return json.load(open(path, encoding="utf-8"))


def _parse_install_command(ic: str) -> dict:
    """Turn a catalog install_command into a non-interactive host config entry.

    stdio servers -> {command, args}; hosted/Smithery/`hermes mcp add --url`
    -> {url}; `pip install X` -> uvx X (the server package's CLI entry point);
    anything multi-step/manual -> ValueError (fail loudly, never prompt, and
    never invoke the interactive `hermes mcp add`).
    """
    ic = (ic or "").strip()
    if not ic or ic.startswith("see repo"):
        raise ValueError("install_command is 'see repo' — manual setup required, "
                         "cannot auto-install non-interactively")
    if ic.startswith("hermes mcp add"):
        m = re.search(r"--url\s+(\S+)", ic)
        if not m:
            raise ValueError(f"interactive flow, no --url to write: {ic!r}")
        return {"url": m.group(1)}
    if ic.startswith("npx -y @smithery/cli mcp add"):
        url = ic.split()[-1]
        if url.startswith("http"):
            return {"url": url}
        raise ValueError(f"cannot parse hosted URL from: {ic!r}")
    if ic.startswith("pip install "):
        pkg = ic[len("pip install "):].strip().split()[0]
        return {"command": "uvx", "args": [pkg]}
    first = ic.split()[0]
    if "&&" in ic or first in ("git", "docker", "npm", "brew", "copilot"):
        raise ValueError(f"multi-step/container install not automatable: {ic!r}")
    parts = shlex.split(ic)
    if not parts:
        raise ValueError(f"empty install_command: {ic!r}")
    return {"command": parts[0], "args": parts[1:]}


def _resolve_mcp(name: str, catalog: dict) -> dict:
    """Resolve a catalog MCP name to a host config entry (enabled by default)."""
    entry = catalog.get(name)
    if not entry:
        raise ValueError(f"unknown MCP server in catalog: {name!r}")
    try:
        cfg = _parse_install_command(entry.get("install_command", ""))
    except ValueError as exc:
        raise ValueError(f"MCP {name!r}: {exc}") from exc
    cfg.setdefault("enabled", True)
    return cfg


def _yaml_block(name: str, cfg: dict) -> str:
    """Render one mcp_servers entry as YAML text at indent 2 (host schema:
    {command, args} for stdio, {url} for HTTP transport, + enabled flag)."""
    import yaml

    def scalar(v):
        # safe_dump appends a '...' document-end marker — strip it
        return yaml.safe_dump(v, default_flow_style=False).split("\n...")[0].strip()

    key = scalar(name)
    lines = [f"  {key}:"]
    for k, v in cfg.items():
        if k == "args" and isinstance(v, list):
            lines.append("    args:")
            for a in v:
                lines.append(f"      - {scalar(a)}")
        else:
            lines.append(f"    {k}: {scalar(v)}")
    return "\n".join(lines)


def _existing_mcp_names(text: str) -> set:
    """Names already defined under the mcp_servers: block (indent-2 keys)."""
    names, in_block = set(), False
    for line in text.splitlines():
        if not in_block:
            if re.match(r"^mcp_servers:", line):
                in_block = True
            continue
        if line and not line[0].isspace():
            break  # next top-level key
        m = re.match(r"^ {2}(\S[^:]*):", line)
        if m:
            names.add(m.group(1).strip().strip("\"'\n"))
    return names


def _append_mcp_servers(config_path: str, entries: list[tuple[str, dict]]) -> tuple[int, list[str]]:
    """Append (name, cfg) entries into config.yaml's mcp_servers block.

    Returns (added, skipped) where skipped are names already present. Fails
    loudly with the exact fix when the file is missing or read-only. Textual
    insert — the rest of the config (comments, ordering, other sections) is
    preserved untouched.
    """
    if not os.path.isfile(config_path):
        raise OSError(
            f"config.yaml not found at {config_path} — the host config must exist.\n"
            f"Fix: run `hermes setup` (or `hermes mcp add <name>` once) to create it, "
            f"then re-run `xomni add <stack>`.")
    text = open(config_path, encoding="utf-8").read()
    existing = _existing_mcp_names(text)
    pending = [(n, c) for n, c in entries if n not in existing]
    skipped = [n for n, _ in entries if n in existing]
    if not pending:
        return 0, skipped
    blocks = [_yaml_block(n, c) for n, c in pending]
    lines = text.splitlines()
    idx = next((i for i, l in enumerate(lines) if re.match(r"^mcp_servers:", l)), None)
    if idx is None:
        new_text = text.rstrip("\n") + "\n\nmcp_servers:\n" + "\n".join(blocks) + "\n"
    else:
        # `mcp_servers: {}` / `mcp_servers: []` (empty inline container) is a
        # valid YAML idiom but cannot hold block entries — expand it to a bare
        # key first, mirroring the mcp-catalog plugin's host-config writer.
        if re.search(r":\s*(\{\s*\}|\[\s*\])\s*(#.*)?$", lines[idx]):
            lines[idx] = "mcp_servers:"
        new_text = "\n".join(lines[:idx + 1] + blocks + lines[idx + 1:]) \
            + ("\n" if text.endswith("\n") else "")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except (PermissionError, OSError) as exc:
        raise OSError(
            f"config.yaml is not writable: {config_path} ({exc}).\n"
            f"Fix: uncheck Read-only in the file's properties (or run as administrator), "
            f"then re-run `xomni add <stack>`.") from exc
    return len(pending), skipped


def _run_smoke(sdef: dict) -> int:
    """Run the stack's smoke_test command and check expect appears in output."""
    cfg = sdef["smoke_test"]
    print(f"  SMOKE: {cfg['command']}")
    try:
        r = subprocess.run(shlex.split(cfg["command"]), shell=False,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  SMOKE FAILED — could not run: {exc}")
        return 1
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    ok = r.returncode == 0 and cfg["expect"] in out
    print(out[:2000])
    print(f"  SMOKE {'PASS' if ok else 'FAIL'} (expect {cfg['expect']!r} in output, "
          f"exit={r.returncode})")
    return 0 if ok else 1


def cmd_add(stack: str, dry_run: bool = False, smoke: bool = False,
            yes: bool = False) -> int:
    """`xomni add <stack>` — validate the stack def, print the plan, then
    install its MCP servers by appending host config (non-interactive).

    --yes / -y (U3 — non-interactive): accepted and stripped; the command
    never prompts, and the flag guarantees no confirmation is ever shown.
    --dry-run only prints the plan; --smoke also runs the stack's live smoke
    test (public API curl, expect-code match)."""
    try:
        sdef = _load_stack(stack)
        catalog = _load_catalog()
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1
    errors: list[str] = []
    skills = sdef.get("skills", [])
    if os.path.isfile(CURATED_SKILLS):
        known = {x["name"] for x in json.load(open(CURATED_SKILLS, encoding="utf-8"))}
        for sk in skills:
            if sk not in known:
                errors.append(f"skill not in data/curated-skills.json: {sk!r}")
    mcps: list[tuple[str, dict]] = []
    for m in sdef.get("mcp_servers", []):
        try:
            mcps.append((m, _resolve_mcp(m, catalog)))
        except ValueError as exc:
            errors.append(str(exc))
    smoke_cfg = sdef.get("smoke_test") or {}
    if not smoke_cfg.get("command") or not smoke_cfg.get("expect"):
        errors.append(f"stack {stack!r}: smoke_test must define command + expect")
    if errors:
        print(f"ERROR: stack {stack!r} failed validation:")
        for e in errors:
            print(f"  ! {e}")
        return 1
    config_path = _config_path()
    print(f"STACK: {sdef.get('name')} — {sdef.get('description')}")
    print(f"  skills ({len(skills)}): {', '.join(skills)}")
    print(f"  MCPs ({len(mcps)}): {', '.join(m for m, _ in mcps)}")
    print(f"  host config: {config_path}")
    if dry_run:
        print(f"  DRY-RUN — would append {len(mcps)} MCP server(s) to mcp_servers "
              f"(no write)")
        return _run_smoke(sdef) if smoke else 0
    try:
        added, skipped = _append_mcp_servers(config_path, mcps)
    except OSError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"  wrote {added} MCP server(s) to mcp_servers"
          + (f" (skipped {len(skipped)} already present: {', '.join(skipped)})"
             if skipped else ""))
    if added:
        _receipt_file("stack.add", config_path,
                      f"added {added} MCP server(s) from stack {stack!r}",
                      {"stack": stack, "mcps": [m for m, _ in mcps]})
    print("  restart the host (or /reload-mcp) to load them")
    return _run_smoke(sdef) if smoke else 0


def cmd_stacks() -> int:
    """`xomni stacks` — list available one-command vertical stacks."""
    print("XOMNI STACKS — one-command vertical installs: xomni add <stack> [--dry-run] [--smoke]")
    for name in _list_stacks():
        try:
            sdef = _load_stack(name)
        except (ValueError, OSError) as exc:
            print(f"  {name:<20} (unreadable: {exc})")
            continue
        print(f"  {name:<20} {len(sdef.get('skills', [])):>2} skills, "
              f"{len(sdef.get('mcp_servers', [])):>2} MCPs — "
              f"{sdef.get('description', '')[:60]}")
    return 0


def main(argv=None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if not args else 0
    cmd = args.pop(0)
    if cmd == "plugins" and args and args[0] == "list":
        return cmd_plugins_list()
    if cmd == "plugins" and args and args[0] == "install":
        return cmd_plugins_install(args[1:])
    if cmd == "plugins":
        return cmd_plugins_list()
    if cmd == "skill" and args and args[0] == "search":
        return cmd_skill_search(" ".join(args[1:]))
    if cmd == "skill" and args and args[0] == "install":
        return cmd_skill_install(" ".join(args[1:]))
    if cmd == "skill":
        print("usage: xomni skill search <query> | install <dir>")
        return 1
    if cmd == "providers":
        return cmd_providers()
    if cmd == "doctor":
        return cmd_doctor()
    if cmd == "stacks":
        return cmd_stacks()
    if cmd == "add":
        if not args or args[0].startswith("-"):
            print("usage: xomni add <stack> [--yes] [--dry-run] [--smoke]   (stacks: "
                  + ", ".join(_list_stacks()) + ")")
            return 1
        name = args.pop(0)
        flags = set(args)
        return cmd_add(name,
                       dry_run=("--dry-run" in flags or "-n" in flags),
                       smoke=("--smoke" in flags or "-s" in flags),
                       yes=("--yes" in flags or "-y" in flags))
    if cmd == "launch":
        home = os.path.expanduser("~/AppData/Local/hermes")
        env = dict(os.environ, HERMES_HOME=os.path.join(home, "profiles", "xomni"))
        return subprocess.call([_resolve_exe("hermes"), *args], env=env)  # .cmd shim fix (hermes.exe works bare)
    print(f"unknown command: {cmd}\n{__doc__}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
