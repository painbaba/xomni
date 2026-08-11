# title-statusline

OpenCode-style statusline, Windows-native: makes the sponsor line written
by the `waitperk`/`perkline` modules **visible** in the terminal title bar
(the TUI core change is parked; the title bar is the one surface every CLI
user has open, at zero screen cost).

**What it does:** reads `~/.waitperk/current.txt` + `~/.perkline/current.txt`
(preferring perkline's line, which carries the pricing/model tier), pushes
the result into the title bar via `kernel32.SetConsoleTitleW` on Windows
(Unicode-safe) with an OSC 0 escape fallback everywhere else. Control
chars are stripped so sponsor content can never inject escapes; titles are
truncated to ~60 chars.

**Commands:** `/statusline [status|on|off|now]` (`off` restores a neutral
`[agent]` title; `now` force-refreshes). State lives in plugin-local
`state.json` (`enabled`).

**Speed posture:** single `post_tool_call` hook — stateless, cheap, and
wrapped in try/except so a title-bar failure can never break the agent;
all hooks return `None` (no-op-safe).

**Config:** plugin-local `state.json` (`enabled: true|false`); corrupt or
missing state falls back to defaults silently.

```bash
cd plugins/title-statusline && python -m unittest tests.test_core -v
```
