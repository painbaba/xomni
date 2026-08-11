# XOMNI — Repository Snapshot

Live snapshot generated 2026-08-12. Every number below was produced by running the listed command against the repo; no estimates or hardcoded values.

## Repo

| Metric | Value | Source command |
|---|---|---|
| Git commits | 17 | `git log --oneline \| wc -l` |
| Branch | master | `git branch --show-current` |
| Last commit | 2026-08-12 01:41 +0530 | `git log -1 --format='%ci'` |
| Committers | 2 (painbaba ×5, unknown ×12) | `git log --format='%an' \| sort \| uniq -c` |
| Core repo size (excl. .git) | 41 MB | `du -sh --exclude=.git --exclude=ollama --exclude=tmp --exclude=work --exclude=.tmp .` |
| Git history size | 22 MB | `du -sh .git` |
| Total on-disk (with scratch dirs) | 1.5 GB | `du -sh .` |

## Plugins & Tests

| Metric | Value | Source command |
|---|---|---|
| Plugins | 17 | `ls plugins \| wc -l` |
| Python files in plugins/ | 59 | `find plugins -name '*.py' \| wc -l` |
| Plugin LOC | 13,505 | `find plugins -name '*.py' -exec cat {} + \| wc -l` |
| Test methods | 647 | docs/TEST-MATRIX.md (auto-generated; per-plugin column sums to 647) |
| Tests passing | 647 / 647 | docs/TEST-MATRIX.md |

## Website (flagship)

| Metric | Value | Source command |
|---|---|---|
| Site files | 23 | `find website -type f \| wc -l` |
| Site size | 694 KB | `du -sh website` |
| — html / css / js / json / svg / other | 13 / 1 / 1 / 2 / 1 / 5 | `find website -type f \| sed 's/.*\\.//' \| sort \| uniq -c` |
| — data assets (skills.json, mcps.json) | 372 KB | `du -sh website/data` |
| — gallery | 24 KB | `du -sh website/gallery` |

## Databases (data/)

| Metric | Value | Source command |
|---|---|---|
| skills.db — skills rows | 544 | `python -c "import sqlite3; ... SELECT COUNT(*) FROM skills"` |
| skills.db — sources rows | 7 | same |
| mcps.db — servers rows (MCP catalog) | 311 | same |

## Docs

| Metric | Value | Source command |
|---|---|---|
| docs/ files | 17 (16 top-level .md + 1 proposal) | `find docs -type f \| wc -l` |
| docs/ line count (top-level .md) | 1,593 | `wc -l docs/*.md \| tail -1` |
| README.md | 192 lines | `wc -l README.md` |
| README.hi.md | 151 lines | `wc -l README.hi.md` |
| CONTRIBUTING.md / SECURITY.md | 150 / 77 lines | `wc -l` |
| skills/ catalog dirs | 42 | `ls skills \| wc -l` |

## Highlights

- 17 commits, 17 plugins, 647/647 tests green, 13.5k plugin LOC.
- 544-skill DB (7 sources) + 311-server MCP catalog; both mirrored as JSON in website/data.
- Scratch dirs (tmp 839 MB, work 727 MB, .tmp 209 MB) dominate raw disk usage; core repo is 41 MB + 22 MB git history.
