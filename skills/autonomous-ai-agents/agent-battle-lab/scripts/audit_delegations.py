#!/usr/bin/env python3
"""Audit Hermes delegation live transcripts: count REAL spawned subagents, thinkers, and markers.

Use when a swarm/city/battle report claims "N agents spawned" and you must verify against the
transcripts. Run with the HOST python via terminal (NOT inside the execute_code sandbox — its raw
FS view of cache/delegation is flaky; see references/population-census-audit.md).

Usage:
  python audit_delegations.py [live_dir] [--window "YYYY-MM-DD HH:MM" "YYYY-MM-DD HH:MM"] [--markers PATH]

  live_dir  default: ~/AppData/Local/hermes/cache/delegation/live
  --window  only include delegations started inside [start, end] (inclusive, ISO-ish strings)
  --markers count marker files (e.g. population/*.md) under PATH, reported separately

Per log it counts think/final/tool lines and flags:
  THINK  = substantive reasoning lines (>80 chars)  -> full-thinking agents
  THIN   = one-line confirmations (marker-task agents)
  TRUNC  = no final line (orchestrator killed mid-run -> its claimed spawns never happened)

Exit code 0 always; output is a table + totals you can paste into a registry/audit report.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

# Log lines look like: 12:29:25 think    | <content>  (multiple spaces before the pipe)
TS_KIND = re.compile(r"^(\d{2}:\d{2}:\d{2}) (think|final|tool|result|start|user|kickoff)")
SUBST_THRESHOLD = 80


def analyze_log(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return {"error": str(exc), "thinks": 0, "subst": 0, "finals": 0, "tools": 0, "trunc": True}
    thinks = subst = finals = tools = 0
    for line in text.splitlines():
        m = TS_KIND.match(line)
        if not m:
            continue
        kind = m.group(2)
        if kind == "think":
            thinks += 1
            if len(line) > SUBST_THRESHOLD:
                subst += 1
        elif kind == "final":
            finals += 1
        elif kind == "tool":
            tools += 1
    return {"thinks": thinks, "subst": subst, "finals": finals, "tools": tools,
            "trunc": finals == 0}


def parse_when(s):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError:
        sys.exit(f"bad --window timestamp: {s!r} (use 'YYYY-MM-DD HH:MM')")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("live_dir", nargs="?", default=os.path.expanduser(
        "~/AppData/Local/hermes/cache/delegation/live"))
    ap.add_argument("--window", nargs=2, metavar=("START", "END"),
                    help="only delegations started in [START, END]")
    ap.add_argument("--markers", metavar="PATH",
                    help="count marker files under PATH (e.g. a population/ dir)")
    args = ap.parse_args()

    win = tuple(parse_when(w) for w in args.window) if args.window else None
    rows = []
    for name in sorted(os.listdir(args.live_dir)):
        dd = os.path.join(args.live_dir, name)
        if not (name.startswith("deleg_") and os.path.isdir(dd)):
            continue
        manifest = {}
        mf = os.path.join(dd, "manifest.json")
        if os.path.exists(mf):
            try:
                manifest = json.load(open(mf, encoding="utf-8"))
            except (OSError, ValueError):
                manifest = {}
        started = manifest.get("started") or dt.datetime.fromtimestamp(
            os.path.getmtime(dd)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            started_dt = dt.datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            started_dt = dt.datetime.strptime(started, "%Y-%m-%d %H:%M")
        if win and not (win[0] <= started_dt <= win[1]):
            continue

        logs = sorted(f for f in os.listdir(dd) if f.startswith("task-") and f.endswith(".log"))
        claimed = manifest.get("task_count", len(logs))
        totals = {"thinks": 0, "subst": 0, "finals": 0, "tools": 0}
        truncated = 0
        for lg in logs:
            a = analyze_log(os.path.join(dd, lg))
            for k in totals:
                totals[k] += a[k]
            truncated += 1 if a["trunc"] else 0
        rows.append((name, started, len(logs), claimed, totals["thinks"], totals["subst"],
                     totals["finals"], totals["tools"], truncated))

    if not rows:
        print("no delegations found (check live_dir / --window)")
        return

    hdr = f"{'delegation':<16}{'started':<19}{'logs':>5}{'claimed':>8}{'think':>6}{'subst':>6}{'final':>6}{'tool':>6}{'trunc':>6}"
    print(hdr)
    print("-" * len(hdr))
    g = {"logs": 0, "think": 0, "subst": 0, "final": 0, "tool": 0, "trunc": 0}
    for name, started, logs, claimed, th, su, fi, to, tr in rows:
        print(f"{name:<16}{started:<19}{logs:>5}{claimed:>8}{th:>6}{su:>6}{fi:>6}{to:>6}{tr:>6}")
        g["logs"] += logs; g["think"] += th; g["subst"] += su
        g["final"] += fi; g["tool"] += to; g["trunc"] += tr
    print("-" * len(hdr))
    print(f"{'TOTAL':<16}{'':<19}{g['logs']:>5}{'':>8}{g['think']:>6}{g['subst']:>6}{g['final']:>6}{g['tool']:>6}{g['trunc']:>6}")
    print()
    print(f"REAL spawned subagents (task logs):      {g['logs']}")
    print(f"Full thinkers (substantive think lines): {g['subst']}")
    print(f"Truncated/killed agents (no final):      {g['trunc']}  "
          f"-> their claimed spawns likely never happened")
    if args.markers:
        n = sum(len(fs) for _, _, fs in os.walk(args.markers))
        print(f"Marker files under {args.markers}:       {n}  (files, NOT minds)")


if __name__ == "__main__":
    main()
