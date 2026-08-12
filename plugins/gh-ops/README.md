# gh-ops

GitHub/GitLab workflows via the `gh`/`glab` CLIs (OpenCode P4 port) with
**strict** output parsing: column positions are derived from the header
line and rows sliced by those positions — never split on whitespace,
because titles and labels contain spaces.

**What it does:** wraps `gh` (and detects `glab`) to run auth status, PR
list, issue list, and current-user lookups; parses both the TTY table and
the piped-TSV shapes; empty results, absent CLIs, auth failures, network
errors, and timeouts all collapse into stable, clean messages. Never
fabricates data (TSV rows have no draft column → `draft: False`).

**Commands/tools:** slash command
`/gh status|prs [repo]|issues [repo]|me|pr-review <n> <text>|pr-summary <n> <text>`
plus model tool `gh_ops(action, repo?)` — both share `core.execute`.
`pr-review`/`pr-summary` post comments via `gh pr review <n> --comment --body <text>`
(core also exposes `pr_review_batch(pr_number, comments)` for programmatic
batches, with `path`/`line` position hints rendered as `[path:line]` prefixes).
Requires the `gh` CLI installed (https://cli.github.com).

**Speed posture:** no hooks — nothing alters agent behavior; each call is
a single subprocess with a 30 s timeout.

**Config:** none (optional `repo` arg scopes `prs`/`issues` to `OWNER/REPO`).

```bash
cd plugins/gh-ops && python -m unittest tests.test_core -v
```
