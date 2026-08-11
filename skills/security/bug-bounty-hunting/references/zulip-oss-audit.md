# Zulip OSS Audit Dossier (measured 2026-08)

Program: HackerOne /zulip (open source, Python/Django). Repo clone:
`C:\Users\HP\zulip-audit\zulip` (shallow `--depth 60`, 2016 Python files).

## The finding that wasn't — optimization-commit regression (the lesson)

Commit chain (all in `zerver/lib/users.py` + `zerver/actions/message_send.py`):

- `38e356174e` (Jul 27, author **Bedo Khaled**): "message_send: Optimize
  computing inaccessible users" — refactored `get_inaccessible_user_ids`
  into a shared `get_inaccessible_users_queryset` helper and REMOVED the
  `is_user_active=True` filter "to make it generic". Result: limited
  guests could access DEACTIVATED users they shared stream subscriptions
  with — on Zulip Cloud for ~10 days.
- `2bf3bd2` (Aug 6): "users: Add missing is_user_active=True filter" —
  re-added the filter. Commit message states the design intent: "we
  treat all deactivated users as inaccessible".

**Why not reportable**: already fixed by the team. Found-and-fixed
regressions are only worth reporting if they landed in a shipped release
BEFORE the fix — here the window (Jul 27 → Aug 6) was Cloud-internal and
now closed. Document + move on.

**Durable outputs**:
1. The CLASS: "optimization/refactor" commits touching access-control
   code are first-class reverse-audit targets — not just
   "fix/security" commits. Grep `git log --oneline` for
   `optimize|refactor|chore` touching authz files.
2. The SIBLING-HELPER HUNT: after a filter was dropped in one helper,
   check EVERY access function in the same module before concluding.
   Verified on Zulip: `check_can_access_user` (zerver/lib/users.py:746)
   had `is_user_active=True` PRE-EXISTING in its final subscription
   query (line 778) — the regression only hit
   `get_inaccessible_users_queryset`. Read the full logic incl. the
   early returns: `user_access_restricted_in_realm` returns False for
   bots and for all-users-accessible realms; `check_user_can_access_all_users`
   returns True for non-guests and spectators. A deactivated human
   target in a restricted realm reaches the final filtered query →
   inaccessible → correct.
3. The AUTHOR PATTERN: the same author's optimization cluster that week
   (38e3561 inaccessible-users, 4e832aa check_can_access_user, 1338aa9
   user-creation events — all "Fixes: #27835" from the same perf ticket).
   One of them broke security. Feed the author name into the nightly
   cron watch-list: any future commit by that author on access-control
   files gets the full regression-hunt treatment.
4. EVENT-OPTIMIZATION ≠ FINDING: `1338aa9` skips user-creation EVENT
   notifications when a common huddle exists — events are notifications,
   not access grants; missing events = no leak (UX bug at worst). Don't
   chase it.

## Webhook auth (validated safe)

All Zulip webhooks (incl. the new intercom admin handler, 9b302b8) go
through `@webhook_view` (zerver/decorator.py:371) which requires a valid
bot API key (`validate_api_key(..., allow_webhook_access=True)` in the
URL `api_key` param). No per-webhook signature code needed — the key IS
the auth. Don't flag "no hmac verification" on Zulip webhooks.

## Cron coverage

`oss-nightly-audit` (job edbb13a732d9, 1 AM IST) PART 4 = zulip:
watch Bedo Khaled's commits on zerver/lib/users.py + message_send;
re-scan the three access helpers for missing is_user_active/is_active
filters; audit fresh commits generally.
