# War Room — wiring the live battle viewer

## What it is
A stdlib-only Python server + HTML page that streams BOTH sides of an agent battle
(ghost attackers vs defender teams) in real time, using Hermes' own delegation
transcripts as the observation channel.

## Files (C:\Users\HP\ai-workforce\warroom\)
- `warroom.py` — server on 127.0.0.1:8790; endpoints `/` (UI) and `/api/state` (JSON)
- `warroom.html` — two-column UI, auto-refresh 2s, auto-scroll
- `battle_config.template.json` — config template for a real battle

## How it observes agents
Hermes writes every subagent's stream to:
`C:\Users\HP\AppData\Local\hermes\cache\delegation\live\<deleg_id>\task-N.log`
Lines look like: `23:13:53 think    | text` / `tool     | -> terminal(...)` / `result  | ...`
The parser classifies think (purple, italic), action (amber), result (green),
final (pink) — so the user literally reads the agents' reasoning as it happens.

## Config format (battle_config.json)
```json
{
  "columns": [
    {"label": "👻 GHOST", "side": "ghost", "color": "#ef4444",
     "files": ["C:/Users/HP/AppData/Local/hermes/cache/delegation/live/deleg_GHOST/task-*.log"]},
    {"label": "🛡 DEFENDERS (10)", "side": "def", "color": "#3b82f6",
     "files": [".../deleg_DEF1/task-*.log", ".../deleg_DEF2/task-*.log"]}
  ],
  "intel": "C:/Users/HP/ai-workforce/ghost-lab/ghost_sandbox/intel.md",
  "bank_log": "C:/Users/HP/ai-workforce/bank-war/bank_defense.log"
}
```
- **files[] supports GLOB patterns** (`task-*.log`, `deleg_*`): the server
  resolves them per request, so you can pre-write the config with a placeholder
  deleg id and it lights up the moment the real delegation dir appears — no
  need to know the exact deleg IDs ahead of time. Nonexistent paths = blank
  column (which is exactly what you want pre-battle).
- **Config reloads PER REQUEST** (load_config() inside do_GET, not at startup):
  edit battle_config.json mid-battle and the next 2s poll picks it up — no
  server restart needed.
- **Battle-pure mode (user preference)**: for a real battle the config should
  contain ONLY the two battle columns (👻 GHOST red + 🛡 DEFENDERS blue) —
  NOT the builder swarms or past battles. The user explicitly wants to see only
  the two sides, blank until they act ("only show me defenders and ghost now
  blank when they in act i will see them only"). Auto-discover mode (no config)
  is for pre-battle watching of builders; write battle_config.json to switch to
  battle-pure.
- With NO config file present, `warroom.py` auto-discovers the 3 most recently
  modified delegation dirs and shows them as columns (useful pre-battle to watch
  builder swarms).

## Start
```
cd C:\Users\HP\ai-workforce\warroom && python warroom.py 8790
```
Then open http://127.0.0.1:8790

## Gotchas
- Transcripts are append-only; the API returns last ~150 events per column.
- intel.md and bank_defense.log are tailed (last 60/40 lines) — these show the
  shared battlefield state and defender-side event stream.
- **SCROLL-LOCK (user correction — do not regress)**: scrolling UP must NOT snap
  back to bottom on the 2s refresh. Preserve each column's scrollTop across
  re-renders (save before innerHTML swap, restore after); autoscroll ONLY when
  the user is at the bottom (`scrollHeight - scrollTop - clientHeight > 60px` =
  user scrolled up). Show a floating "⬇ live" button when scrolled up; click
  jumps to latest. Implemented in warroom.html via per-column ids (`col_g`/
  `col_d`), a capture-phase scroll listener, and a sticky-positioned button.
- The user asked for this explicitly ("find a way I will see it in real the
  thoughts of both sides") — ALWAYS spin up the war room BEFORE launching a
  battle, and point battle_config.json at the live deleg IDs once spawned.
