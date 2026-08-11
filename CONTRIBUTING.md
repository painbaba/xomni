# Contributing to XOMNI

Thanks for contributing to XOMNI — an MIT-licensed, open-source agent product
with **16 plugins** and a **603-test** suite. This guide covers how to add a
plugin, the rules that keep the runtime fast, and how to get your changes
reviewed and merged.

---

## 1. Repository layout

```
xomni/
├── plugins/            # each plugin is a self-contained directory
│   └── <plugin-name>/
│       ├── plugin.yaml     # metadata: name, version, description
│       ├── __init__.py     # tool/command definitions + register(ctx)
│       ├── core.py         # pure-stdlib logic, unit-testable in isolation
│       └── tests/
│           └── test_core.py  # unittest suite
├── data/               # skill DB builder + security scanner (build_db.py)
├── docs/               # TEST-MATRIX.md, ARCHITECTURE.md, PERFORMANCE.md, ...
├── website/            # flagship website
└── .bench/             # benchmark + full test matrix runner
```

## 2. Plugin anatomy

A XOMNI plugin is a directory under `plugins/<name>/` with exactly four parts:

### `plugin.yaml`
YAML metadata — `name`, `version`, and a one-line `description` that lists the
plugin's tools and commands:

```yaml
name: my-plugin
version: "1.0.0"
description: "One-line summary of what the plugin does. Tools: <tool> (web). Commands: /cmd."
```

### `__init__.py` — `register(ctx)`
Defines the plugin's surface: model tools via `ctx.register_tool(...)` (with a
`toolset`, JSON `schema`, and `handler`) and slash commands via
`ctx.register_command(...)`. Every plugin exposes exactly one entry point:

```python
def register(ctx) -> None:
    ctx.register_tool(
        "my_tool",
        toolset="web",
        schema={"type": "object", "properties": {...}, "required": [...]},
        handler=_my_tool_handler,
        description="What the tool does",
        emoji="🔧",
    )
    ctx.register_command("mycmd", handler=_my_cmd_handler, description="...", args_hint="<arg>")
```

Handlers are thin: validate input, delegate to `core.py`, return a string.

### `core.py` — pure stdlib
All real logic lives here. `core.py` must be **pure Python stdlib** — no Hermes
imports, no third-party dependencies — so it is unit-testable in isolation.
See `plugins/context-loader/core.py` for the canonical example (urllib-based
fetching, regex HTML→text conversion, base64 image encoding).

### `tests/test_core.py`
A `unittest` suite (stdlib only) that exercises `core.py` directly. Run a
single plugin's suite with:

```bash
python -m unittest tests.test_core -v   # from inside plugins/<name>/
```

## 3. The hook speed rule (mandatory)

**Hook policy:** NEW plugins (omni-design, omni-parallel, anything added after
2026-08) must register **no hooks** at all. The 14 legacy plugins may keep
their hooks, but a hook handler must never call the LLM, the network, or
subprocess — enforcement: `python .bench/ci_gate.py` (exit 0 = pass).
Runtime speed is a product feature: the agent loop must stay fast and
predictable (<1s/turn target, see docs/PERFORMANCE.md).

- ❌ **No lifecycle hooks for new plugins** — nothing that runs at load, at
  registration, or between turns without being explicitly invoked by the user
  or model.
- ❌ **No LLM calls, network requests, or subprocess spawning** at
  registration/import time or inside any hook handler (legacy or new).
- ❌ **No blocking work in `register(ctx)`** — registration must be pure
  bookkeeping (schemas + handler wiring) and return in milliseconds.
- ✅ All network/LLM work happens **lazily inside tool/command handlers**,
  only when the tool is actually invoked.
- ⏱️ **Speed target: <1s per turn.** New plugins must not push the perceived
  turn latency past this; benchmark regressions are review-blocking.

Reviewers will reject any PR that registers a hook in a new plugin, performs
I/O at import or registration time, calls the LLM/network/subprocess inside a
hook handler, or measurably slows the loop.

## 4. Test matrix

The full matrix runs every plugin suite and rewrites `docs/TEST-MATRIX.md`:

```bash
bash .bench/run_all_tests.sh
```

Current verified environment (see `docs/TEST-MATRIX.md`):

| Environment | Result |
|---|---|
| Windows 10/11, Python 3.11, git-bash (primary dev env) | ✅ 603/603 pass (16 plugins) |
| <!-- MATRIX-PLACEHOLDER: add rows here as platforms/versions are verified, e.g. `Ubuntu 22.04, Python 3.10 | ⏳ pending` --> | ⏳ pending |

Rules for the matrix:

- Every plugin **must** ship a `tests/test_core.py` that passes under
  `python -m unittest` — no tests, no merge.
- New plugins appear as a row automatically; keep existing rows green.
- If you verify a new OS/Python version, add it to the table above (replace
  the placeholder).

## 5. Code style

- `core.py`: pure stdlib, `from __future__ import annotations`, module
  docstring listing every public function, constants in UPPER_CASE.
- Handlers return human-readable strings (including error strings) — never
  raise for expected failures.
- Keep `plugin.yaml` `description` to one line.
- No secrets, no absolute user paths, no hardcoded home directories
  (use `os.path.expanduser("~")`).

## 6. PR workflow

1. **Fork** `github.com/painbaba/xomni` and create a branch
   (`feat/<plugin>` or `fix/<description>`).
2. **Add or fix a plugin** following §2, including tests.
3. **Run the matrix** (`bash .bench/run_all_tests.sh`) and confirm 603/603
   (or your new total) pass.
4. **Open the PR** with a description covering: what the plugin does, its
   tools/commands, test results, and confirmation that it adds **zero hooks**
   and stays under the 1s/turn target.
5. A maintainer reviews; address feedback with follow-up commits (no force
   pushes after review starts).

## 7. Questions

Open a discussion or issue on GitHub. For security issues, follow
[SECURITY.md](SECURITY.md) instead — do not file public issues for
vulnerabilities.
