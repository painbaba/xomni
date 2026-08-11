"""gh-ops core — pure stdlib GitHub/GitLab CLI integration helpers.

Parses ``gh pr list`` / ``gh issue list`` table output STRICTLY: column
positions are derived from the header line and rows are sliced by those
positions — never split on whitespace, because titles and labels contain
spaces. Empty-result messages, absent CLIs, auth failures and network errors
all collapse into stable, clean shapes.

No Hermes imports; unit-testable in isolation.
"""
from __future__ import annotations

import re
import shutil
import subprocess

# Column order matches `gh pr list` / `gh issue list` default TTY table output.
PR_COLUMNS = ("NUMBER", "TITLE", "BRANCH", "STATE", "DRAFT")
ISSUE_COLUMNS = ("NUMBER", "TITLE", "LABELS", "STATE")

# When stdout is piped (which is what subprocess capture always gets), gh
# switches to TAB-separated rows with NO header line — and the column ORDER
# differs from the pretty table:
#   gh pr list    -> number \t title \t branch \t state \t createdAt
#   gh issue list -> number \t state \t title \t labels \t createdAt
PR_TSV_COLUMNS = ("NUMBER", "TITLE", "BRANCH", "STATE", "CREATED")
ISSUE_TSV_COLUMNS = ("NUMBER", "STATE", "TITLE", "LABELS", "CREATED")

VALID_ACTIONS = ("status", "prs", "issues", "me")

GH_MISSING_MSG = "gh CLI not installed — install from https://cli.github.com"

# gh/glab empty-result wordings across versions, e.g.:
#   "No pull requests found"
#   "There are no open issues in octocat/Hello-World"
#   "No issues are currently open"
_EMPTY_PATTERNS = (
    re.compile(r"no (open )?(pull requests|issues?|results) (found|in )", re.IGNORECASE),
    re.compile(r"there are no (open )?(pull requests|issues?)", re.IGNORECASE),
    re.compile(r"no (open )?issues? (are )?currently (open|available)", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Table parsing
# ---------------------------------------------------------------------------


def _find_header(lines, required):
    """Return ``(line_index, {column: start_pos})`` for the header line.

    The header is the first line whose whitespace tokens contain every name
    in *required* (e.g. ``("NUMBER", "TITLE")``). Column start positions come
    from ``str.find`` in token order, so any spacing/width works.
    Returns ``None`` when no such line exists.
    """
    for i, line in enumerate(lines):
        tokens = line.split()
        if not all(tok in tokens for tok in required):
            continue
        starts = {}
        pos = 0
        for tok in tokens:
            idx = line.find(tok, pos)
            if idx < 0:
                break
            starts[tok] = idx
            pos = idx + len(tok)
        else:
            return i, starts
    return None


def _slice_row(line, starts, columns):
    """Slice one data line into ``{column: value}`` using header positions."""
    row = {}
    n = len(line)
    for j, col in enumerate(columns):
        start = starts[col]
        if j + 1 < len(columns):
            end = starts[columns[j + 1]]
        else:
            end = n
        row[col] = line[start:end].strip()
    return row


def _tsv_row(line, names):
    """Split one tab-separated gh row into ``{name: value}`` cells."""
    cells = line.split("\t")
    return {name: (cells[i].strip() if i < len(cells) else "") for i, name in enumerate(names)}


def _empty_result(lines):
    return any(p.search(line) for line in lines for p in _EMPTY_PATTERNS)


def _parse_table(text, columns, required_header, tsv_columns):
    """Shared strict table parser.

    Two accepted shapes, in order of preference:

    1. Header table (TTY-style): column positions derived from the header
       line, rows sliced by those positions (never split on whitespace).
    2. Piped TSV (real ``gh`` non-TTY output): rows split on tabs using the
       per-kind column order.

    Returns a list of ``{COLUMN: value}`` rows; blank lines and footer/hint
    lines (any line whose NUMBER cell is not a number) are skipped.
    """
    lines = (text or "").splitlines()
    if not lines or _empty_result(lines):
        return []
    found = _find_header(lines, required_header)
    if found is not None:
        hi, starts = found
        raw_rows = [_slice_row(ln, starts, columns) for ln in lines[hi + 1:] if ln.strip()]
    else:
        raw_rows = [_tsv_row(ln, tsv_columns) for ln in lines if ln.strip()]
    items = []
    for row in raw_rows:
        num_text = (row.get("NUMBER") or "").lstrip("#").strip()
        if not num_text.isdigit():
            continue  # e.g. 'Use `gh pr list --author @me` ...' footer
        row["NUMBER"] = num_text
        items.append(row)
    return items


def parse_pr_list(text):
    """Parse ``gh pr list`` output (TTY table or piped TSV).

    Returns a list of ``{number, title, branch, state, draft}`` dicts.
    Empty output (any 'no pull requests found' wording) yields ``[]``.
    The piped TSV format has no draft column, so ``draft`` is ``False``
    there — the parser never invents data.
    """
    items = []
    for row in _parse_table(text, PR_COLUMNS, ("NUMBER", "TITLE"), PR_TSV_COLUMNS):
        items.append({
            "number": int(row["NUMBER"]),
            "title": row["TITLE"],
            "branch": row["BRANCH"],
            "state": row["STATE"] or "UNKNOWN",
            "draft": (row.get("DRAFT") or "").strip().lower() == "true",
        })
    return items


def parse_issue_list(text):
    """Parse ``gh issue list`` output (TTY table or piped TSV).

    Returns a list of ``{number, title, labels, state}`` dicts.
    Empty output (any 'no issues found' wording) yields ``[]``.
    """
    items = []
    for row in _parse_table(text, ISSUE_COLUMNS, ("NUMBER", "TITLE", "STATE"), ISSUE_TSV_COLUMNS):
        items.append({
            "number": int(row["NUMBER"]),
            "title": row["TITLE"],
            "labels": row["LABELS"],
            "state": row["STATE"] or "UNKNOWN",
        })
    return items


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_summary(items, kind):
    """Render a compact human summary of parsed items.

    *kind* is ``"pr"`` or ``"issue"``. Empty input yields a short
    'No ... found.' line; otherwise a count header plus one line per item.
    """
    kind = (kind or "").strip().lower()
    if not items:
        if kind == "pr":
            return "No pull requests found."
        if kind == "issue":
            return "No issues found."
        return "Nothing found."
    label = {"pr": "PR", "issue": "issue"}.get(kind, "item")
    n = len(items)
    lines = [f"{n} {label}{'' if n == 1 else 's'}:"]
    for it in items:
        num, title = it["number"], it["title"]
        if kind == "pr":
            flags = [it.get("state") or "UNKNOWN"]
            if it.get("draft"):
                flags.append("draft")
            lines.append(
                f"  #{num} {title} [{', '.join(flags)}] branch: {it.get('branch') or '-'}"
            )
        else:
            line = f"  #{num} {title} [{it.get('state') or 'UNKNOWN'}]"
            if it.get("labels"):
                line += f" labels: {it['labels']}"
            lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI detection / invocation
# ---------------------------------------------------------------------------


def detect_cli():
    """Return ``{'gh': bool, 'glab': bool}`` via ``shutil.which``."""
    return {
        "gh": shutil.which("gh") is not None,
        "glab": shutil.which("glab") is not None,
    }


def missing_cli_message():
    """Human message describing which CLIs are absent (never fabricates)."""
    det = detect_cli()
    bits = []
    if not det["gh"]:
        bits.append("gh CLI not installed (install from https://cli.github.com)")
    if not det["glab"]:
        bits.append("glab CLI not installed (install from https://gitlab.com/gitlab-org/cli)")
    return " | ".join(bits) + "."


def gh_argv(action, repo=None):
    """Build the exact ``gh`` argv for *action* (list, never a shell string)."""
    action = (action or "").strip().lower()
    repo = (repo or "").strip()
    if action == "status":
        return ["gh", "auth", "status"]
    if action == "me":
        return ["gh", "api", "user", "--jq", ".login"]
    if action == "prs":
        argv = ["gh", "pr", "list", "--limit", "20"]
        return argv + (["--repo", repo] if repo else [])
    if action == "issues":
        argv = ["gh", "issue", "list", "--limit", "20"]
        return argv + (["--repo", repo] if repo else [])
    raise ValueError(f"unknown gh_ops action: {action!r}")


def classify_error(stderr, returncode):
    """Turn raw gh stderr into a clean, user-facing error message."""
    err = (stderr or "").strip()
    low = err.lower()
    if any(k in low for k in (
        "not logged in", "auth login", "authentication required", "please log in",
    )):
        return "gh is not authenticated — run 'gh auth login' first."
    if any(k in low for k in (
        "connection refused", "connection reset", "timed out", "timeout",
        "could not resolve host", "no such host", "network is unreachable",
        "failed to connect", "tls handshake", "http 5",
    )):
        first = err.splitlines()[0] if err else f"exit code {returncode}"
        return f"network error talking to GitHub: {first}"
    if not err:
        return f"gh command failed (exit code {returncode})."
    return f"gh error: {err.splitlines()[0]}"


def run_gh(argv, timeout=30.0):
    """Run *argv* via subprocess; return ``{'ok', 'stdout', 'stderr', 'error'}``.

    Absent CLI (FileNotFoundError), timeouts and non-zero exits are translated
    into clean ``error`` strings instead of raising.
    """
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "", "error": GH_MISSING_MSG}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "", "error": f"gh command timed out after {timeout:g}s."}
    if proc.returncode != 0:
        return {
            "ok": False,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "error": classify_error(proc.stderr or "", proc.returncode),
        }
    return {"ok": True, "stdout": proc.stdout or "", "stderr": proc.stderr or "", "error": None}


# ---------------------------------------------------------------------------
# Orchestration (shared by the /gh command and the gh_ops model tool)
# ---------------------------------------------------------------------------


def execute(action="status", repo=None):
    """Run a gh workflow end to end and return a clean printable string.

    *action*: ``status | prs | issues | me``; *repo* is an optional
    ``OWNER/REPO`` used by ``prs``/``issues``.
    """
    action = (action or "").strip().lower()
    if action not in VALID_ACTIONS:
        return (
            f"Unknown gh_ops action {action!r} — "
            "use: status | prs [repo] | issues [repo] | me"
        )
    if not detect_cli()["gh"]:
        return missing_cli_message()
    res = run_gh(gh_argv(action, repo))
    if not res["ok"]:
        return res["error"]
    out = (res["stdout"] or "").strip()
    if action == "status":
        det = detect_cli()
        return (
            f"gh: {'installed' if det['gh'] else 'NOT installed'} | "
            f"glab: {'installed' if det['glab'] else 'NOT installed'}\n"
            f"{out or 'gh auth status: OK'}"
        )
    if action == "me":
        return f"Authenticated as {out}" if out else "Authenticated (login unavailable)"
    if action == "prs":
        return format_summary(parse_pr_list(out), "pr")
    return format_summary(parse_issue_list(out), "issue")
