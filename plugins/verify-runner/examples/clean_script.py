"""Standalone ruff-clean script for the verify-runner example project."""

from __future__ import annotations


def main() -> int:
    """Print a greeting and return a zero exit code."""
    print("verify-runner example: all checks green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
