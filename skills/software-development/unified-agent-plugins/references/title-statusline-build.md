# title-statusline build notes (hook/command-only plugin, Windows-native statusline)

Built 2026-08 at `C:\Users\HP\unified-agent\plugins\title-statusline\` — fourth member-pattern in the
collection: a plugin with NO model tool. `post_tool_call` hook refreshes the terminal title bar with the
sponsor line from `~/.waitperk/current.txt` + `~/.perkline/current.txt`; `/title status|on|off|now` toggles
a plugin-local `state.json`. Purpose: close the sponsorship loop — the sponsor line visible in the title bar
while the agent works (the Windows-native statusline; the TUI core change is parked).

## core.py surface (pure stdlib, no Hermes imports)
- `set_title(title)` — win32 → `ctypes.windll.kernel32.SetConsoleTitleW`; else OSC 0 escape `"\x1b]0;{title}\x07"` to stdout; sanitize `\x1b \x07 \r \n` out of the title first (escape injection guard).
- `read_sponsor_lines() -> list[str]` — reads `[WAITPERK_LINE, PERKLINE_LINE]`; missing/blank files contribute nothing → `[]` when both missing. Order is contract: waitperk FIRST, perkline LAST.
- `pick_line(lines, prefix="[agent]")` — prefers perkline's line (it carries the pricing/model tier) by scanning `reversed(lines)` (blank perkline = paused → falls through to waitperk); result = `prefix + line` truncated to `TITLE_MAX` (60); empty input → just the prefix (neutral title).
- `cycle_title(interval_hint=30)` — stateless one-shot refresh; returns title set or None when no lines. Caller owns cadence: post_tool_call hook refreshes continuously while the agent works; a timer with `interval_hint` covers idle periods; `/title now` calls it directly.

## Plugin-local state.json pattern (deepcopy!)
```python
DEFAULT_STATE = {"enabled": True}
_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

def _load_state() -> dict:
    state = deepcopy(DEFAULT_STATE)          # NEVER share/mutate the module default
    try:
        with open(_STATE_PATH, encoding="utf-8") as f:
            state.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return state

def _save_state(state) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        with open(_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
    except OSError:
        pass  # persistence must never break the agent
```
Hook contract: `def _on_post_tool_call(**kwargs) -> None` — body in try/except, returns None always;
skip work when `not _load_state().get("enabled", True)`. `/title off` restores a neutral title
(`core.NEUTRAL_TITLE`, e.g. `"[agent]"`).

## _load_plugin() harness for hyphenated __init__.py tests
`title-statusline` can't be `import`ed by module name (hyphen). Replicates
`hermes_cli.plugins._load_directory_module` (which loads plugins as `hermes_plugins.<slug>` packages with
hyphens→underscores). Copy-paste into `tests/test_plugin.py`:

```python
import importlib.util, os, sys, types

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_plugin():
    ns_name = "hermes_plugins"
    if ns_name not in sys.modules:
        ns = types.ModuleType(ns_name); ns.__path__ = []; sys.modules[ns_name] = ns
    pkg_name = f"{ns_name}.title_statusline"          # slug: hyphens -> underscores
    spec = importlib.util.spec_from_file_location(
        pkg_name, os.path.join(PLUGIN_DIR, "__init__.py"),
        submodule_search_locations=[PLUGIN_DIR])
    module = importlib.util.module_from_spec(spec)
    module.__package__ = pkg_name
    module.__path__ = [PLUGIN_DIR]                     # so `from . import core` resolves
    sys.modules[pkg_name] = module
    spec.loader.exec_module(module)
    return module

PLUGIN = _load_plugin()   # once at module import time
```
Then `PLUGIN._on_post_tool_call(...)`, `PLUGIN._handle_title("off")`, `PLUGIN.core.set_title` all work.

## Mock recipes (all used in the 27-test suite, 16-check verify script)
- win32 path: `mock.patch.object(sys, "platform", "win32")` + `mock.patch.dict(sys.modules, {"ctypes": fake_ctypes})` where `fake_ctypes.windll.kernel32.SetConsoleTitleW = mock.Mock()`; assert `call_args == mock.call("exact string")`.
- ctypes unavailable: `mock.patch.dict(sys.modules, {"ctypes": None})` → `import ctypes` raises ImportError → fallback path exercised.
- SetConsoleTitleW itself failing: side_effect=OSError → must not raise, must fall back.
- stdout capture: `mock.patch.object(sys, "stdout", io.StringIO())`; assert `buf.getvalue() == "\x1b]0;hello\x07"`.
- file isolation: `mock.patch.object(core, "WAITPERK_LINE", os.path.join(d, "wp.txt"))` (patch module-level constants, don't touch `~`).
- state isolation: `mock.patch.object(PLUGIN, "_STATE_PATH", os.path.join(tmp, "state.json"))` in setUp + addCleanup stop.

## Live Windows console-title round-trip (real ctypes, not mocked)
```python
before = ctypes.create_unicode_buffer(512)
ctypes.windll.kernel32.GetConsoleTitleW(before, 512)
core.set_title("[agent] hermes-verify")
after = ctypes.create_unicode_buffer(512)
ctypes.windll.kernel32.GetConsoleTitleW(after, 512)
assert before.value != after.value and after.value == "[agent] hermes-verify"
ctypes.windll.kernel32.SetConsoleTitleW(before.value or "[agent]")  # restore!
```
Run in a plain `python -c` or the verify script; restore the original title afterward (courtesy).

## Ad-hoc verification script flow (hermes-verify-)
When fresh verification evidence beyond the suite is demanded:
1. Write focused script to the OS temp dir with `hermes-verify-` filename prefix (e.g. `C:\Users\HP\AppData\Local\Temp\hermes-verify-title-statusline.py`).
2. `sys.path.insert(0, PLUGIN_DIR)`; `check(name, cond, detail="")` helper appends failures; per-check `print("PASS  " / "FAIL  " + name)`; final line `"{n} failure(s)"` or `"ALL CHECKS PASSED"`; `sys.exit(1 if failures else 0)`.
3. Include: mocked win32 + OSC fallback + sanitize, read_sponsor_lines missing/with-files, pick_line preference/truncation, hook returns-None + swallows failures, /title off→on round-trip + deepcopy independence, and the LIVE GetConsoleTitleW round-trip.
4. Run with `python` (3.11). On success: `rm -f` the script and confirm deletion (`ls` → "No such file").

## Test-discovery notes
`python -m unittest discover -s tests -v` from the plugin dir works with the per-file sys.path preamble
(insert PLUGIN_DIR at top of each test file so `import core` works from any launch dir). `tests/` has no
`__init__.py` (namespace) — `python -m unittest tests.test_core` also works from the plugin dir.
