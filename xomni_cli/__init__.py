"""xomni — the XOMNI CLI.

One agent. Every feature. Every free model.

Installed via ``pip install .`` from the repo root. Commands:

  xomni                      launch the host (Hermes with XOMNI plugins)
  xomni plugins list         list the 17 plugins + test counts
  xomni plugins install [n]  copy plugin dirs into the Hermes plugins dir
  xomni skill search <q>     search skills (DB in checkout, else installed tree)
  xomni skill install <dir>  install a SKILL.md skill/marketplace (fail-closed)
  xomni providers            provider coverage table (all Hermes providers)
  xomni doctor               environment health check
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
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
]

PLUGIN_TESTS = {  # from docs/TEST-MATRIX.md
    "context-compact": 31, "context-loader": 69, "gh-ops": 99, "local-models": 87,
    "mcp-catalog": 26, "omni-design": 8, "omni-media": 27, "omni-memory": 26,
    "omni-parallel": 20, "omni-skills": 12, "perkline": 18, "provider-pool": 36,
    "repomap": 42, "sandbox-gate": 42, "title-statusline": 32, "verify-runner": 38,
    "waitperk": 34,
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
    targets = names or _plugins()
    ok = 0
    for name in targets:
        src = _plugin_dir(name)
        if not src:
            print(f"  ! unknown plugin: {name}")
            continue
        shutil.copytree(src, os.path.join(HERMES_PLUGINS_DIR, name), dirs_exist_ok=True)
        print(f"  installed: {name} -> {HERMES_PLUGINS_DIR}")
        ok += 1
    print(f"{ok} plugin(s) installed. Restart the host to load them.")
    return 0 if ok else 1


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


def cmd_skill_install(path: str) -> int:
    """Install a SKILL.md skill or marketplace dir into the Hermes skills dir (fail-closed)."""
    if not path or not os.path.isdir(path):
        print(f"usage: xomni skill install <dir>  ({path!r} is not a directory)")
        return 1
    omni_skills_core = _load_omni_skills_core()
    os.makedirs(HERMES_SKILLS_DIR, exist_ok=True)
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        r = omni_skills_core.install_skill(path, HERMES_SKILLS_DIR)
        print(f"  {r['verdict'] if 'verdict' in r else '?'} -> {r.get('dest', '?')}")
        return 0 if r.get("ok") else 1
    r = omni_skills_core.install_marketplace(path, HERMES_SKILLS_DIR)
    print(f"  {r['installed']} installed, {r['rejected']} rejected -> {HERMES_SKILLS_DIR}")
    return 0 if r["ok"] else 1


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
        return cmd_skill_install(args[1] if len(args) > 1 else "")
    if cmd == "skill":
        print("usage: xomni skill search <query> | install <dir>")
        return 1
    if cmd == "providers":
        return cmd_providers()
    if cmd == "doctor":
        return cmd_doctor()
    if cmd == "launch":
        return subprocess.call(["hermes", *args])
    print(f"unknown command: {cmd}\n{__doc__}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
