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

## Publish flow (stamp → push → index → install)

1. **Stamp** — `/skills publish <dir>` (or `core.publish_skill`) validates the
   skill (fail-closed; REJECT skills are refused outright) and stamps CREDIT
   into `SKILL.md` frontmatter:

   ```yaml
   author: <publisher>            # see credit policy below
   source: xomni                  # XOMNI publication stamp
   published_at: "2026-08-12"     # ISO date, set once, never rewritten
   origin: "painbaba/xomni"       # owner/repo of the source repo, if detectible
   ```

   The stamp is **idempotent**: publishing the same skill again never
   double-stamps and never changes the original `published_at`.

2. **Copy** — the skill lands at
   `<repo>/skills/<category>/<name>/` (category = first frontmatter tag,
   else `general`), already stamped.

3. **Push** — from the target repo:

   ```bash
   cd <repo>
   git add skills/<category>/<name>
   git commit -m "publish skill: <name>"
   git push
   ```

   The repo must be **public** for the directory to index it.

4. **Index** — once pushed, the skills.sh directory picks the repo up; anyone
   can then install:

   ```bash
   npx skills add <owner/repo>
   ```

   or inside XOMNI:

   ```
   /skills-marketplace <git-url>
   ```

5. **Receipt** — `/skills publish` prints a one-line receipt:
   `RECEIPT: name=<name> sha256=<64-hex> path=<target path> author=<publisher>`.
   The sha256 is a full content fingerprint of the published copy (paths +
   bytes of every file) — compare it later to detect drift.

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
/skills publish skills/<category>/<name> --repo=<path-to-public-repo>
```

- Default target repo is the XOMNI checkout itself (`XOMNI_HOME` or the plugin
  parent) — publish there to ship XOMNI's own skills.
- Use `--repo=` to publish into a fork or a dedicated market repo.
- `--author=` overrides the derived publisher for one publish.

## Command reference

| Command | Action |
|---|---|
| `/skills publish <dir> [--author=NAME] [--repo=<target>]` | validate → stamp → copy → push steps → skills.sh note → receipt |
| `/skills-marketplace <url-or-dir>` | install skills from a git marketplace (shallow clone, fail-closed) |
| `/skills-install <dir>` | install a skill/marketplace into the local skills surface |
| `/skills-scan <dir>` | inventory + security-validate skills |
| `/skills-search <query>` | search the skills DB + installed trees |

Python API (`plugins/omni-skills/core.py`): `publish_skill(skill_dir,
target_repo_dir, author=None, published_at=None, env=None, git_config=None)`,
plus `stamp_credit`, `derive_author`, `detect_origin`, `validate_skill`.
