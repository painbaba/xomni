# Bounty report template — fill every section, one issue per report

## Title
[Asset] [Vulnerability type] — [one-line business impact]
Example: supplier.meesho.com IDOR — supplier A can read supplier B's payout documents

## Summary
2-3 sentences: what, where, why it matters (business impact, not CVSS text).

## Affected asset(s)
Exact in-scope URL(s)/app(s) from the program scope table.

## Steps to reproduce
1. (exact request with ALL headers the program requires, e.g. X-Hackerone)
2. (exact request/action)
3. (observation — what the response shows)
4. (impact proof — data shown, action possible)

Include screenshots or a short video of each key step. No redacted claims —
show, don't tell.

## Impact
What an attacker can actually do:
- Data: what PII/financial/other data exposed, volume
- Actions: what the attacker can perform (transfer, delete, impersonate)
- Reach: single user vs all users vs admin

## Remediation suggestion
1-3 concrete fixes (server-side authorization check, ownership validation,
OTP binding, etc.). Doesn't need to be perfect — shows good faith.

## Checklist before submitting
- [ ] Only in-scope asset, vulnerability class not in the Out-of-Scope list
- [ ] Not in the program's Known Issues (duplicates) list
- [ ] Required headers (X-Hackerone etc.) present in the repro
- [ ] Used only provided/test accounts
- [ ] No real user data accessed or stored; nothing destructive performed
- [ ] Single issue per report
