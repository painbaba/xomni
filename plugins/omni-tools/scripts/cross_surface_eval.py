#!/usr/bin/env python3
"""Cross-surface recall eval runner for omni-tools.

Scores recall@k per surface (plugin / MCP / skill / mixed) and overall
against the 50 planted queries in data/cross_surface_eval.json, and writes
the per-case report to data/cross_surface_report.json (repo root).

Usage:
    python scripts/cross_surface_eval.py [--top-k 5] [--cases PATH] [--report PATH]

Pure stdlib; thin CLI wrapper over core.cross_surface_recall().
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--top-k", type=int, default=5,
                        help="recall cutoff k (default: 5)")
    parser.add_argument("--cases", type=Path, default=None,
                        help="path to the eval cases JSON (default: "
                             "data/cross_surface_eval.json)")
    parser.add_argument("--report", type=Path, default=None,
                        help="path for the JSON report (default: "
                             "data/cross_surface_report.json)")
    args = parser.parse_args()

    result = core.cross_surface_recall(
        cases_path=args.cases, top_k=args.top_k, report_path=args.report
    )
    print()
    print(f"overall recall@{result['top_k']}: {result['overall_recall']:.3f} "
          f"({result['queries']} queries)")
    if result.get("report_path"):
        print(f"report written: {result['report_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
