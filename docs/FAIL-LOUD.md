# FAIL-LOUD — non-interactive + no silent cancels (U3)

## Policy

Every XOMNI install/exec surface — the `xomni` CLI (`xomni plugins install`,
`xomni skill install`) and the plugin commands (`/mcp add`, `/skills-install`,
`/skills-marketplace`, and the `skills_import` / `mcp_call` tools) — is fully
non-interactive: every mutating command accepts `--yes` / `-y` (skips any
confirmation; none of these commands ever blocks on a prompt, so piping
`printf 'Y\nY\n'` into them is never needed again), and **no failure is ever
silent**: a failure must either exit non-zero (CLI) or return an error string
that names the cause (plugin command handlers), with no bare `return`/`pass`
swallowing install errors. Concretely: a missing directory, a read-only
target, an invalid URL, a missing binary (e.g. `git`), a rejected skill, an
empty or all-rejected marketplace, and an unknown plugin name all produce a
loud, cause-naming error and a non-zero exit / FAILED line — verified by
`.bench/test_fail_loud.py`, which simulates each failure mode in BOTH the CLI
and the plugin-command handlers.

## Checklist (apply to any new or edited install/exec path)

- [ ] Command accepts `--yes` / `-y` (strip it from args before parsing paths;
      it must never be misread as a file/dir/URL argument).
- [ ] No `input()` / prompt anywhere in the path — verified by
      `PromptFreeGuaranteeTests` in `.bench/test_fail_loud.py`.
- [ ] CLI surface: every failure prints the cause (path, reason, or exception
      text) and returns exit code 1; partial failure (e.g. some plugins
      unknown/uninstallable) is reported per-item AND exits non-zero.
- [ ] Plugin-command surface: every failure returns an error string beginning
      with a FAILED/error marker that NAMES the cause (e.g. `no such file: X`,
      `not a directory: X`, `invalid URL: …`, `copy failed: …`,
      `git clone failed: …`, `all N skill(s) rejected: …`).
- [ ] Core functions return `{"ok": False, "reason": "<cause>"}` instead of
      raising through the handler or returning a bare falsy dict; unexpected
      exceptions inside install loops are caught and converted to a named
      reason (never `pass`).
- [ ] Failure modes covered by `.bench/test_fail_loud.py`: missing dir,
      read-only target, invalid URL, missing binary, rejected skill,
      empty/all-rejected marketplace, unknown plugin — each asserted in BOTH
      surfaces.
- [ ] Run `python .bench/test_fail_loud.py` (green) plus the affected plugin
      suites (`cd plugins/<name> && python -m unittest tests.test_core -q`)
      before shipping.

## Surface map (audited 2026-08)

| Command | `--yes` | Failure behavior |
|---|---|---|
| `xomni plugins install [--yes] [names…]` | yes | per-name `! failed: <name>: <cause>`; exit 1 if any failed |
| `xomni skill install [--yes] <dir>` | yes | `FAILED — <reason>` + issues; exit 1 |
| `xomni add <stack> [--yes]` | yes (accepted) | `ERROR: <cause>` (unknown stack / MCP / missing-or-unwritable config.yaml); exit 1 |
| `/mcp add [--yes] <path>` | yes | `/mcp add: no such file: <path>` / `rejected — <cause>` / `failed to copy: <exc>` |
| `/mcp add <name> [--yes]` (host install) | yes | plan without `--yes` → `confirm by re-running: /mcp add <name> --yes` (no mutation); on any error → `/mcp add: FAILED — <cause>` |
| `/skills-install [--yes] <dir>` | yes | `/skills-install: FAILED — <reason>` |
| `/skills-marketplace [--yes] <url-or-dir>` | yes | `/skills-marketplace: FAILED — <reason>` |
| `/skills publish [--yes] <dir>` | yes | `/skills publish: FAILED — <reason>` (+ first 3 issues) |
| `/skill save [--yes] <name>` | yes | `/skill save: FAILED — <reason>` (unknown draft, REJECT/REVIEW, write error) |
| `skills_import` tool | (n/a) | `skills_import failed: <exc>` |

Full policy + behavior-without-`--yes` column: docs/NONINTERACTIVE.md.
