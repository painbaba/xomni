# Mozilla fxa audit dossier (mozilla_core_services) — first pass 2026-08

## Program split (important discovery)
Mozilla has TWO H1 programs:
- `/mozilla` — websites/services broadly (386 resolved, $50 min)
- `/mozilla_core_services` — the AUTH STACK: Firefox Accounts, Sync, etc.
  (separate handle; higher-value target class — account data, sessions).
  The `/mozilla` page links to it via "Gold Standard Safe Harbor" →
  hackerone.com/mozilla_core_services/safe_harbor. Always check for a
  sibling program handle when the main program page mentions a "core
  services" safe-harbor link — that's where the money surface is.

## Repo
`C:\Users\HP\mozilla-audit\fxa` (monorepo, ~257MB shallow depth 60).
Key packages: fxa-auth-server (the crown jewel — routes/, lib/oauth/,
lib/customs/), fxa-content-server, fxa-customs-server (rate limiting),
fxa-profile-server, fxa-admin-server, fxa-event-broker, libs/accounts/
passkey (shared passkey lib).

## First-pass results (all verified clean — do not re-walk)
- 9e877d1b "fix(oauth): purge v2 consent rows on delete" — COMPLETE:
  `_deleteAllAccountConsentsForUser` clears BOTH tables (v2 first, then
  v1) so reads can't answer "consent exists" for a deleted account;
  logging is bounded (missing-scope list capped 10×128 chars) and
  credential-safe (code/errno only, never driver connection options).
- a2e5baf2 "chore(deps): replace request with native fetch" — CLEAN:
  touched 123done (demo OAuth client), fxa-geodb maxmind-db-downloader
  (external download), test client. The migration ADDED a `!res.ok`
  status check (old code piped ANY response body including error pages
  into the geodb file). No redirect/proxy/TLS regression found.
- passkeys `/passkey/authentication/{start,finish}` — `auth: false` by
  design (public WebAuthn ceremony), but SOLID (see checklist below).
- OAuth surface: PKCE validators present (validators.js pkce* exports),
  refresh-token/consent handling mature. Sink scan of auth-server
  lib/routes: no exec/eval/unserialize (only regex `.exec()` and
  child_process in version.js — benign).

## WebAuthn / passkey auth audit checklist (transferable)
When auditing any passkey login flow, verify ALL of these (fxa passes all):
1. CHALLENGE: must be server-stored + SINGLE-USE (consumed on verify).
   Client-sent challenge string is only a LOOKUP KEY into the store;
   verification must use the STORED challenge, never the client value.
   fxa: `challengeManager.consumeAuthenticationChallenge(challenge)` —
   consumed, and `verifyWebauthnAuthenticationResponse` gets
   `storedChallenge.challenge`.
2. USER BINDING: credential ID → stored credential lookup determines the
   uid (correct WebAuthn — the passkey IS the credential); optional
   `expectedUid` param must reject on mismatch. fxa:
   `findPasskeyByCredentialId` + `uid !== expectedUid` → fail.
3. SIGN-COUNT: rollback detection (counter decrease = cloned authenticator)
   must reject or log. fxa: simplewebauthn "Response counter value" error
   caught + logged (passkey.signCount.rollback).
4. USER VERIFICATION: `userVerification: 'required'` in the ceremony +
   UV-required errors mapped to generic 401 (no credential-capability
   leak on sign-in).
5. POST-VERIFY: session created for the VERIFIED uid only; security events
   recorded on both failure and success.
Routes: `options.auth: false` on the ceremony endpoints is NORMAL (login
is public) — the authz is in the handler, not the route guard.

## Cron coverage
The nightly cron (edbb13a732d9, 1 AM IST, deliver local) now grinds
vercel + matomo + fxa: git fetch → audit NEW commits → reverse-audit
security fixes → routes-authz sweep (options.auth present on
account-data routes, uid bound to authenticated session) → append
findings. The fxa routes to watch: lib/routes/*.ts|js route configs
`options.auth`; handlers taking uid from payload/params must derive it
from the session.
