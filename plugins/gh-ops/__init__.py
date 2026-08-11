"""gh-ops — GitHub/GitLab workflows via the gh/glab CLIs (strict parsing).

Registers:
  * slash command ``/gh status|prs [repo]|issues [repo]|me``
  * model tool ``gh_ops(action, repo?)``

Both share :func:`core.execute` — CLI output is parsed strictly (column
positions from the header line), never trusted as raw text. Errors (CLI
missing, not authenticated, network failure) come back as clean messages.
No hooks; nothing here alters agent behavior.
"""
from __future__ import annotations

from . import core

HELP = (
    "/gh status           show CLI availability + GitHub auth status\n"
    "/gh prs [repo]       list up to 20 pull requests (OWNER/REPO optional)\n"
    "/gh issues [repo]    list up to 20 issues (OWNER/REPO optional)\n"
    "/gh me               show the authenticated GitHub account\n"
)


def _handle_gh(raw: str) -> str:
    """Slash-command handler: ``fn(raw_args: str) -> str``."""
    raw = (raw or "").strip()
    if not raw:
        return core.execute("status")
    parts = raw.split(None, 1)
    action = parts[0].lower()
    repo = parts[1].strip() if len(parts) > 1 else ""
    return core.execute(action, repo or None)


def _tool_gh_ops(args: dict, **kwargs) -> str:
    """Model-tool handler: called by the registry as ``handler(args, **kwargs)``."""
    args = args or {}
    action = (args.get("action") or "status").strip().lower()
    repo = (args.get("repo") or "").strip() or None
    return core.execute(action, repo)


TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["status", "prs", "issues", "me"],
            "description": (
                "What to run: status (CLI + auth), prs (list up to 20 pull "
                "requests), issues (list up to 20 issues), me (current login)"
            ),
        },
        "repo": {
            "type": "string",
            "description": "Optional OWNER/REPO to scope prs/issues (defaults to the current repo)",
        },
    },
    "required": ["action"],
}


def register(ctx) -> None:
    ctx.register_command(
        "gh",
        handler=_handle_gh,
        description="GitHub/GitLab workflows via the gh/glab CLIs: auth status, PR list, issue list, current user",
        args_hint="status|prs [repo]|issues [repo]|me",
    )
    ctx.register_tool(
        name="gh_ops",
        toolset="gh_ops",
        schema=TOOL_SCHEMA,
        handler=_tool_gh_ops,
        description="Run GitHub workflows via the gh CLI: status, prs [repo], issues [repo], me",
    )
