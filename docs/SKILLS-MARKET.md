# SKILLS MARKET — Cross-Session Skill Publishing (U11)

XOMNI's cross-session skill market: publish a skill once, and any session —
or any person on the internet — can install it. Skills are published to a
public git repo's `skills/` tree, indexed by the skills.sh directory, and
installed with `npx skills add <owner/repo>` or XOMNI's `/skills-marketplace`.

## The market (skills.sh)

- **Directory**: https://skills.sh — "The Agent Skills Directory" (Vercel app,
  9600+ skills as of 2026-08).
- **Content model**: plain git repos containing `SKILL.md` files. A repo's
  `source` in the directory is `owner/repo`.
- **Install**: `npx skills add <owner/repo>` (any repo with SKILL.md files),
  or inside XOMNI: `/skills-marketplace <git-url>` (shallow clone, fail-closed
  validation, cached under `~/.xomni-marketplaces`).

XOMNI's own `skills/<category>/<name>/SKILL.md` tree already matches this
content model — publish from it, or into a fork/dedicated market repo.

## Publish flow (stamp → host delegate → index → install)

`/skills publish` is **one** publish path — the plugin is the CREDIT layer,
the host CLI owns the actual publish. There is no separate/parallel publish
path in the plugin.

1. **Stamp** — `/skills publish <dir>` (or `core.publish_via_host`) validates
   the skill (fail-closed; REJECT skills are refused outright) and stamps
   CREDIT into `SKILL.md` frontmatter:

   ```yaml
   author: <publisher>            # see credit policy below
   source: xomni                  # XOMNI publication stamp
   published_at: "2026-08-12"     # ISO date, set once, never rewritten
   origin: "painbaba/xomni"       # owner/repo of the source repo, if detectible
   ```

   The stamp is **idempotent**: publishing the same skill again never
   double-stamps and never changes the original `published_at`.

2. **Delegate (host-first)** — if the host CLI is available (PATH check + a
   smoke `--help` call), the actual publish is delegated to it:

   ```bash
   hermes skills publish --to github <stamped-skill-dir>
   # --to ∈ {github, clawhub}, default github
   ```

   The plugin prints the exact delegated command, the host output, and a
   receipt. Captured host help (exact flags) lives in
   `plugins/omni-skills/README.md`.

3. **Fallback (host missing)** — only when `hermes skills publish` is not
   available does the plugin copy the skill into a repo's skills/ tree
   (`core.publish_skill`, `<repo>/skills/<category>/<name>/`), with a **loud
   note that host publish is preferred**. Push steps are printed:

   ```bash
   cd <repo>
   git add skills/<category>/<name>
   git commit -m "publish skill: <name>"
   git push
   ```

   The repo must be **public** for the directory to index it.

4. **Index** — once published, the skills.sh directory picks the repo up;
   anyone can then install:

   ```bash
   npx skills add <owner/repo>
   ```

   or inside XOMNI:

   ```
   /skills-marketplace <git-url>
   ```

5. **Receipt** — `/skills publish` prints a one-line receipt:
   `RECEIPT: name=<name> delegated=True target=github author=<publisher>`
   (delegated path), or with the full sha256 + path when the fallback copy
   ran. The sha256 is a full content fingerprint of the published copy
   (paths + bytes of every file) — compare it later to detect drift.

`--dry-run` stamps the skill and prints the exact delegated command
**without publishing** — safe to preview. `--repo=<target-repo-dir>` selects
the fallback copy target; the host CLI's `--repo` flag (a GitHub repo slug,
e.g. `openai/skills`) is host-side and documented in its help.

## Credit policy

- **Author is always preserved.** The publisher (derived automatically, never
  prompted) is stamped as `author`. If the skill already names its original
  creator in frontmatter, that credit is **never destroyed** — it is moved to
  `original_author` and both are published.
- **Derivation order**: explicit `--author=` flag → `XOMNI_USER` env var →
  `git config --get user.name` → `git config --get user.email` →
  `xomni-user`.
- `source: xomni` marks the stamp and drives idempotency; `origin` records the
  git repo the skill was published from (owner/repo), when detectible.
- Publish is **fail-closed**: missing skill dir, missing SKILL.md, or a
  REJECT security verdict → loud error, nothing copied, repo tree untouched.

## XOMNI-created skills

Anything under `skills/` in the XOMNI checkout is already skills.sh-compatible.
To get a XOMNI skill into the market:

```
/skills publish skills/<category>/<name> --to=github [--author=NAME]
```

- Default registry target is `github` (`--to=clawhub` for ClawHub); the actual
  publish is delegated to the host CLI (`hermes skills publish --to <target>`
  `<dir>`) after credit stamping.
- `--dry-run` stamps the skill and prints the exact delegated command without
  publishing.
- `--repo=<target-repo-dir>` selects the fallback copy target (used only when
  the host CLI is missing); default fallback repo is the XOMNI checkout itself
  (`XOMNI_HOME` or the plugin parent).
- `--author=` overrides the derived publisher for one publish.

## Command reference

| Command | Action |
|---|---|
| `/skills publish <dir> [--author=NAME] [--repo=<target>] [--to=github\|clawhub] [--dry-run]` | validate → stamp → **delegate to host** (`hermes skills publish --to <target>`) → skills.sh note → receipt; repo-copy fallback only when the host CLI is missing |
| `/skills-marketplace <url-or-dir>` | install skills from a git marketplace (shallow clone, fail-closed) |
| `/skills-install <dir>` | install a skill/marketplace into the local skills surface |
| `/skills-scan <dir>` | inventory + security-validate skills |
| `/skills-search <query>` | search the skills DB + installed trees |

Python API (`plugins/omni-skills/core.py`): `publish_via_host(skill_dir,
target="github", repo=None, author=None, published_at=None, env=None,
git_config=None, runner=None, dry_run=False, fallback_repo=None)` — the single
publish path (validate → stamp → host delegate → fallback), plus
`stamp_credit`, `derive_author`, `detect_origin`, `validate_skill`,
`build_publish_command`, `host_publish_available`, and `publish_skill` (the
repo-copy fallback).
