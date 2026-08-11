# verify-runner plugin — the verify-after-every-change loop

Worked example (built at `C:\Users\HP\unified-agent\plugins\verify-runner\`): a
stateless plugin that runs a project's tests + linter and returns a verdict —
closing the "verify after every change" loop from the git-diff-discipline
skill. 38 tests green in ~2s; loaded cleanly through the real host
`PluginManager`.

## Anatomy (pure core.py + one shared public function)

- `plugin.yaml` — name/version/description only (same shape as perkline).
- `__init__.py` — `verify_project(dir) -> str` is THE function; the model tool
  and the slash command are one-line wrappers so both surfaces return
  byte-identical output:
  - tool handler: `verify_project((params or {}).get("dir") or "")`
  - command handler: `verify_project((raw or "").strip())`
  - `register(ctx)`: `ctx.register_tool("verify_project", toolset="file",
    schema={"description": ..., "type": "object", "properties": {"dir":
    {"type": "string", "description": "directory to verify (default: cwd)"}}},
    handler=..., description="...", emoji="✅")` +
    `ctx.register_command("verify", handler=..., args_hint="[dir]")`.
    (toolset "file" — free-form label, never validated by the registry.)
- Output shape: header `VERIFY <dir>`, one verdict line per step
  (`TEST PASS (exit 0)`), `--- TEST failing tail ---` sections for failing
  steps, final `VERDICT: PASS|FAIL`. Bad dir returns an error LINE
  ("verify_project: not a directory: X"), never raises.
- `core.py` — pure stdlib, zero Hermes imports.

## Discovery precedence (commands are strings; run with cwd=dir)

- tests: `"pytest"` if `pytest.ini`/`pyproject.toml`/`setup.cfg` exists in dir,
  else `shutil.which("pytest")`, else `"python -m unittest discover"`.
- lint: `"ruff"` if `ruff.toml`/`.ruff.toml` exists, else `[tool.ruff]` found
  in `pyproject.toml` content, else `shutil.which("ruff")`, else
  `"python -m py_compile <changed .py files>"` (zero-dep syntax check).
- `changed_py_files(dir)`: `git rev-parse --show-toplevel` → if a repo, run
  `git diff --name-only HEAD` + `git ls-files --others --exclude-standard`
  with cwd=REPO ROOT (paths come back repo-root-relative), join to root,
  filter `os.path.exists` (kills rename/deleted stragglers) and `.py`, cap
  ~120 files; non-repo fallback = `os.walk` skipping
  `.git/node_modules/venv/dist/build/__pycache__/...`. Return ABSOLUTE paths
  so py_compile works even when the verified dir is a repo subdirectory.

## run_command: the never-hang contract

`run_command(cmd, cwd, timeout=180) -> {"ok", "exit_code", "stdout_tail",
"stderr_tail", "timed_out"}`:

- guard: cwd must exist (else "working directory not found").
- `shlex.split(cmd)` → argv; `subprocess.run(argv, cwd=cwd,
  capture_output=True, text=True, encoding="utf-8", errors="replace",
  timeout=timeout)`. `shell=False` — never `shell=True` on Windows.
- tail: last 3000 chars per stream (`text[-3000:]`).
- `TimeoutExpired` → `timed_out=True, ok=False, exit_code=None`; partial
  output lives in `exc.output`/`exc.stderr` (there is NO `.stdout`) —
  `_as_text()` normalizes bytes/None/str. subprocess kills the child, so a
  hung test can't hang the agent.
- `OSError` → "command not found"; `ValueError` from shlex.split → "bad
  command".

## summarize(result, kind) shapes

`TEST PASS (exit 0)` / `LINT FAIL (exit 1) | <last stderr-or-stdout line,
truncated ~160 chars>` / `TEST TIMEOUT` / `RUN PASS (exit 0)` (kind
uppercased, default "RUN"). stderr preferred over stdout for the detail line.

## Test harness (the module-identity trick)

- `sys.path.insert(0, plugin_dir)`; `import core` for pure tests.
- Load the package exactly like the host loader (`_load_directory_module`:
  importlib spec from `__init__.py`, `submodule_search_locations=[plugin_dir]`,
  `__package__` + `__path__` set) and **pre-seed
  `sys.modules["<testpkg>.core"] = core` BEFORE `exec_module`** — without
  this, the plugin's `from . import core` creates a SECOND module instance and
  `mock.patch.object(core, ...)` silently patches the wrong one.
- `_FakeCtx` records `register_command`/`register_tool` calls (name, handler,
  schema, kwargs); routing tests grab the recorded handlers and call them
  directly with mocked `core.run_command` + `discover_*` (hermetic) AND with
  real tiny commands.
- run_command tests: real one-liners via
  `shlex.quote(sys.executable) + " -c " + shlex.quote(body)` (safe on Windows
  backslash paths); timeout via `mock.patch.object(core.subprocess, "run",
  side_effect=subprocess.TimeoutExpired([...], 0.01, output="partial",
  stderr=""))`; truncation via `sys.stdout.write("x" * 5000)` → tail is
  exactly 3000 chars.
- changed_py_files: real `git init` + `config user.*` + commit + modify +
  untracked-file fixture in a temp dir.
- E2E: temp dir with trivial `unittest` files → real discovery + subprocesses
  (fast): `VERDICT: PASS`; broken test file → `TEST FAIL` with `AssertionError`
  in the failing tail.
- Run: `python -m unittest discover -s tests -v` from the plugin dir.

## Host-truth verification (do before declaring done)

1. Name conflict pre-check: `from hermes_cli.commands import resolve_command;
   resolve_command("verify") is None` → `/verify` is free (the loader drops
   conflicting commands SILENTLY, so this check matters).
2. Real loader, no full discovery scan needed: set `HERMES_HOME` to a temp
   dir, then `PluginManager()` + `PluginManifest(name=..., version=...,
   path=<plugin dir>, key=<name>, source="user")` + `mgr._load_plugin(m)` →
   assert `mgr._plugins[key].error is None`, `commands_registered ==
   ["verify"]`, `tools_registered == ["verify_project"]`.
3. Live smoke: `verify_project(<plugin dir>)` on its own repo → real
   discovery, `TEST PASS`/`LINT PASS`/`VERDICT: PASS` (unittest discovers the
   plugin's own tests; py_compile compiles the changed files).
4. Fresh ad-hoc evidence: write a focused check script to a
   `tempfile.gettempdir()` path (prefix `hermes-verify-`), run it, delete it,
   report PASS/FAIL counts — don't cite earlier green runs alone.

## Pitfall: heredoc/JSON escaping collisions (Windows)

`\\` in a tool-call JSON string arrives at the shell as `\`; a
`<<'EOF'` heredoc embedding `C:\Users\...` then throws `SyntaxError: (unicode
error) 'unicodeescape' codec can't decode ... truncated \UXXXXXXXX escape`.
Fix: write embedded scripts with write_file to a tempfile-derived path, or use
forward slashes (`C:/Users/...`) inside them.
