---
name: hermes-session-recovery
description: "Use when session_search 0-hits: query state.db directly."
---

# Hermes Session Recovery

When a user asks "what did we do about X" / "what's the agent got" / any vague
reference to a PAST or PARALLEL session, and `session_search` returns nothing,
the FTS index missed — that is NOT evidence the topic was never discussed.
Recover context from the underlying session store instead.

## Trigger

- User references something from a previous conversation without enough detail to pin it
- `session_search(query=...)` returns `{"count": 0, "sessions_searched": 0}` — note `sessions_searched: 0` is an index miss, not absence
- User runs multiple parallel Hermes sessions and jumps between them mid-question

## Workflow (in order)

### 1. Browse recent sessions (no query)
`session_search()` with no args lists recent sessions chronologically with
previews. Pick the 2-3 candidates that could hold the reference.

### 2. Read a session's tail
`session_search(session_id="...")` returns first 20 + last 10 messages.
The last 10 show where the conversation actually left off — usually enough to
place the user's reference.

### 3. Scroll into the middle
`session_search(session_id=..., around_message_id=N, window=14)` — pass any
id seen in a window to move forward/backward. Anchor ids are NOT sequential
per session; gaps are normal.

### 4. Direct DB queries (the reliable fallback)
When FTS 0-hits or you need a cross-session grep, query `state.db` read-only:

```bash
cd "$HERMES_HOME"   # e.g. C:\Users\HP\AppData\Local\hermes
python -c "
import sqlite3
con = sqlite3.connect('file:state.db?mode=ro', uri=True)  # read-only, no WAL lock issues
cur = con.cursor()
print([r[0] for r in cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")])
rows = cur.execute(\"\"\"
  SELECT m.id, m.session_id, m.role, substr(m.content, 1, 400)
  FROM messages m
  WHERE lower(m.content) LIKE '%term%'
  ORDER BY m.id DESC LIMIT 20
\"\"\").fetchall()
"
```

Key schema facts:
- Tables: `sessions`, `messages`, `messages_fts` (+ shadow tables), `async_delegations`
- `messages.content` holds both user text and JSON-serialized tool results
- `lower(content) LIKE '%term%'` is the reliable cross-session grep — FTS may be empty
- Filter `WHERE m.session_id NOT LIKE 'bg_%'` to skip background/orchestrator sessions if they pollute results

### 5. Check the pastes directory
User-pasted text (long pastes, pasted second-opinion responses, env dumps) lands in
`$HERMES_HOME/pastes/paste_<n>_<timestamp>.txt`. List newest first
(`ls -t pastes/`) and read the newest 1-2 before assuming the reference is
unexplained. Pastes are often the missing link between the user's two chats.

### 6. Recover a clobbered/overwritten file from tool-output history (verified R3)
If a shared or important file was accidentally truncated/overwritten (e.g. a
battle intel.md destroyed by a `write_file` call), past tool results in `state.db`
are a recovery source: every earlier `tail`/`read_file`/grep of that file is stored
as a JSON message. Recipe:

```python
import sqlite3, json, re
db = sqlite3.connect(r'C:\Users\HP\AppData\Local\hermes\state.db')
db.text_factory = lambda b: b.decode('utf-8','replace')
# find the biggest messages containing a signature line from the lost file
rows = db.execute("""SELECT m.id, length(m.content) AS L FROM messages m
  WHERE m.content LIKE '%<signature line from the file>%'
  ORDER BY L DESC LIMIT 25""").fetchall()
# unwrap JSON tool output; read_file dumps carry "N| " line-number prefixes — strip them
obj = json.loads(content)
inner = obj.get("content") or obj.get("output") or ""
clean = "\n".join(re.sub(r'^\d+\|', '', ln) for ln in inner.split("\n"))
```
Notes: prefer the LARGEST hits (full-file reads over tails); merge overlapping
chunks newest-first; mark the rebuilt file's header as rebuilt so sibling agents
re-append their own tails. Worked in practice: recovered ~55KB of a 160KB shared
log this way.

## Pitfalls

- **Never conclude "never discussed" from `sessions_searched: 0`.** Go to the DB.
- **search_files/rg can fail with "IO error: path not found" on long AppData paths** — use terminal + python sqlite3 for anything under `AppData\Local\hermes`.
- **Same background-process notifications appear in multiple parallel sessions** — a proc id in session A doesn't mean the work belongs to A.
- Anchor message ids jump (e.g. 541 → 2026); don't assume contiguity.
- `sqlite3.connect` needs `uri=True` with `mode=ro` to avoid touching the WAL while the live gateway holds the DB.

## Verification

Before answering the user, you should have: (a) the exact session(s) the
reference lives in, (b) the message id + content that matches, (c) the
conversation tail around it. If you only have (a), scroll or grep more —
guessing at a vague reference wastes a round-trip with this user.
