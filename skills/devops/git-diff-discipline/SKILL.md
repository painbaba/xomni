---
name: git-diff-discipline
description: "Use when applying code edits: keep diffs small, reviewed."
version: 1.0.0
author: unified-agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, diff, code-review, aider, surgical-patches]
    related_skills: [github-pr-workflow, requesting-code-review]
---

# Git Diff Discipline — Surgical Patches for AI Coding Agents

A port of Aider's P5 philosophy: small, reviewable, surgical patches. Every code change runs the same loop — check scope, apply, review the diff, test, stage deliberately, commit.

## TRIGGER

Use this skill whenever you are about to apply multi-file or risky code edits, **or** after any code change (before reporting completion). When in doubt, run it — the loop costs seconds and prevents unreviewable messes.

## CORE DISCIPLINE STEPS

1. **Make ONE logical change at a time.** One bug fix, one feature, one refactor per step. If the task bundles several, decompose it into a sequence of steps and do them one by one.

2. **Before applying, check the current scope:**
   ```bash
   git status
   git diff --stat
   ```
   This shows what is already dirty (untracked, modified, staged) so you never build a change on top of an unknown tree.

3. **Apply the change, then IMMEDIATELY review the actual diff:**
   ```bash
   git diff          # unstaged changes
   git diff --cached # staged changes
   ```
   Read every hunk. If you cannot explain a line, revert or fix it before moving on. Never assume "it should look right" — read what git actually recorded.

4. **Reject giant diffs.** If the change touches more than ~10 files or more than ~300 lines, STOP. Split it into smaller, reviewed steps and re-run steps 2–3 for each slice. This is Aider's core rule: small, reviewable, surgical patches.

5. **Verify after every change — run the tests:**
   ```bash
   pytest                 # or: python -m pytest
   python -m unittest discover
   ```
   Run the relevant suite (at minimum the tests covering the touched module). Never claim success without running them.

6. **Stage deliberately with `git add -p`** to keep unrelated changes out of a commit:
   ```bash
   git add -p path/to/file.py
   ```
   Interactive partial staging commits only the hunks that belong to the logical change. Stage whole files only when the file is 100% part of the change.

7. **Commit with a message describing the WHY** — intent and motivation, not a paraphrase of the diff:
   ```bash
   git commit -m "fix: retry on transient 503s so the sync job stops dying mid-run"
   ```

8. **Never force-push to shared branches.** `git push --force` (or `--force-with-lease`) rewrites history others may have based work on. If a push is rejected, pull/rebase and push normally. Force-push only your own unpublished feature branch, and only with `--force-with-lease`.

9. **Keep the working tree clean between tasks:**
   ```bash
   git stash   # park WIP before switching context
   git commit  # or land the finished change
   ```
   Start the next task from a clean `git status` so the scope check in step 2 stays trustworthy.

## BEFORE/AFTER CHECKLIST

**Before making a change:**
- [ ] `git status` run — I know exactly what is dirty right now
- [ ] `git diff --stat` run — I know the current scope of uncommitted work
- [ ] The change is ONE logical change (if not, I split it into steps first)
- [ ] I know which files this change will touch (<10 expected)

**After making a change:**
- [ ] `git diff` / `git diff --cached` reviewed hunk-by-hunk — no surprise lines
- [ ] Diff is small: ≤~10 files, ≤~300 lines (if bigger, I split it and re-reviewed)
- [ ] Tests actually ran and passed — pytest/unittest output shown, exit code 0
- [ ] Only related hunks staged (`git add -p` used wherever the tree was dirty)
- [ ] Commit message explains the WHY
- [ ] `git status` clean, or WIP stashed for the next task

## PITFALLS

- **Unreviewed diffs.** Applying a change and reporting success without reading `git diff`. The diff is the ground truth — read it every time.
- **Tests skipped.** Claiming success because "it probably works", or declaring done before running the suite. Tests are the only proof of success; run them and read the exit code.
- **Giant diffs.** One mega-change across 20 files and 800 lines. Undo, split, and review each slice (step 4).
- **Unrelated changes bundled.** Formatting, renames, or drive-by fixes mixed into a feature commit. Use `git add -p` and commit only what belongs to the logical change.
- **Force-push accidents.** Rewriting a shared branch's history with `git push --force` and destroying teammates' work. Never force-push shared branches (step 8).
- **Dirty-tree drift.** Starting a new change while the tree still holds half-finished work — scope checks lie and changes tangle. Stash or commit first.
- **Wrong test target.** Running an unrelated suite (or one happy-path test) and calling it verification. Run the tests that cover the code you touched.

## VERIFICATION

Confirm the discipline was followed:

```bash
git status       # clean working tree, or only the intended change staged
git diff --stat  # fewer than 10 files for the current change
git diff         # empty — nothing unreviewed lurking unstaged
```

- **Scope:** `git diff --stat` shows fewer than 10 files and fewer than ~300 changed lines for the current change.
- **Tests:** the test command was actually executed and exited 0 — pytest/unittest output exists in the transcript, not just a claim.
- **Tree:** `git status` shows only the intended change (staged or stashed) — no leftover untracked or modified files.
- **History:** commits are one-logical-change each, and messages state the WHY.
