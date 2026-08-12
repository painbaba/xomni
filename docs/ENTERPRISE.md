# Enterprise tier: audit log + SSO-readiness

This document covers the two enterprise-facing capabilities of the XOMNI
platform:

1. **Tamper-evident audit trail** — the `audit-log` plugin
   (`plugins/audit-log/`), what it records, why it matters for compliance,
   and how to operate it.
2. **SSO-ready checklist** — a practical, verifiable path to OIDC/SAML single
   sign-on, session management, RBAC, secrets hygiene, and audit-readiness.

---

## 1. The audit log story

### 1.1 What it records

`audit-log` is an **append-only, tamper-evident audit trail** shipped as a
standalone zero-hook plugin. Every auditable action — login/logout, payment
capture, config change, payout trigger, deployment — is appended as one JSONL
record at `~/.xomni-audit/audit.jsonl` (override the location with the
`XOMNI_AUDIT_FILE` environment variable):

```json
{"id": "A177…-a1b2c3", "ts": "2026-08-12T17:20:00+00:00",
 "actor": "alice@corp.com", "action": "payment.capture", "target": "order-42",
 "result": "ok", "meta": {"amount": 100},
 "prev_hash": "9f2c…", "hash": "e7a1…"}
```

Fields:

| field | meaning |
|---|---|
| `id` | unique record id (`A<ts-ms>-<random>`), also the JSONL line |
| `ts` | UTC timestamp (ISO-8601, second precision) |
| `actor` | acting principal — **the SSO subject / role** (see §2.3 RBAC) |
| `action` | operation, e.g. `login`, `payment.capture`, `payout.trigger` |
| `target` | object acted upon, e.g. `order-42`, `config.yaml`, `session` |
| `result` | outcome (`ok` / `fail` / free text) |
| `meta` | optional structured detail (amount, idempotency key, …) |
| `prev_hash` | sha256 of the *previous* record |
| `hash` | sha256 of this record (minus its own `hash` field) + `prev_hash` |

### 1.2 Tamper-evident by hash chaining

Each record's `hash` is

```
hash = sha256( canonical_json(record minus its own "hash" field) + prev_hash )
```

Because every record's hash covers the previous record's hash, the ledger is
a **hash chain**: editing *any* field of *any* earlier record — or deleting a
line — invalidates that record's hash and breaks every subsequent
`prev_hash` link. Tampering is therefore always detectable, and the break is
reported at the *first* affected record.

The ledger is append-only by construction: records are only ever written
with `open(path, "a")` and the plugin exposes **no update or delete path**.
Writes are flushed and `fsync`'d before `append()` returns, so a crash cannot
silently drop a just-recorded entry (at worst a torn trailing line, which is
skipped and counted, never fatal).

### 1.3 Commands

```
/audit                last 25 entries (newest first)
/audit show <id>      full audit record
/audit verify         verify the hash chain -> {ok, first_bad_index}
```

### 1.4 Core API (`plugins/audit-log/core.py`, pure stdlib, zero hooks)

```python
from audit_log.core import AuditLog, AuditError

log = AuditLog()                      # ~/.xomni-audit/audit.jsonl by default
rec = log.append(actor, action, target, result=None, meta=None)   # -> record dict
log.query(actor=None, action=None, limit=50)                      # newest-first list
log.verify_chain()        # -> (ok, first_bad_index)  (True, None) when intact
log.corrupt_count()       # skipped corrupt/torn lines
log.count()               # total well-formed records
log.get(record_id)        # -> record dict; raises AuditError when missing
```

All read-only helpers never raise. Corrupt/torn JSONL lines are skipped and
counted via `corrupt_count()`; they never break the chain.

### 1.5 Operation & retention

- **Location:** `~/.xomni-audit/audit.jsonl` (per-user default),
  `XOMNI_AUDIT_FILE` override for central/enterprise deployment. The
  directory is created on first append.
- **Rotation:** the plugin itself is deliberately simple — rotate the file
  with the standard external mechanisms (logrotate / systemd timers /
  nightly job), then **preserve a copy of the rotated file**; verification
  against an archive is just `AuditLog(old_path).verify_chain()`.
- **Retention policy:** 12 months online + 7 years cold archive is a common
  enterprise/compliance baseline (PCI-DSS requires 12 months accessible + a
  minimum of 3 years of history; adjust to your obligations). Archive copies
  must be hash-chained too — keep them immutable (WORM storage or
  permission-locked directories).
- **Alerting:** run `/audit verify` (or `AuditLog().verify_chain()`) on a
  schedule; a `False` result means a record was edited, deleted, or
  malformed and must be treated as a security incident, not a data glitch.
- **Why it matters for compliance:** an audit trail that an attacker (or an
  insider with write access) can silently rewrite is worthless as evidence.
  The hash chain turns "we keep logs" into "we can *prove* our logs have not
  been altered since the moment they were written."

---

## 2. SSO-ready checklist

XOMNI is built to slot into an enterprise identity environment. Nothing below
requires changing core XOMNI code — every item is integration, configuration,
and verification. The `actor` field of the audit log (§1) is the seam where
identity and audit meet.

### 2.1 OIDC / SAML posture

- [ ] **Pick the protocol by user base:** OIDC (with PKCE) for interactive
      users, SAML 2.0 when the customer's identity provider (IdP) only speaks
      SAML. Support both behind one internal "identity" abstraction.
- [ ] **Never invent identity:** the IdP is the only source of truth. XOMNI
      must never issue its own long-lived credentials for human users.
- [ ] **Verify tokens properly:** validate signature (JWKS from the IdP's
      well-known discovery endpoint), `iss`, `aud`, `exp`, `nbf`, and `nonce`
      (OIDC) — cache the JWKS and refresh on rotation.
- [ ] **IdP discovery:** configure issuer URL, client id/secret, redirect
      URIs, and scopes (`openid profile email`, plus `groups`/roles claim for
      RBAC) in a config file or env vars — never in source.
- [ ] **PKCE for public clients** (CLI, embedded webview); confidential
      client flow (client secret) only for server-side integrations.
- [ ] **Test matrix per IdP:** Okta, Azure AD/Entra ID, Google Workspace,
      Keycloak (the OSS reference), and one SAML IdP. Verify login, logout,
      token refresh, and group-claim mapping on each.

### 2.2 Session management

- [ ] **Short-lived access tokens** (5–15 min) + refresh tokens; never
      accept an access token past `exp`.
- [ ] **Server-side session invalidation:** logout and admin "revoke user"
      must invalidate the session/refresh token at the IdP and locally.
- [ ] **Absolute + idle timeouts** enforced on every request (e.g. 12h
      absolute / 30min idle); re-auth prompt on expiry.
- [ ] **Secure storage:** httpOnly + Secure + SameSite cookies, or tokens in
      the OS keychain for CLIs; never in localStorage/logs.
- [ ] **Session fixation / rotation:** rotate session id on privilege change;
      bind sessions to a device/user-agent fingerprint.
- [ ] **Re-verification for sensitive actions** (payouts, key rotation,
      config changes): step-up auth (re-prompt or MFA) for admin-scoped
      actions, per §2.3.

### 2.3 RBAC mapping (the `actor` field)

- [ ] **Map IdP groups/roles → XOMNI roles** at login and on refresh
      (`admin`, `operator`, `readonly`, …). The mapped identity — subject,
      email, or `role@tenant` — is what goes into
      `AuditLog().append(actor, action, target, result, meta)`.
- [ ] **Enforce, don't just display:** every mutating path checks the role
      server-side; the audit record is written *after* the authorization
      decision so `result` reflects what actually happened.
- [ ] **Least privilege:** separate roles for read, operate, and administer;
      no shared/root accounts for humans.
- [ ] **Per-tenant scoping:** tenant id must ride along with the role claim
      so one deployment can serve multiple customers without cross-tenant
      access.
- [ ] **Verify with the audit log:** every SSO login/logout and every
      authorization decision is auditable — query by
      `log.query(actor=subject)` to prove *who did what*.

### 2.4 Secrets hygiene

- [ ] **Zero secrets in the repo:** no API keys, webhook secrets, JWKS
      private keys, or seed phrases in source, config-as-code, docs, or
      backups. See `docs/UPI.md` for the payment-side secret handling
      (webhook HMAC-SHA256 signature verification, idempotency) that this
      policy complements.
- [ ] **External secret store:** env vars at deploy time, a secrets manager
      (Vault / cloud KMS / secret manager), or a git-ignored `.env` for local
      dev — never committed.
- [ ] **Rotate on a schedule** (90 days) and immediately on suspected
      exposure; use per-environment secrets, never shared prod/dev values.
- [ ] **Audit the secrets, too:** log key rotation and credential issuance as
      audit records (`action="secret.rotate"`, `actor=<admin>`), so key
      lifecycle is provable.

### 2.5 Audit-readiness

- [ ] **Every sensitive action lands in the audit log** — login/logout,
      role changes, payment capture, payout triggers, config/deploy changes,
      key rotation — with the SSO identity in `actor`.
- [ ] **Automated chain verification** runs on a schedule (cron/CI) and pages
      on `verify_chain() == (False, i)` — see §1.5.
- [ ] **Immutable storage** for the ledger (permission-locked dir, WORM
      bucket, or nightly copy to read-only archive).
- [ ] **Retention and export** documented and tested: 12 months hot + 3–7
      years cold archive, with a tested restore/export path for auditors.
- [ ] **Playbook:** a written incident response step for a broken chain
      ("who accessed the ledger host, which record changed, preserve the
      forensic copy before any fix").
- [ ] **DRY run once per quarter:** append → archive → tamper a copy → run
      `verify_chain()` → confirm the break is reported with the correct
      `first_bad_index`.

---

*Companion docs: `docs/UPI.md` (payment secrets + webhook HMAC),
`plugins/audit-log/README.md` (plugin usage), `plugins/audit-log/core.py`
(reference implementation).*
