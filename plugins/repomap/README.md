# repomap

Aider-style symbol-level repo map for XOMNI. Scans a directory and returns a
compact map of files plus their top-level symbols (classes, functions, types)
so the model can navigate a codebase without dumping whole files. Honest v1
uses per-language regex extraction for 18 languages; tree-sitter is the
deferred upgrade (see `docs/PORT-PLAN.md` P3).

## What it does

- `build_map(root)` — depth-sorted file tree with `[symbol, ...]` lines
  (skips 30+ noise dirs, files > 500 KB; capped at 60 files / 6000 chars).
- `rank_files(root, query)` — aider-style "relevant files": scores files by
  symbol match (+3) > filename substring (+2) > symbol substring (+1).
- `stack_tags(root)` — local, private stack detection (extension scan only;
  nothing leaves the machine).

## Tools / commands

- Model tool: `repomap(path, query?)` — ranked map when `query` given,
  otherwise full map.
- Slash command: `/repomap [path] [query]` — interactive use.

## Speed posture

Pure stdlib, zero Hermes imports, zero hooks registered. Read-only — never
alters agent behavior or execution speed.

## Test

```bash
cd plugins/repomap && python -m unittest tests.test_core -v
```

## Config

None (no config file). Tuning knobs are module constants:
`DEFAULT_MAX_FILES = 60`, `DEFAULT_MAX_CHARS = 6000`, `MAX_FILE_BYTES = 500_000`.
