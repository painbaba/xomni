"""omni-parallel core: TaskQueue, context-pack builder, Judge, PR-split helper.

Pure Python stdlib. No host imports — this module is safe to import and test
standalone. The plugin layer (__init__.py) wires these into the /swarm command
family and the swarm_plan tool. Nothing here ever raises on bad input: corrupt
state, missing templates, and unparseable diffs degrade to empty/safe results.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PLUGIN_DIR / "templates"
DEFAULT_STATE_PATH = PLUGIN_DIR / "state.json"

DELIVERABLE_CONTRACT = (
    "write files to <out> (create directories as needed); end your summary under "
    "10 lines; touch nothing outside <out>; finish with a verdict line: "
    "VERDICT: done | partial | blocked"
)

_FALLBACK_TEMPLATE = """TASK: {brief}
REPO: {repo}
OUT: {out}

GOAL
- {brief}

CONSTRAINTS
- work only inside <out>; never modify files outside it
- use only the stdlib / already-installed dependencies; no network unless the brief says so

DELIVERABLE CONTRACT
- {contract}

ISOLATION NOTE
- you are one parallel worker among several; do not assume sibling outputs exist
- if you need something from another task, note it in your summary instead of blocking

FINAL VERDICT
- last line of your summary: VERDICT: done | partial | blocked
"""

_KEYWORD_STOP = {
    "about", "after", "again", "against", "being", "brief", "could", "done",
    "file", "files", "final", "from", "have", "into", "line", "lines", "more",
    "most", "must", "only", "other", "over", "path", "result", "should", "some",
    "summary", "task", "than", "that", "their", "there", "these", "they", "this",
    "those", "through", "under", "using", "verdict", "were", "what", "when",
    "where", "which", "while", "with", "work", "would", "write", "your", "out",
    "the", "and", "for", "not", "are", "was", "you", "will", "can", "all",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ TaskQueue


class TaskQueue:
    """JSON-persisted queue, deduped by id, in-memory for the session.

    Every mutation persists to ``state_path`` (best-effort, atomic tmp+rename).
    A corrupt or unreadable state file never raises — it falls back to empty.
    """

    def __init__(self, state_path: str | Path | None = None):
        self.state_path = Path(state_path) if state_path else DEFAULT_STATE_PATH
        self.tasks: dict[str, dict] = {}
        self.corrupt = False
        self._load()

    def _load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            tasks = data.get("tasks", []) if isinstance(data, dict) else data
            self.tasks = {
                t["id"]: t
                for t in tasks
                if isinstance(t, dict) and "id" in t
            }
        except Exception:
            self.corrupt = True
            self.tasks = {}

    def _persist(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_name(self.state_path.name + ".tmp")
            tmp.write_text(
                json.dumps({"tasks": list(self.tasks.values())}, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.state_path)
        except Exception:
            pass  # persistence is best-effort; never raise

    def add_task(self, task_id, brief, context_pack=None, status="pending"):
        task_id = str(task_id)
        existing = self.tasks.get(task_id)
        if existing is not None:  # auto-dedupe by id
            return existing
        task = {
            "id": task_id,
            "brief": brief,
            "context_pack": context_pack or "",
            "status": status,
            "created_at": _now(),
            "updated_at": _now(),
            "result": None,
            "error": None,
        }
        self.tasks[task_id] = task
        self._persist()
        return task

    def _transition(self, task_id, status, **extra):
        task = self.tasks.get(str(task_id))
        if task is None:
            return None
        task.update({"status": status, "updated_at": _now()})
        task.update(extra)
        self._persist()
        return task

    def claim(self, task_id):
        return self._transition(task_id, "in_progress")

    def complete(self, task_id, result=None):
        return self._transition(task_id, "done", result=result)

    def fail(self, task_id, error=None):
        return self._transition(task_id, "failed", error=error)

    def retry(self, task_id):
        task = self.tasks.get(str(task_id))
        if task is None:
            return None
        task.update({"status": "pending", "updated_at": _now(), "error": None})
        self._persist()
        return task

    def get(self, task_id):
        return self.tasks.get(str(task_id))

    def list(self, status=None):
        items = list(self.tasks.values())
        if status:
            items = [t for t in items if t["status"] == status]
        return sorted(items, key=lambda t: t["created_at"])

    def counts(self) -> dict:
        return dict(Counter(t["status"] for t in self.tasks.values()))

    def table(self) -> str:
        if not self.tasks:
            return "(queue is empty)"
        rows = [("ID", "STATUS", "BRIEF")]
        for t in self.list():
            brief = t["brief"].replace("\n", " ")[:60]
            rows.append((t["id"], t["status"], brief))
        widths = [max(len(r[i]) for r in rows) for i in range(3)]
        lines = [
            "  ".join(h.ljust(widths[i]) for i, h in enumerate(rows[0])),
            "-" * (sum(widths) + 4),
        ]
        for r in rows[1:]:
            lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(r)))
        counts = self.counts()
        lines.append("counts: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        return "\n".join(lines)


# ------------------------------------------------------- context-pack builder


def make_context_pack(task_brief: str, repo_path=None, template: str = "default") -> str:
    """Build a self-contained per-task context block from templates/<t>.txt.

    Missing template files fall back to a builtin default (never raises).
    """
    tpl_name = str(template)
    if not tpl_name.endswith(".txt"):
        tpl_name += ".txt"
    try:
        text = (TEMPLATES_DIR / tpl_name).read_text(encoding="utf-8")
    except Exception:
        text = _FALLBACK_TEMPLATE
    out = str(repo_path) if repo_path else "<out>"
    repo = str(repo_path) if repo_path else "(no repo — current dir is the workspace)"
    return text.format(
        brief=str(task_brief).strip(),
        repo=repo,
        out=out,
        contract=DELIVERABLE_CONTRACT,
    )


# ---------------------------------------------------------------------- Judge


def _brief_keywords(brief: str) -> list:
    words = re.findall(r"[a-z0-9]{5,}", str(brief or "").lower())
    return sorted({w for w in words if w not in _KEYWORD_STOP})


def judge_results(results: list[dict], rubric: str = "default") -> dict:
    """Deterministically score each result and pick the best. No LLM.

    Each result may carry: id, brief, text, summary, verdict,
    deliverable_path, sources, citations, tests.

    Rubrics:
      default  — deliverable path, verdict line, summary-length sanity, brief keywords
      code     — default + tests/verdict-signal presence
      research — default + URL sources + [n] citations
    """
    rubric = rubric if rubric in ("default", "code", "research") else "default"
    scored = []
    for i, r in enumerate(results or []):
        r = r or {}
        rid = str(r.get("id") or f"result-{i}")
        text = " ".join(
            str(r.get(k, "")) for k in ("text", "summary", "verdict") if r.get(k)
        )
        text_l = text.lower()
        checks = {}

        score = 0
        dp = str(r.get("deliverable_path") or "")
        if dp:
            score += 30
            checks["deliverable"] = dp
        else:
            checks["deliverable"] = "missing"

        has_verdict = bool(
            re.search(r"VERDICT\s*:\s*(DONE|PARTIAL|BLOCKED)", text.upper())
        )
        if has_verdict:
            score += 20
            checks["verdict"] = "ok"
        else:
            checks["verdict"] = "missing"

        summary = str(r.get("summary") or text)
        n = len([ln for ln in summary.splitlines() if ln.strip()])
        if 1 <= n <= 20:
            score += 10
            checks["length"] = f"{n} lines (ok)"
        elif n > 50:
            score -= 10
            checks["length"] = f"{n} lines (too long)"
        else:
            score += 5
            checks["length"] = f"{n} lines"

        kw = _brief_keywords(r.get("brief"))
        if kw:
            matched = sum(1 for w in kw if w in text_l)
            score += round(matched / len(kw) * 40)
            checks["keywords"] = f"{matched}/{len(kw)}"

        if rubric == "code":
            if "test" in text_l or r.get("tests"):
                score += 15
                checks["tests"] = "present"
        elif rubric == "research":
            urls = re.findall(r"https?://\S+", text)
            if urls:
                score += min(len(urls), 2) * 15
                checks["sources"] = len(urls)
            cites = re.findall(r"\[\d+\]", text)
            if cites:
                score += 10
                checks["citations"] = len(cites)

        score = max(0, int(score))
        first_line = next(
            (ln.strip() for ln in summary.splitlines() if ln.strip()), ""
        )[:100]
        scored.append({"id": rid, "score": score, "checks": checks, "summary": first_line})

    best = None
    if scored:
        top = max(scored, key=lambda s: (s["score"], s["id"]))  # deterministic tie-break
        bits = [f"{k}={v}" for k, v in top["checks"].items()]
        best = {
            "id": top["id"],
            "score": top["score"],
            "rationale": f"best={top['id']} score={top['score']} ({', '.join(bits)})",
        }
    return {"rubric": rubric, "results": scored, "best": best}


# ---------------------------------------------------------------- PR-split


_DIFF_HDR = re.compile(r"^diff --git a/(\S+) b/(\S+)")
_TPLUS = re.compile(r"^\+\+\+ b/(\S+)")


def _parse_diff(diff_text: str) -> dict:
    """Split a unified diff into {path: [lines]}."""
    files: dict = {}
    cur = None
    for line in (diff_text or "").splitlines():
        m = _DIFF_HDR.match(line)
        if m:
            cur = m.group(2)
            files.setdefault(cur, []).append(line)
            continue
        if cur is None:
            m2 = _TPLUS.match(line)
            if m2:
                cur = m2.group(1)
                files.setdefault(cur, []).append(line)
                continue
        if cur is not None:
            files[cur].append(line)
    return files


def _prefix_of(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "plugins":
        return "/".join(parts[:2])
    return parts[0] if parts else path


def _suggest_commit(prefix: str, files: list) -> str:
    return f"feat({prefix}): update {len(files)} file(s)"


def split_diff(diff_text: str, max_chunks: int = 4) -> list[dict]:
    """Group diff hunks into logical chunks by path prefix (e.g. plugins/<name>/).

    Each chunk: {title, files, diff, commit_message}. Deterministic ordering;
    chunks beyond ``max_chunks`` fold into the last chunk.
    """
    files = _parse_diff(diff_text)
    if not files:
        return []
    max_chunks = max(1, int(max_chunks))
    groups: dict = {}
    for path, lines in files.items():
        groups.setdefault(_prefix_of(path), []).append((path, lines))

    order = sorted(groups)
    chunks = []
    if len(order) <= max_chunks:
        for prefix in order:
            chunk_files = [p for p, _ in groups[prefix]]
            diff = "\n".join(ln for _, ls in groups[prefix] for ln in ls)
            chunks.append(
                {
                    "title": prefix,
                    "files": chunk_files,
                    "diff": diff,
                    "commit_message": _suggest_commit(prefix, chunk_files),
                }
            )
    else:
        tail_chunk = None
        for i, prefix in enumerate(order):
            if i < max_chunks - 1:
                chunk_files = [p for p, _ in groups[prefix]]
                diff = "\n".join(ln for _, ls in groups[prefix] for ln in ls)
                chunks.append(
                    {
                        "title": prefix,
                        "files": chunk_files,
                        "diff": diff,
                        "commit_message": _suggest_commit(prefix, chunk_files),
                    }
                )
            else:  # fold the whole tail into ONE extra chunk
                if tail_chunk is None:
                    tail_chunk = {"title": "misc", "files": [], "diff": ""}
                    chunks.append(tail_chunk)
                for path, lines in groups[prefix]:
                    tail_chunk["files"].append(path)
                    tail_chunk["diff"] += "\n" + "\n".join(lines)
        if tail_chunk is not None:
            tail_chunk["commit_message"] = _suggest_commit("misc", tail_chunk["files"])
    return chunks


def merge_plan(chunks: list[dict]) -> str:
    """Human-readable merge report: per-chunk files + suggested commit message."""
    if not chunks:
        return "(no diff chunks parsed — empty or unrecognized diff)"
    lines = ["MERGE PLAN — split into separate PRs", ""]
    for i, c in enumerate(chunks, 1):
        lines.append(f"PR {i}: {c['title']}")
        lines.append(f"  files ({len(c['files'])}):")
        for f in c["files"]:
            lines.append(f"    - {f}")
        lines.append(f"  suggested commit: {c['commit_message']}")
        lines.append("")
    return "\n".join(lines)
