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
    "/verify [--coverage] [dir] — run the project's tests (pytest/unittest) "
    "then lint (ruff/py_compile) and print a PASS/FAIL verdict with the "
    "failing tail; with --coverage, run tests under stdlib line tracing and "
    "print per-file line coverage instead. Defaults to the current working "
    "directory."
)


def verify_project(dir: str, coverage: bool = False) -> str:
    """Run tests (+ lint, or coverage) in ``dir``; return the verdict string.

    ``coverage=True`` runs the tests under ``python -m trace`` (stdlib-only)
    and reports per-file covered/total lines instead of lint. Never raises
    for a bad directory — returns an error line instead.
    """
    if not dir:
        dir = os.getcwd()
    if not os.path.isdir(dir):
        return f"verify_project: not a directory: {dir}"
    if coverage:
        return _verify_coverage_report(dir)
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


def _verify_coverage_report(dir: str) -> str:
    """Render the stdlib coverage run: per-file rows + totals + verdict."""
    res = core.verify_coverage(dir)
    parts = [f"COVERAGE {dir}", core.summarize(res, "COVERAGE")]
    for row in res.get("rows", []):
        rel = os.path.relpath(row["file"], dir)
        parts.append(
            f"  {rel:<40} {row['covered']:>4}/{row['total']:<4} lines  {row['pct']:>3}%"
        )
    parts.append(f"TOTAL {res['covered']}/{res['total']} lines ({res['pct']:.1f}%)")
    parts.append(f"VERDICT: {'PASS' if res.get('ok') else 'FAIL'}")
    return "\n".join(parts)


def _verify_tool(params: dict) -> str:
    params = params or {}
    return verify_project(
        (params.get("dir") or ""), coverage=bool(params.get("coverage"))
    )


def _handle_verify(raw: str) -> str:
    raw = (raw or "").strip()
    coverage = False
    if raw.startswith("--coverage"):
        coverage = True
        raw = raw[len("--coverage"):].strip()
    return verify_project(raw, coverage=coverage)


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
                "Set coverage=True to run the tests under python -m trace instead "
                "(stdlib-only line coverage, per-file covered/total lines and pct). "
                "Args: dir (directory to verify; default: current working "
                "directory); coverage (bool, optional). Read-only — never edits files."
            ),
            "type": "object",
            "properties": {
                "dir": {"type": "string", "description": "directory to run tests + lint in (default: cwd)"},
                "coverage": {"type": "boolean", "description": "run tests under stdlib line tracing and report per-file coverage (default: false)"},
            },
        },
        handler=_verify_tool,
        description="Run tests + lint in a project dir and return a PASS/FAIL verdict",
        emoji="✅",
    )
    ctx.register_command(
        "verify", handler=_handle_verify,
        description="Run the project's tests + linter (or --coverage stdlib line coverage) and print a PASS/FAIL verdict",
        args_hint="[--coverage] [dir]",
    )
