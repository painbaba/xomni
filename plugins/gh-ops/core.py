"""gh-ops core — pure stdlib GitHub/GitLab CLI integration helpers.

Parses ``gh pr list`` / ``gh issue list`` table output STRICTLY: column
positions are derived from the header line and rows are sliced by those
positions — never split on whitespace, because titles and labels contain
spaces. Empty-result messages, absent CLIs, auth failures and network errors
all collapse into stable, clean shapes.

No Hermes imports; unit-testable in isolation.
"""
from __future__ import annotations

import os
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
        start = starts.get(col)
        if start is None:
            row[col] = ""  # column absent from the header — never invent data
            continue
        if j + 1 < len(columns):
            end = starts.get(columns[j + 1], n)
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


def _resolve_exe(name: str) -> str:
    """Resolve *name* to its real executable, honoring .cmd/.bat shims (Windows).

    ``shutil.which`` honors PATHEXT on Windows, so ``npx`` resolves to
    ``npx.CMD``. subprocess with shell=False CAN launch the full path to a
    .cmd/.bat shim, but the bare name raises FileNotFoundError (CreateProcess
    does no PATHEXT search). Plain .exe tools (gh.exe, git.exe) work bare, so
    we only substitute when a shim is actually found.
    """
    found = shutil.which(name)
    if found and os.path.splitext(found)[1].lower() in (".cmd", ".bat"):
        return found
    return name


def run_gh(argv, timeout=30.0):
    """Run *argv* via subprocess; return ``{'ok', 'stdout', 'stderr', 'error'}``.

    Absent CLI (FileNotFoundError), timeouts and non-zero exits are translated
    into clean ``error`` strings instead of raising.
    """
    argv = list(argv)
    argv[0] = _resolve_exe(argv[0])  # .cmd shim fix: gh is gh.exe normally; npx-style shims need the full path
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


# ---------------------------------------------------------------------------
# PR review comments
# ---------------------------------------------------------------------------

# Known success wordings of `gh pr review` across versions:
#   "Reviewed pull request #42"
#   "Review submitted" / "Review posted"
REVIEW_OK_PATTERNS = (
    re.compile(r"reviewed pull request #\d+", re.IGNORECASE),
    re.compile(r"review (submitted|posted)", re.IGNORECASE),
)


def render_comment_body(comment):
    """Render one comment dict into the ``gh pr review --body`` string.

    *comment* is ``{"body": str, "path"?: str, "line"?: int}``. A position
    hint (path and optional line) becomes a ``[path:line]`` prefix so the
    reviewer can see where the comment applies; a bare body passes through
    unchanged. Never invents a hint when none was given.
    """
    body = (comment.get("body") or "").strip() if isinstance(comment, dict) else ""
    path = (comment.get("path") or "").strip() if isinstance(comment, dict) else ""
    line = comment.get("line") if isinstance(comment, dict) else None
    if path:
        hint = path
        if line is not None:
            try:
                hint = f"{path}:{int(line)}"
            except (TypeError, ValueError):
                pass  # non-numeric line -> keep the bare path hint
        return f"[{hint}] {body}" if body else f"[{hint}]"
    return body


def pr_review_argv(pr_number, body, repo=None):
    """Build the exact ``gh pr review <n> --comment --body <body>`` argv.

    Returns a list (never a shell string). *repo* is an optional
    ``OWNER/REPO`` appended as ``--repo`` when given.
    """
    argv = ["gh", "pr", "review", str(pr_number).strip(), "--comment", "--body", body]
    return argv + (["--repo", (repo or "").strip()] if (repo or "").strip() else [])


def pr_review_batch(pr_number, comments, repo=None):
    """Post a batch of review comments; return one result dict per comment.

    *comments* is an iterable of ``{"body", "path"?, "line"?}`` dicts. Each
    comment becomes its own ``gh pr review <n> --comment --body <text>`` call
    (position hints rendered into the body via :func:`render_comment_body`),
    so a failure in one comment never blocks the others. Empty bodies and
    non-dict entries are skipped — the plugin never posts empty comments.
    Result dicts are :func:`run_gh` shapes plus ``"body"`` (the rendered text).
    """
    results = []
    for comment in comments or []:
        body = render_comment_body(comment)
        if not body:
            continue
        res = run_gh(pr_review_argv(pr_number, body, repo))
        res["body"] = body
        results.append(res)
    return results


def pr_review_summary(pr_number, text, repo=None):
    """Post one review summary comment; return the :func:`run_gh` result dict."""
    return run_gh(pr_review_argv(pr_number, text, repo))


def parse_review_output(text, pr_number=None):
    """Classify ``gh pr review`` stdout into a clean, stable result string.

    Known success wordings collapse to ``"Posted review comment on PR #<n>."``;
    empty stdout (gh is quiet on some happy paths) gets the same treatment;
    anything unrecognized returns the raw first line verbatim — never fabricates.
    """
    out = (text or "").strip()
    if not out:
        return f"Posted review comment on PR #{pr_number}." if pr_number is not None else "Posted review comment."
    if any(p.search(out) for p in REVIEW_OK_PATTERNS):
        return f"Posted review comment on PR #{pr_number}." if pr_number is not None else "Review posted."
    return out.splitlines()[0]


def format_review_batch(results, pr_number):
    """Render batch results into one printable multi-line string."""
    if not results:
        return "No review comments to post."
    lines = []
    for res in results:
        if res.get("ok"):
            lines.append(parse_review_output(res.get("stdout"), pr_number))
        else:
            lines.append(res.get("error") or "gh command failed.")
    return "\n".join(lines)


def execute_pr_review(pr_number, text, repo=None):
    """Slash-command path: post one review comment (batch of one), printable."""
    if not detect_cli()["gh"]:
        return missing_cli_message()
    body = (text or "").strip()
    if not body:
        return f"pr-review needs a comment body: /gh pr-review {pr_number} <comment>"
    return format_review_batch(pr_review_batch(pr_number, [{"body": body}], repo), pr_number)


def execute_pr_summary(pr_number, text, repo=None):
    """Slash-command path: post a review summary comment, printable."""
    if not detect_cli()["gh"]:
        return missing_cli_message()
    body = (text or "").strip()
    if not body:
        return f"pr-summary needs text: /gh pr-summary {pr_number} <text>"
    res = pr_review_summary(pr_number, body, repo)
    if not res["ok"]:
        return res["error"]
    return parse_review_output(res.get("stdout"), pr_number)
