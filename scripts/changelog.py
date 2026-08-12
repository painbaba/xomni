#!/usr/bin/env python3
"""Generate CHANGELOG.md from git log since the last tag (or full history if no tags).

Stdlib only. Groups commits by conventional-commit prefix
(feat/fix/docs/refactor/other), newest first, each entry with a short sha.
Writes CHANGELOG.md at the repo root.
"""
import datetime
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PREFIXES = ("feat", "fix", "docs", "refactor")
SECTION_ORDER = ["feat", "fix", "docs", "refactor", "other"]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    ).stdout


def last_tag() -> str | None:
    """Return the most recent tag reachable from HEAD, or None if no tags exist."""
    proc = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        return None
    tag = proc.stdout.strip()
    return tag or None


def main() -> None:
    tag = last_tag()
    if tag is not None:
        raw = git("log", "--pretty=format:%h|%s", f"{tag}..HEAD")
        since = f" since {tag}"
    else:
        raw = git("log", "--pretty=format:%h|%s")
        since = " (full history, no tags found)"

    groups = {p: [] for p in PREFIXES}
    groups["other"] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, subject = line.partition("|")
        match = re.match(r"^([a-z]+)(?:\([^)]*\))?(!)?:\s+", subject)
        prefix = match.group(1) if match else ""
        group = prefix if prefix in groups else "other"
        groups[group].append(f"- {sha} {subject}")

    lines = ["# Changelog", ""]
    lines.append(
        f"Generated {datetime.date.today().isoformat()} from git log{since}, newest first."
    )
    lines.append("")

    total = 0
    for section in SECTION_ORDER:
        entries = groups[section]
        if not entries:
            continue
        lines.append(f"## {section}")
        lines.append("")
        lines.extend(entries)
        lines.append("")
        total += len(entries)

    (REPO_ROOT / "CHANGELOG.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[changelog] wrote CHANGELOG.md: {total} entries{since}")


if __name__ == "__main__":
    main()
