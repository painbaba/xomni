# NONINTERACTIVE — every mutating command has a `--yes` path (U3)

## Policy

XOMNI is **non-interactive everywhere**. No mutating command may block on a
prompt, and none may fail silently. The three rules:

1. **Every mutating command accepts `--yes` / `-y`.** The flag is stripped
   from the argument list before paths/URLs are parsed, so it can never be
   misread as a file, dir, or URL. Commands that already never prompt accept
   the flag as a guarantee that no confirmation will ever be shown; the one
   command that gates on it (`/mcp add <name>`) requires it to mutate.
2. **Failures are loud.** A failure must either exit non-zero (CLI) or return
   an error string that NAMES the cause (plugin command handlers). There is
   no bare `return`/`except: pass` that swallows an install error. A missing
   directory, a read-only target, an invalid URL, a missing binary, a
   rejected skill, an empty/all-rejected marketplace, an unknown plugin
   or server, a missing/unwritable config.yaml, an unwritable `.env`, and a
   missing host binary (`xomni launch`) all produce a cause-naming error and
   a non-zero exit / FAILED line.
3. **Zero silent cancels.** Nothing ever prints "Cancelled" and walks away.
   The only "no-op" outcomes are explicit and informative: `already
   registered — nothing to do` (`/mcp add <name>` when the server exists),
   `skipped N already present` (`xomni add <stack>` on re-run), and the
   plan-then-confirm flow of `/mcp add <name>` without `--yes`, which prints
   the exact re-run command instead of mutating.

The old workaround — piping `printf 'Y\nY\n'` into a prompt — is never
needed. Piping a prompt into any of these commands would EOF it (stdin is
closed in CI), which is exactly what `.bench/test_fail_loud.py` verifies.

## Command table

| Command | `--yes` flag | Behavior without `--yes` | Failure behavior |
|---|---|---|---|
| `xomni plugins install [names…]` | `--yes` / `-y` (stripped) | Same — never prompts; installs immediately | per-name `! failed: <name>: <cause>`; exit 1 if any failed |
| `xomni skill install <dir>` | `--yes` / `-y` (stripped) | Same — never prompts; installs immediately | `FAILED — <reason>` + issues; exit 1 |
| `xomni add <stack>` | `--yes` / `-y` (accepted) | Same — never prompts; appends MCP servers immediately (`--dry-run` previews) | `ERROR: <cause>` (unknown stack, invalid MCP, missing/unwritable config.yaml, failed validation); exit 1 |
| `xomni providers add <name> <url>` | `--yes` / `-y` (stripped) | Same — never prompts; writes the providers block + .env key placeholder immediately (`--dry-run` previews) | `FAILED — <cause>` (invalid name/URL/env var/api-type, missing config.yaml, unwritable config.yaml, unwritable `.env`); exit 1; `ALREADY PRESENT` idempotent no-op |
| `xomni launch` | `--yes` / `-y` (passed through to the host) | Never prompts; delegates to `hermes` | host exit code; `launch: FAILED — the hermes binary was not found on PATH` if missing; exit 1 |
| `/mcp add <path>` (catalog import) | `--yes` / `-y` (stripped) | Same — never prompts; imports immediately | `no such file: <path>` / `rejected — <cause>` / `failed to copy: <exc>` |
| `/mcp add <name>` (host install) | `--yes` / `-y` (required to mutate) | Prints the plan + `confirm by re-running: /mcp add <name> --yes` — NO mutation | `/mcp add: FAILED — <cause>` (unknown server, launch binary missing, config write error) |
| `/skills-install <dir>` | `--yes` / `-y` (stripped) | Same — never prompts; installs immediately (`--dry-run` previews) | `/skills-install: FAILED — <reason>` |
| `/skills-marketplace <url-or-dir>` | `--yes` / `-y` (stripped) | Same — never prompts; installs immediately (`--dry-run` previews) | `/skills-marketplace: FAILED — <reason>` (invalid URL, git missing, empty/all-rejected) |
| `/skills publish <dir>` | `--yes` / `-y` (stripped) | Same — never prompts; stamps credit then delegates to the host (`hermes skills publish`), repo-copy fallback only if hermes is missing | `/skills publish: FAILED — <reason>` (+ first 3 issues) |
| `/skill save <name>` | `--yes` / `-y` (meaningful: writes flat into the host skills dir, no category) | Never prompts; saves to the plugin drafts target as `<target>/<category>/<name>/SKILL.md` (draft must exist first) | `/skill save: FAILED — <reason>` (unknown draft, REJECT/REVIEW, write error) |
| `skills_import` tool | n/a (model tool — confirm-free by design) | n/a | `skills_import failed: <exc>` |

## Surface map

| Surface | File | Mutating command(s) |
|---|---|---|
| CLI | `xomni_cli/__init__.py` | `plugins install`, `skill install`, `add <stack>`, `providers add`, `launch` |
| Plugin command | `plugins/mcp-catalog/__init__.py` | `/mcp add <path>`, `/mcp add <name> [--yes]` |
| Plugin command | `plugins/omni-skills/__init__.py` | `/skills-install`, `/skills-marketplace`, `/skills publish` |
| Plugin command | `plugins/skill-drafter/__init__.py` | `/skill save` |
| Model tool | `plugins/omni-skills/__init__.py` | `skills_import` |

## Verification

- `.bench/test_fail_loud.py` — fail-loud + `--yes`-path suite: every audited
  command is invoked with `--yes` and asserted to perform its action
  (stubbed handlers), and every simulated failure names its cause. Green:
  `python .bench/test_fail_loud.py`.
- `xomni_cli/tests/test_noninteractive.py` — CLI unit suite: `--yes` accepted
  on every mutating command, unknown plugin / missing dir / un-creatable
  target dir / unwritable `.env` / missing host binary each exit 1 with the
  cause named, and `main()` propagates subcommand exit codes. Green:
  `cd xomni_cli && python -m unittest discover -s tests -q`.
- `PromptFreeGuaranteeTests` — asserts no `input(` anywhere in the audited
  files.
- Source-level grep: every audited mutating command's file contains `--yes`
  (asserted by the suite).
