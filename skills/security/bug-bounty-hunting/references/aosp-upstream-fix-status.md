# AOSP upstream fix-status verification (disclosure readiness)

Worked example: giflib + libhevc + libavc AOSP decoder findings, Aug 2026.
Goal: determine, before disclosure, (1) the exact audited AOSP copy, (2) whether
AOSP main is fixed, (3) which Android release branches are affected, (4) whether
the canonical upstream is fixed. Output: a disclosure table + who-to-report-to
recommendations, written to a DISCLOSURE_READINESS.md in the audit workspace.

## Layer 1 — the audited AOSP copy
```
git -C <clone> log -1 --format='%H %cd %s'      # HEAD commit + date
git -C <clone> describe --tags                    # nearest tag, e.g. android-16.0.0_r3
```
AOSP upgrades codecs rarely. Measured: AOSP external/libhevc main HEAD =
`c83a76b` "Upgrade libhevc to v1.6.0" (2024-08-21) — IDENTICAL to the audited
copy. Same for libavc (`e67b0aa`, 2024-11-02). So a fuzzed local clone of an
AOSP external repo is usually still current main — state that in the report.

## Layer 2 — AOSP main + release branches
Release branches are `refs/heads/android13-release`, `android14-release`,
`android15-release` (branch NAMES — do not use tags). Branch tips are FROZEN
snapshots (libhevc android13-release tip = 2022-04-03, android14 = 2023-04-15,
android15 = 2024-06-08). Absence of a fix at the tip = authoritative "still
vulnerable in that Android version".

### Fetching a file version — two ways
1. googlesource `?format=TEXT` (returns BASE64, decode with `base64 -d`):
   `curl -s "https://android.googlesource.com/<repo>/+/refs/heads/<branch>/<path>?format=TEXT" | base64 -d > file.c`
2. git (preferred, robust): full clone once, then `git show`:
   `git clone --filter=blob:none https://android.googlesource.com/platform/external/<repo>`
   (~24MB for libhevc; blobs fetched on demand) then
   `git show refs/remotes/origin/<branch>:<path> | grep -n <bug-pattern>`
   and per-branch: `git -C <repo> fetch --filter=blob:none origin refs/heads/<b>:refs/remotes/origin/<b>`

### Rate-limit trap (measured)
Bursts of `?format=TEXT` fetches start returning **HTTP 404** (NOT 429) — easy to
misread as "wrong path/repo". Diagnosis: a single spaced fetch (sleep ~20s)
returns 200. Avoid the whole class: use the git-clone path for anything >1-2
fetches, and add retry-with-backoff if you must curl.

### Per-file last-touch (is the fix even ported?)
`git -C <repo> log -1 --format='%H %cd %s' refs/remotes/origin/main -- <path>`
Measured: libhevc files last touched 2019-01-09 / 2019-12-01 / 2023-07-21; libavc
parse_cavlc.c 2019-03-28 → any 2026-era upstream fix is by definition NOT in AOSP.

## Layer 3 — canonical upstream
- **libhevc / libavc**: `github.com/ittiam-systems/libhevc`, `.../libavc` (active,
  pushed within days). AOSP is a mirror — fixes land at Ittiam first.
- **giflib**: SourceForge `git.code.sf.net/p/giflib/code`. The old
  `TeamHypersomnia/giflib` (GitHub) and `gitlab.com/limx/giflib` URLs are DEAD
  (both 404) — do not reuse them. Upstream is 6.x while AOSP ships 5.2.

## Disclosure table template
| # | Finding (file:line) | Audited AOSP copy (ver/commit/date) | AOSP main fixed? | Branches affected | Upstream fixed? |
|---|---|---|---|---|---|
| (a) | giflib double-free `DGifDecreaseImageCounter` underflow, dgif_lib.c:1153 | 5.2, `425be06`, 2024-10-15 (android-16.0.0_r3) | NO | Android 16/main only (13/14/15 giflib lacks the fn entirely) | YES — 6.1.3 tag `edff4ae` has `if (ImageCount <= 0)` guard |
| (b) | libhevc NULL+offset, ihevcd_fmt_conv.c:779 | v1.6.0, `c83a76b`, 2024-08-21 | NO | 13/14/15/main | NO (Ittiam main line 855) |
| (c) | libhevc misaligned load, ihevcd_process_slice.c:1069 | same | NO | 13/14/15/main | NO |
| (d) | libhevc shift-UB, ihevcd_parse_residual.c:758 | same | NO | 13/14/15/main | PARTIAL — Ittiam `(UWORD32)value` cast, commit `5ad6b713` |
| (e) | libavc UEV OOB, ih264d_parse_cavlc.c:85 | v1.6.0, `e67b0aa`, 2024-11-02 | NO | 13/14/15/main | NO |

## Reporting routing
- All AOSP findings → Android Security Rewards (`g.co/androidsecurityreport`) +
  AOSP Issue Tracker, one report per library. Cite audited AOSP commit + exact
  line + sanitizer evidence + branch list.
- Upstream-unfixed classes ((b),(c),(e) here) = highest value: no fix exists
  anywhere; expect coordinated disclosure. Reference the partial upstream commit
  when one exists ((d) → `5ad6b713`).
- If upstream already fixed (giflib 6.1.3), the ask is "backport/sync", not a new
  vuln discovery.

## Pitfalls recap
- googlesource TEXT burst → 404; space requests or clone the repo.
- `git -C <repo>` ALWAYS when multiple clones exist; a bare `cd` silently greps
  the wrong repo and yields bogus zero counts (happened here; re-verify from the
  correct repo before trusting a "not present" answer).
- "Fixed upstream" ≠ "fixed in AOSP" — table needs both columns (Ittiam fixed (d)
  in Jun 2026; AOSP main untouched since 2019 for that file).
- Check `git describe --tags` on the local clone too: it reveals which Android
  security tag the audited copy corresponds to (android-security-16.0.0_r7 etc.).
