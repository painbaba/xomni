"""verify-runner — Hermes plugin wiring.

Exposes a model-callable tool ``verify_project`` (runs the project's tests +
linter in a directory and returns a PASS/FAIL verdict with the failing tail)
and a ``/verify [dir]`` slash command that prints the same summary. Closes
the "verify after every change" loop: one command, compact verdict.
"""
from __future__ import annotations

import os

from . import core

_CTX = None

HELP = (
    "/verify [dir] — run the project's tests (pytest/unittest) then lint "
    "(ruff/py_compile) and print a PASS/FAIL verdict with the failing tail.\n"
    "Defaults to the current working directory."
)


def verify_project(dir: str) -> str:
    """Run tests, then lint, in ``dir``; return the verdict summary string.

    Never raises for a bad directory — returns an error line instead.
    """
    if not dir:
        dir = os.getcwd()
    if not os.path.isdir(dir):
        return f"verify_project: not a directory: {dir}"
    parts = [f"VERIFY {dir}"]
    test_res = core.run_command(core.discover_test_command(dir), dir)
    parts.append(core.summarize(test_res, "TEST"))
    lint_cmd = core.discover_lint_command(dir)
    lint_res = None
    if lint_cmd:
        lint_res = core.run_command(lint_cmd, dir)
        parts.append(core.summarize(lint_res, "LINT"))
    for label, res in (("TEST", test_res), ("LINT", lint_res)):
        if res is not None and not res.get("ok"):
            tail = (res.get("stderr_tail") or "").strip() or (res.get("stdout_tail") or "").strip()
            if tail:
                parts.append(f"--- {label} failing tail ---")
                parts.append(tail)
    ok = bool(test_res.get("ok")) and (lint_res is None or bool(lint_res.get("ok")))
    parts.append(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    return "\n".join(parts)


def _verify_tool(params: dict) -> str:
    return verify_project((params or {}).get("dir") or "")


def _handle_verify(raw: str) -> str:
    return verify_project((raw or "").strip())


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_tool(
        "verify_project",
        toolset="file",
        schema={
            "description": (
                "Run the project's tests and linter in a directory and return a "
                "PASS/FAIL verdict with the failing output tail. The test command "
                "is discovered as pytest (fallback: python -m unittest discover); "
                "lint as ruff (fallback: python -m py_compile on changed files). "
                "Args: dir (directory to verify; default: current working "
                "directory). Read-only — never edits files."
            ),
            "type": "object",
            "properties": {
                "dir": {"type": "string", "description": "directory to run tests + lint in (default: cwd)"},
            },
        },
        handler=_verify_tool,
        description="Run tests + lint in a project dir and return a PASS/FAIL verdict",
        emoji="✅",
    )
    ctx.register_command(
        "verify", handler=_handle_verify,
        description="Run the project's tests + linter and print a PASS/FAIL verdict",
        args_hint="[dir]",
    )
