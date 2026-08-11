# gh/glab CLI output formats & strict parsing (live-verified, gh v2.95)

Source: building the `gh-ops` plugin in the unified-agent collection. All
format claims below were captured from REAL `gh` output on this box (piped
through `subprocess.run(capture_output=True)`, i.e. what any agent tool sees).

## THE trap: output shape depends on TTY-ness

`gh pr list` / `gh issue list` print a pretty **aligned table WITH a header
line** only when stdout is a terminal. When piped (always the case for
subprocess capture), gh switches to **TAB-separated rows with NO header** —
and the column ORDER is different from the pretty table.

| Command | TTY table (terminal only) | Piped (subprocess capture) |
|---|---|---|
| `gh pr list` | `NUMBER TITLE BRANCH STATE DRAFT` | `number \t title \t branch \t state \t createdAt` |
| `gh issue list` | `NUMBER TITLE LABELS STATE` | `number \t state \t title \t labels \t createdAt` |

Piped issue-list has **state BEFORE title**. Real captured samples:

```
# gh pr list --repo cli/cli --limit 3   (piped)
14120	chore(deps): bump github.com/klauspost/compress from 1.19.1 to 1.19.2	dependabot/go_modules/github.com/klauspost/compress-1.19.2	OPEN	2026-08-10T14:03:49Z
14108	Allow public extension installs past SAML enforcement	loganrosen:loganrosen-fix-extension-saml-install	OPEN	2026-08-08T22:01:01Z

# gh issue list --repo cli/cli --limit 3   (piped)
14118	OPEN	`gh skill` ignores `PI_CODING_AGENT_DIR` for Pi user-scope skills	enhancement, gh-skill	2026-08-10T09:58:55Z
14093	OPEN	`gh stack submit` fails with `authentication token not found for host github.com`		2026-08-07T23:20:27Z
```

Notes:
- Piped TSV has **no draft column** — draft is unknowable there; report
  `draft=False`, never invent. In piped TSV a draft PR's 4th field literally
  reads `DRAFT` (that is its state value), while the TTY table shows
  `STATE=OPEN` + `DRAFT=true/false`.
- Labels in piped TSV render as `enhancement, gh-skill` (comma+space).
- No "Showing X of Y" preamble in piped mode; footer hints
  (`Use 'gh pr list --author @me' ...`) appear only on TTY.
- `gh auth status` masks tokens itself (`ghp_****...`) — safe to surface.

## Strict parse algorithm (works for both shapes)

1. Split lines. If empty or any line matches an empty-result wording → `[]`.
2. Look for a header line whose whitespace tokens contain the required names
   (PRs: `NUMBER TITLE`; issues: `NUMBER TITLE STATE`). If found:
   - derive column start positions: iterate header tokens in order,
     `pos = line.find(tok, pos)`, `starts[tok] = pos`, `pos += len(tok)`;
   - slice each following row `line[start_i : start_{i+1}]` (last column
     `line[start_last:]`), `.strip()` each cell. NEVER whitespace-split —
     titles contain spaces.
3. No header found → headerless TSV path: split rows on `\t` with a per-kind
   column map (`PR_TSV_COLUMNS = NUMBER,TITLE,BRANCH,STATE,CREATED`;
   `ISSUE_TSV_COLUMNS = NUMBER,STATE,TITLE,LABELS,CREATED`). Extra columns
   beyond the map are ignored (future-proof).
4. Row filter: skip blank lines and any row whose NUMBER cell stripped of
   `#` is not all digits (catches footer hints in TTY captures).
5. Map to dicts: PR → `{number:int, title, branch, state, draft:bool}`;
   issue → `{number:int, title, labels, state}`. Empty/absent STATE → `"UNKNOWN"`.

## Empty-result wordings (match ALL, versions vary)

- `No pull requests found` / `No issues found`
- `There are no open pull requests in OWNER/REPO` / `There are no open issues in OWNER/REPO`
- `No issues are currently open`

Regexes that cover them:
`no (open )?(pull requests|issues?|results) (found|in )`,
`there are no (open )?(pull requests|issues?)`,
`no (open )?issues? (are )?currently (open|available)` — all IGNORECASE.

## argv recipes (list argv, never shell=True)

- status: `["gh", "auth", "status"]`
- me:     `["gh", "api", "user", "--jq", ".login"]` → bare login on stdout
- prs:    `["gh", "pr", "list", "--limit", "20"]` + `["--repo", OWNER/REPO]` when scoped
- issues: `["gh", "issue", "list", "--limit", "20"]` + same `--repo` suffix

## Error classification (return clean messages, never dump stderr)

| Condition | Signal | Message |
|---|---|---|
| CLI missing | `FileNotFoundError` from subprocess | "gh CLI not installed — install from https://cli.github.com" (+ glab state) |
| Not authenticated | stderr contains `not logged in` / `auth login` / `authentication required` / `please log in` | "gh is not authenticated — run 'gh auth login' first." |
| Network fail | stderr contains `connection refused` / `connection reset` / `timed out` / `timeout` / `could not resolve host` / `no such host` / `network is unreachable` / `failed to connect` / `tls handshake` / `http 5` | "network error talking to GitHub: <first stderr line>" |
| Generic | else | "gh error: <first stderr line>" (or `exit code N` when stderr empty) |

## Windows subprocess gotchas

- `subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
  errors="replace", timeout=30)` — without `encoding="utf-8"` Windows uses
  cp1252 and crashes on emoji/unicode in PR titles.
- `TimeoutExpired` → clean "gh command timed out after Ns." message.

## Fixture rules for parser unit tests (cost a debug cycle when ignored)

- TTY-table fixtures MUST be column-aligned: rows padded so each field starts
  at the header-derived position, exactly as gh pads them. Unaligned rows
  ("ragged" single-space rows) are NOT what gh emits — position slicing
  returns garbage and the tests fail confusingly.
- Test width-independence with a header whose column gaps differ from the
  main fixture, rows still aligned to THAT header.
- Cover: preamble line present/absent, draft true/false, merged state,
  empty labels (empty cell, not `""`), footer hint line, blank line between
  rows, and both piped-TSV column orders.

## Real-host registration proof (stronger than FakeCtx)

The unified-agent plugins dir is NOT wired into the live Hermes install
(HERMES_BUNDLED_PLUGINS unset) — plugins there are dev artifacts. To prove a
plugin registers against the REAL host API, run under the hermes venv python:

```python
sys.path.insert(0, r"C:\Users\HP\AppData\Local\hermes\hermes-agent")
from hermes_cli.plugins import PluginContext, PluginManifest
from tools.registry import registry
# load __init__.py via the importlib harness (see title-statusline-build.md)
ctx = PluginContext(PluginManifest(name="gh-ops", version="1.0.0", source="user", key="gh-ops"), Mgr())
mod.register(ctx)                 # Mgr: object with _plugin_tool_names=set(), _plugin_commands={}
entry = registry.get_entry("gh_ops")
entry.handler({"action": "me"})   # -> "Authenticated as painbaba" (live)
```

Registry dispatch is literally `entry.handler(args, **kwargs)` where `args`
is the model-passed tool-args dict (`tools/registry.py` ~line 694) — write
tool handlers as `def _tool(args: dict, **kwargs) -> str`.
