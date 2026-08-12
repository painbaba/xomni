# receipts

Receipts-by-default: every external side-effect (file write, HTTP POST,
deploy) automatically returns a **verifiable handle** — so "it works" is
always backed by proof, never claims.

**Ledger:** append-only JSONL at `~/.xomni-receipts/receipts.jsonl`
(override with `XOMNI_RECEIPTS_FILE`). One line per receipt:

```json
{"id": "R…", "ts": "…", "action": "skill.install", "target": "…/SKILL.md",
 "result": "PASS hello-skill", "handle": "sha256:…", "meta": {"skill": "hello-skill"}}
```

**Verifiable handles** (the `handle` field is what `verify` re-checks):

| kind | handle format | verify re-checks |
|---|---|---|
| file write | `sha256:<hex>` | file exists + sha256 matches |
| URL returned | `url:<url>` | live GET returns HTTP 200 |
| command run | `exit:<code>:<tail>` | recorded exit code + output tail (re-runs the recorded `meta['command']` when rechecking) |

**Commands** (zero hooks):

```
/receipts                last 10 receipts (newest first)
/receipts show <id>      full receipt record
/receipts verify <id>    re-check the handle -> {ok, evidence}
/receipts audit          mutating-path coverage report (grep-based, gaps loud)
```

**Integrated mutating paths** (each issues a receipt by default; the
receipts plugin is optional at every site — if it is unavailable the path
behaves exactly as before):

- skill install: `/skills-install`, `/skills-marketplace`, `skills_import`
  (omni-skills) and `xomni skill install`
- skill publish: `/skills publish` (omni-skills — sha256 of the stamped /
  published SKILL.md)
- skill save/sync: `/skill save`, `/skill from-session`, `/skill sync`
  (skill-drafter — sha256 of the written/copied SKILL.md)
- MCP: `/mcp add <path>` (catalog import) and `/mcp add <name> --yes`
  (server install into host config.yaml)
- CLI: `xomni plugins install`, `xomni add <stack>` (config.yaml append),
  `xomni providers add` (config.yaml + .env placeholder)
- state: `/statusline on|off` (state.json toggle)

`/receipts audit` verifies this list against the source: every mutating
command's handler is grepped for a receipt-issuing call, and any handler
that writes files without one is flagged loudly (missing-path detection).

**Core API** (`plugins/receipts/core.py`, pure stdlib):

```python
from receipts.core import ReceiptLedger, try_file_receipt, try_url_receipt, try_exit_receipt

rec = ReceiptLedger().issue("skill.install", dest, "PASS demo", handle, {"skill": "demo"})
print(ReceiptLedger().verify(rec["id"]))   # -> {'ok': True, 'evidence': {...}}
```

**Run the suite:**

```bash
cd plugins/receipts && python -m unittest tests.test_core -q
```
