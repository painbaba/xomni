# Security Policy

XOMNI is an MIT-licensed open-source agent product. We take security
seriously — including the security of the third-party content the project
scans and ships. This page describes how to report vulnerabilities and the
project's security posture.

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Please report privately through one of:

1. **GitHub private vulnerability reporting (preferred):**
   <https://github.com/painbaba/xomni/security/advisories/new>
2. **Email:** <!-- SECURITY-EMAIL-PLACEHOLDER: insert maintainer security contact, e.g. security@example.com -->

When reporting, include:

- Affected component (plugin name, `data/build_db.py`, website, etc.) and
  version/commit.
- Steps to reproduce, including any payloads.
- Impact and any proof-of-concept.
- Your suggested fix, if you have one.

You will receive an acknowledgement within **48 hours** of a complete report.

## Response times

| Stage | Target |
|---|---|
| Acknowledgement | 48 hours |
| Initial triage / severity assessment | 5 business days |
| Fix or mitigation plan (confirmed issues) | 30 days from triage |
| Coordinated disclosure | 90 days from triage, unless negotiated |

We follow coordinated disclosure: we will not disclose your report before a
fix is available unless you agree otherwise.

## Scope

In scope: the XOMNI codebase in this repository, its 16 plugins, the
`data/build_db.py` pipeline and its outputs, and the flagship website.

Out of scope: third-party skills, models, and APIs referenced by XOMNI
(including the opencode Zen vision gateway and harvested external skills) —
report issues with those to their respective owners.

## Fail-closed security-scan posture (`data/build_db.py`)

`data/build_db.py` harvests external `SKILL.md` content and must never ship
dangerous material. It is **fail-closed**:

- Every harvested skill is scanned statically and assigned exactly one
  verdict: **PASS**, **REVIEW**, or **REJECT** (enforced by a SQL `CHECK`
  constraint on `scan_verdict` in `data/skills.db`).
- **REJECT** findings (dangerous content) are never importable: they are kept
  in the database only as an immutable audit trail and are explicitly marked
  "do not import".
- **REVIEW** findings are flagged for human review before any use.
- Content is recorded with its `sha256` hash for integrity/auditability.
- The scan regenerates `docs/SKILLS-SECURITY.md`, a public report of verdicts
  and findings, on every run.

Any change that weakens these guarantees (e.g. defaulting unknown verdicts to
PASS, or making REJECT content importable) is a security regression and will
not be merged.

## Secrets handling

- Never commit secrets: API keys, tokens, `.env` files, or private paths.
- XOMNI reads keys from `~/AppData/Local/hermes/.env` (e.g.
  `OPENCODE_GO_API_KEY`) at runtime — never from the repo.
- `.gitignore` covers local state; if you accidentally commit a secret,
  rotate it immediately and report it per the process above.
- Contributors must keep secrets out of logs, test fixtures, and issue/PR
  descriptions.
