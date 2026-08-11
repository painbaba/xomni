"""OmniMemory core — local semantic personal memory (OpenClaw-style, no external service).

Pure stdlib engine: a SQLite fact store under ~/.omni-memory with
remember / recall / consolidate / inject helpers. Consolidation uses a
plain gateway completion (urllib, browser UA) — same pattern as the
vision gateway in the context-loader plugin — so nothing depends on an
external memory vendor.

No Hermes imports in this module; unit-testable in isolation.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.request
from contextlib import closing
from pathlib import Path

STATE_DIR = Path(os.path.expanduser("~/.omni-memory"))
DB_PATH = STATE_DIR / "memory.db"

CONSOLIDATE_URL = "https://opencode.ai/zen/go/v1/chat/completions"
CONSOLIDATE_MODEL = "deepseek-v4-flash"
CONSOLIDATE_PROMPT = (
    "You are a memory consolidator for a personal AI assistant. The user's "
    "assistant collected the following facts over time. Merge them into at "
    "most 3 dense, factual sentences that preserve every distinct fact — "
    "no new facts, no flattery, no preamble. Output ONLY the merged text."
)
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}

CONSOLIDATE_THRESHOLD = 8      # consolidate once the store has >= this many facts
CONSOLIDATE_BATCH = 5          # oldest facts folded per consolidation pass
INJECT_MAX_CHARS = 900         # memory brief budget injected into a turn
INJECT_MIN_QUERY_LEN = 8       # only inject for non-trivial user messages


_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'user',
    created REAL NOT NULL,
    accessed REAL NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT ''
)
"""

_REQUIRED_COLS = {"id", "text", "source", "created", "accessed", "hits", "tags"}


def _schema_ok(db: sqlite3.Connection) -> bool:
    try:
        cols = {row[1] for row in db.execute("PRAGMA table_info(facts)")}
        return _REQUIRED_COLS <= cols
    except sqlite3.DatabaseError:
        return False


def _quarantine_corrupt_db() -> None:
    """Move a corrupt store aside so the next connect starts fresh.

    The target name is made unique so two corruptions inside the same
    second each keep their own evidence file.
    """
    if not DB_PATH.exists():
        return
    target = STATE_DIR / f"memory.db.corrupt-{int(time.time())}"
    n = 0
    while target.exists():
        n += 1
        target = STATE_DIR / f"memory.db.corrupt-{int(time.time())}-{n}"
    try:
        os.replace(str(DB_PATH), str(target))
    except OSError:
        try:
            os.remove(str(DB_PATH))
        except OSError:
            pass


def _conn() -> sqlite3.Connection:
    """Open the store; a corrupt/malformed DB is quarantined and rebuilt."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    db = None
    for attempt in range(2):
        try:
            db = sqlite3.connect(str(DB_PATH))
            db.execute(_SCHEMA)
            if not _schema_ok(db):
                raise sqlite3.DatabaseError("facts table is missing required columns")
            return db
        except sqlite3.DatabaseError:
            if db is not None:
                try:
                    db.close()
                except Exception:  # noqa: BLE001 — best-effort cleanup
                    pass
                db = None
            if attempt == 0:
                _quarantine_corrupt_db()
            else:
                raise
    raise RuntimeError("unreachable")


def remember(text: str, source: str = "user", tags: str = "") -> int:
    """Store one fact. Returns its row id. Blank facts are rejected."""
    text = (text or "").strip()
    if not text:
        raise ValueError("cannot remember an empty fact")
    now = time.time()
    with closing(_conn()) as db, db:
        cur = db.execute(
            "INSERT INTO facts (text, source, created, accessed, tags) VALUES (?,?,?,?,?)",
            (text, source, now, now, tags),
        )
        return int(cur.lastrowid)


def recall(query: str, limit: int = 5) -> list[dict]:
    """Rank stored facts by token overlap with the query, newest-first.

    Returns rows as dicts with id/text/source/created/hits and a 0-1 score.
    Pure, deterministic, and free of any embedding dependency.
    """
    query = (query or "").strip().lower()
    q_tokens = set(re.findall(r"[a-z0-9]+", query))
    rows = []
    with closing(_conn()) as db, db:
        for r in db.execute(
            "SELECT id, text, source, created, hits, tags FROM facts ORDER BY id"
        ):
            fid, text, source, created, hits, tags = r
            t_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
            if not q_tokens or not t_tokens:
                score = 0.0
            else:
                inter = len(q_tokens & t_tokens)
                score = inter / max(1.0, len(q_tokens)) if inter else 0.0
            rows.append(
                {
                    "id": fid,
                    "text": text,
                    "source": source,
                    "created": created,
                    "hits": hits,
                    "tags": tags,
                    "score": round(score, 3),
                }
            )
            db.execute("UPDATE facts SET accessed=?, hits=hits+1 WHERE id=?", (time.time(), fid))
    rows.sort(key=lambda d: (d["score"], d["created"]), reverse=True)
    return rows[:limit]


def inject_brief(query: str = "", max_chars: int = INJECT_MAX_CHARS) -> str:
    """Return a compact memory brief for the current turn, or '' when empty."""
    hits = recall(query, limit=6) if query else recall("", limit=6)
    lines = []
    budget = max_chars
    for h in hits:
        text = h["text"].replace("\n", " ").strip()
        if not text:
            continue
        line = f"- {text}"
        if len(line) > budget:
            break
        lines.append(line)
        budget -= len(line) + 1
    return "\n".join(lines)


def _gateway_complete(prompt: str, key: str, timeout: float = 120.0) -> str:
    """One non-streaming chat completion against the opencode gateway."""
    payload = {
        "model": CONSOLIDATE_MODEL,
        "messages": [
            {"role": "system", "content": CONSOLIDATE_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 600,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": BROWSER_UA["User-Agent"],
    }
    req = urllib.request.Request(
        CONSOLIDATE_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    data = json.loads(raw.decode("utf-8", errors="replace"))
    content = data["choices"][0]["message"]["content"]
    return str(content).strip()


def consolidate(key: str, threshold: int = CONSOLIDATE_THRESHOLD) -> dict:
    """Fold the oldest facts into one summary fact via the gateway.

    Returns {'consolidated': bool, 'before': n, 'after': m, 'error': ...}.
    Fails open: any gateway/parsing error leaves the store untouched.
    """
    with closing(_conn()) as db:
        total = db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        oldest = db.execute(
            "SELECT id, text FROM facts ORDER BY id LIMIT ?", (CONSOLIDATE_BATCH,)
        ).fetchall()
    if total < threshold or len(oldest) < 2:
        return {"consolidated": False, "before": total, "after": total, "error": None}
    prompt = "\n".join(f"{fid}: {text}" for fid, text in oldest)
    try:
        summary = _gateway_complete(prompt, key)
    except Exception as exc:  # noqa: BLE001 — fail open, never crash a turn
        return {"consolidated": False, "before": total, "after": total, "error": str(exc)}
    if not summary:
        return {"consolidated": False, "before": total, "after": total, "error": "empty summary"}
    with closing(_conn()) as db, db:
        db.execute(
            "INSERT INTO facts (text, source, created, accessed, tags) VALUES (?,?,?,?,?)",
            (summary, "consolidated", time.time(), time.time(), "consolidated"),
        )
        ids = [fid for fid, _ in oldest]
        db.execute(
            f"DELETE FROM facts WHERE id IN ({','.join('?' * len(ids))})", ids
        )
        after = db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    return {"consolidated": True, "before": total, "after": after, "error": None}


def load_key(env_path: str = r"C:\Users\HP\AppData\Local\hermes\.env") -> str | None:
    """Read OPENCODE_GO_API_KEY from the hermes .env file (never logged)."""
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                if name.strip() == "OPENCODE_GO_API_KEY":
                    return value.strip().strip('"').strip("'")
    except OSError:
        return None
    return None
