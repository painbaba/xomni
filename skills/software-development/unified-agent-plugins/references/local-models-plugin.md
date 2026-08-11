# local-models plugin — probing & wiring local OpenAI-compatible servers

Worked example: `C:\Users\HP\unified-agent\plugins\local-models\` (SHIPPED).
Purpose: detect/manage LOCAL model servers (Ollama, LM Studio) so the unified
agent can use free local models. `/localmodels status|scan|config [server]|add <url> [id]|remove <id>`
+ `local_models` model tool (action=status|scan|config[, server]).

## Port constants (document these in the module docstring)
- `OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"` — Ollama's OpenAI-compat API; 11434 is its default serve port (`OLLAMA_HOST` can move it; `/v1` is the compat shim).
- `LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"` — LM Studio local server default ("Start Server" in Settings).
- `DEFAULT_SERVERS = [{"id": "ollama", ...}, {"id": "lmstudio", ...}]` — server dicts carry id/name/base_url.
- `SERVERS_JSON` = plugin-local `servers.json` (next to `__init__.py`) holding EXTRA user servers; `load_servers(path=None)` → missing/corrupt = `[]` (extras live on top of defaults), `save_servers(servers, path=None)`; `default_servers()` returns `deepcopy(DEFAULT_SERVERS)` so callers can't mutate the module default.

## probe_server(base_url, timeout=3) -> {ok, http, models:[ids], error}
- GET `{base}/models` (strip trailing `/`) with a browser User-Agent (`BROWSER_UA`, Mozilla Chrome 126 string) — Cloudflare-style 1010 blocks without it.
- Parse ALL THREE payload shapes via a `_extract_model_ids` helper: `{"data": [{"id":...}]}` (OpenAI/Ollama/LM Studio), `{"models": [...]}` (legacy), bare `["id", ...]` list.
- Exception ladder: `urllib.error.HTTPError` → `{"ok": False, "http": exc.code, "error": f"HTTP {exc.code}"}`; generic `Exception` (covers `OSError` refused, `URLError`, timeout, bad JSON) → `error = str(exc)[:160]`.
- `detect_servers(defaults=None, timeout=3)` deepcopies defaults (accepts server dicts OR bare base-url strings), probes each, returns identity-tagged results `{server_id, name, base_url, ok, http, models, error}`. Down servers are reported (ok=False) so callers can show WHY; `scan_text()` lists only up ones as usable.

## Mock recipes (the traps)
Success path WITHOUT side_effect:
```python
fake = mock.MagicMock(); fake.status = 200
fake.read.return_value = json.dumps({"data": [{"id": "llama3.2"}]}).encode()
with mock.patch.object(core, "urlopen") as m:
    m.return_value.__enter__.return_value = fake
    r = core.probe_server("http://127.0.0.1:11434/v1")
```
Assert `m.call_args.args[0].full_url == ".../v1/models"`, `req.get_header("User-agent")` contains Mozilla, `m.call_args.kwargs.get("timeout") == 3`.

**side_effect variant — the session's one test failure**: a side_effect fn that returns the bare `fake` breaks silently — `with fake as resp:` yields `fake.__enter__()` (a fresh child mock) so status/read are MagicMocks and the probe reports DOWN (test sees 0 up). Must return a context-manager mock:
```python
cm = mock.MagicMock(); cm.__enter__.return_value = fake
def side(req, timeout=3):
    if "11434" in req.full_url: raise OSError("Connection refused")
    return cm
with mock.patch.object(core, "urlopen", side_effect=side):
    res = core.detect_servers()
```
Real HTTPError fixture (no mock needed): `urllib.error.HTTPError("http://x/models", 404, "Not Found", {}, io.BytesIO(b""))`.

## Config-gen shapes (assert these)
- `hermes_provider_block(server, model_ids=None)` — YAML comment block for config.yaml:
  `# provider: <id>` / `# model: <id or placeholder>` / `# base_url: <base>` / `# key_env: local` — `key_env: local` is the placeholder convention: local endpoints need no real key (mirrors provider-pool's gateway block shape).
- `opencode_config(server, model_ids=None)` / `ollama_config(server, model_ids=None)` — valid-JSON opencode.json provider block: `{"provider": {"<id>": {"npm": "@ai-sdk/openai-compatible", "name": ..., "options": {"baseURL": base, "apiKey": "local"}, "models": {id: {"name": id}}}}}`. Dummy `apiKey` string satisfies opencode. `ollama_config` is the canonical Ollama-shaped block usable for ANY server id. Test by `json.loads` and asserting `parsed["provider"][id]["options"]["baseURL"]`.
- `/localmodels config <id>` prints the full bundle (hermes + opencode + ollama blocks); unknown id → error listing known ids; no arg → ollama default (deterministic, no network).

## Standalone `__init__.py` test-loading — plain-name variant (simpler than the slug harness)
Plugin's `__init__.py` carries:
```python
try:
    from . import core
except ImportError:          # standalone test import (no parent package)
    import core
```
Then tests load it with a NON-package spec — the fallback resolves `core` to the top-level module already imported by the test, so `mock.patch.object(mod.core, ...)` patches land, no `__path__`/sys.modules pre-seed:
```python
spec = importlib.util.spec_from_file_location("local_models_plugin", init_path)
mod = importlib.util.module_from_spec(spec)
sys.modules["local_models_plugin"] = mod
spec.loader.exec_module(mod)
```
The double-core pre-seed trap (context-loader) only applies to package-name loads (`hermes_plugins.<slug>`), where `from . import core` re-executes core under the package name. Host package-style load was validated by copying the plugin dir to `hermes_plugins/local_models/` (hyphen→underscore slug) and importing — `register()` then wires `/localmodels` + `local_models` correctly.

## Live-scan DOWN shape (expected when nothing is running)
`python -c "import core, json; print(json.dumps(core.detect_servers(), indent=2))"` from the plugin dir with neither server installed → per-server `{"ok": false, "http": null, "models": [], "error": "<urlopen error [WinError 10061] ... actively refused it>"}`. Cross-check with `netstat -ano | grep -E ":(11434|1234)\s"` (LISTENING) + `tasklist | grep -iE "ollama|lm studio"`. 29 tests cover probe/detect/config/round-trip/wiring; run `python -m unittest tests.test_core -v` (python 3.11, never python3).
