"""omni-parallel plugin: /swarm command family + swarm_plan tool.

NO hooks — zero per-turn cost. This plugin is the QUEUE / STATUS / JUDGE /
MERGE layer: it builds the plan and tracks tasks; the actual fan-out is driven
by the host agent (the model calls its own delegate_task per queue entry, using
the context pack this plugin produces). All handlers return strings, catch
exceptions, and never raise.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:  # package import when loaded by the host
    from .core import (
        DELIVERABLE_CONTRACT,
        TaskQueue,
        judge_results,
        make_context_pack,
        merge_plan,
        split_diff,
    )
except ImportError:  # direct-file / flat-sys.path fallback
    from core import (  # type: ignore
        DELIVERABLE_CONTRACT,
        TaskQueue,
        judge_results,
        make_context_pack,
        merge_plan,
        split_diff,
    )

__all__ = ["register", "cmd_swarm", "tool_swarm_plan"]

PLUGIN_DIR = Path(__file__).resolve().parent

USAGE = (
    "usage:\n"
    "  /swarm '3 | build the search index for each vendor'   queue N tasks + context packs\n"
    "  /swarm <plan.md|plan.json>                            load tasks from a plan file\n"
    "  /swarm 'brief...' --judge results.json                build plan, then judge results\n"
    "  /swarm status                                         queue state table\n"
    "  /swarm judge <results.json>                           score + best pick + rationale\n"
    "  /swarm split-pr <diff.txt>                            chunked merge plan (PRs)\n"
    "tool: swarm_plan(brief, n, template) -> plan text for host-driven fan-out"
)

_QUEUE: TaskQueue | None = None


def _get_queue() -> TaskQueue:
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = TaskQueue()
    return _QUEUE


# ------------------------------------------------------------- plan-file IO


def _load_tasks_from_plan_file(path: str) -> list[tuple[str, str, str]]:
    """Parse a plan file into [(id, brief, template)].

    Supports JSON (list or {"tasks": [...]}) and markdown bullets:
    "- id: brief" / "- id | brief" / "- brief" (auto ids task-N).
    """
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.lstrip()
    tasks: list[tuple[str, str, str]] = []
    if stripped.startswith("["):
        for i, item in enumerate(json.loads(text)):
            item = item if isinstance(item, dict) else {"brief": str(item)}
            tasks.append(
                (
                    str(item.get("id") or f"task-{i + 1}"),
                    str(item.get("brief", "")).strip(),
                    str(item.get("template", "default")),
                )
            )
    elif stripped.startswith("{"):
        for i, item in enumerate(json.loads(text).get("tasks", [])):
            item = item if isinstance(item, dict) else {"brief": str(item)}
            tasks.append(
                (
                    str(item.get("id") or f"task-{i + 1}"),
                    str(item.get("brief", "")).strip(),
                    str(item.get("template", "default")),
                )
            )
    else:  # markdown bullets
        for line in text.splitlines():
            line = line.strip()
            if not (line.startswith("-") or line.startswith("*")):
                continue
            body = line.lstrip("-* ").strip()
            m = re.match(r"^`?([\w.\-]+)`?\s*[:|]\s*(.+)$", body)
            if m:
                tasks.append((m.group(1), m.group(2).strip(), "default"))
            elif body:
                tasks.append((f"task-{len(tasks) + 1}", body, "default"))
    return tasks


# ------------------------------------------------------------ swarm builder


def _build_swarm(text: str) -> str:
    """Create TaskQueue entries + per-task context packs; print plan + recipe."""
    text = (text or "").strip()
    template = "default"
    tm = re.search(r"--template\s+(\w+)", text)
    if tm:
        template = tm.group(1)
        text = text.replace(tm.group(0), "").strip()

    entries: list[tuple[str, str, str]] = []
    if text and os.path.isfile(text):
        entries = _load_tasks_from_plan_file(text)
    else:
        m = re.match(r"^(\d+)\s*[|:]\s*(.+)$", text)
        if m:
            n = min(int(m.group(1)), 25)  # hard safety cap on one fan-out
            brief = m.group(2).strip()
            entries = [
                (f"task-{i}", f"{brief} — workstream {i}/{n}", template)
                for i in range(1, n + 1)
            ]
        elif text:
            entries = [(f"task-{i}", f"{text} — workstream {i}/3", template) for i in range(1, 4)]
        else:
            return USAGE

    queue = _get_queue()
    for tid, brief, tpl in entries:
        pack = make_context_pack(brief, repo_path=None, template=tpl)
        queue.add_task(tid, brief, context_pack=pack)

    lines = [
        f"SWARM PLAN — {len(entries)} task(s) queued (ids: {', '.join(e[0] for e in entries)})",
        "",
        queue.table(),
        "",
        f"JUDGE RUBRIC ({template}): deliverable path +30, verdict line +20, "
        "summary 1-20 lines +10, brief keywords up to +40; research adds sources, "
        "code adds tests.",
        "",
        "FAN-OUT (host-driven): for each task id above, run your delegate_task with "
        "the task's context_pack (queue state at plugins/omni-parallel/state.json).",
        "",
        "MERGE RECIPE: collect each task's diff -> /swarm split-pr <diff.txt> -> "
        "review chunks -> commit per chunk -> /swarm judge <results.json> to rank.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------- subcommands


def _run_judge(arg: str | None) -> str:
    if not arg:
        return "usage: /swarm judge <results.json> [--rubric default|code|research]"
    rubric = "default"
    rm = re.search(r"--rubric\s+(\w+)", arg)
    if rm:
        rubric = rm.group(1)
        arg = arg.replace(rm.group(0), "").strip()
    data = json.loads(Path(arg).read_text(encoding="utf-8"))
    results = data if isinstance(data, list) else data.get("results", [])
    out = judge_results(results, rubric=rubric)
    lines = [f"JUDGE (rubric={out['rubric']})", ""]
    for s in out["results"]:
        lines.append(
            f"  {s['id']:<14} score={s['score']:<3} {s['summary'][:70]}"
        )
    if out["best"]:
        lines += ["", f"BEST: {out['best']['id']} (score {out['best']['score']})", f"  {out['best']['rationale']}"]
    else:
        lines.append("(no results scored)")
    return "\n".join(lines)


def _run_split_pr(arg: str | None) -> str:
    if not arg:
        return "usage: /swarm split-pr <diff.txt> [--max-chunks N]"
    max_chunks = 4
    cm = re.search(r"--max-chunks\s+(\d+)", arg)
    if cm:
        max_chunks = int(cm.group(1))
        arg = arg.replace(cm.group(0), "").strip()
    diff = Path(arg).read_text(encoding="utf-8")
    chunks = split_diff(diff, max_chunks=max_chunks)
    return merge_plan(chunks)


# ------------------------------------------------------------- command entry


def cmd_swarm(args: str | None = None) -> str:
    try:
        args = (args or "").strip()
        toks = args.split()
        if not toks:
            return USAGE
        if toks[0] == "status":
            return _get_queue().table()
        if toks[0] == "judge":
            return _run_judge(" ".join(toks[1:]))
        if toks[0] == "split-pr":
            return _run_split_pr(" ".join(toks[1:]))
        if "--judge" in toks:  # build plan, then run the judge on results
            jidx = toks.index("--judge")
            judge_arg = toks[jidx + 1] if len(toks) > jidx + 1 else None
            rest = " ".join(toks[:jidx])
            return _build_swarm(rest) + "\n\n--- JUDGE ---\n" + _run_judge(judge_arg)
        return _build_swarm(args)
    except Exception as e:  # never raise
        return f"error: {e}"


def cmd_swarm_status(args: str | None = None) -> str:
    try:
        return _get_queue().table()
    except Exception as e:
        return f"error: {e}"


def cmd_swarm_judge(args: str | None = None) -> str:
    try:
        return _run_judge((args or "").strip())
    except Exception as e:
        return f"error: {e}"


def cmd_swarm_split_pr(args: str | None = None) -> str:
    try:
        return _run_split_pr((args or "").strip())
    except Exception as e:
        return f"error: {e}"


# --------------------------------------------------------------------- tool


def tool_swarm_plan(brief: str, n: int = 3, template: str = "default") -> str:
    """Build a fan-out plan: queue + context packs + host delegate instructions."""
    try:
        return _build_swarm(f"{int(n)} | {brief} --template {template}")
    except Exception as e:
        return f"error: {e}"


# ----------------------------------------------------------------- register


def register(ctx) -> str:
    """Host entry point: wire /swarm commands + swarm_plan tool."""
    try:
        ctx.register_command("swarm", cmd_swarm)
        ctx.register_command("swarm status", cmd_swarm_status)
        ctx.register_command("swarm judge", cmd_swarm_judge)
        ctx.register_command("swarm split-pr", cmd_swarm_split_pr)
        ctx.register_tool("swarm_plan", tool_swarm_plan)
    except Exception as e:
        return f"omni-parallel register failed: {e}"
    return (
        "omni-parallel registered: /swarm, /swarm status, /swarm judge, "
        "/swarm split-pr, tool swarm_plan (no hooks, zero per-turn cost)"
    )
