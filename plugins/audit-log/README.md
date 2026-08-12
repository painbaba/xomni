# audit-log

Enterprise tamper-evident audit trail. Every auditable action is appended to
a **hash-chained** JSONL ledger: each record's sha256 covers the previous
record's hash, so editing *or deleting* any earlier record breaks every later
hash — tampering is always detectable.

**Ledger:** append-only JSONL at `~/.xomni-audit/audit.jsonl` (override with
`XOMNI_AUDIT_FILE`). One line per record:

```json
{"id": "A…", "ts": "…", "actor": "alice@corp.com", "action": "payment.capture",
 "target": "order-42", "result": "ok", "meta": {"amount": 100},
 "prev_hash": "sha256-of-previous-record…", "hash": "sha256-of-this-record…"}
```

`hash = sha256(canonical JSON of the record minus its own hash + prev_hash)`.
The ledger is append-only by construction — records are only ever written
with `open(path, "a")` and there is no update/delete path in the plugin.

**Commands** (zero hooks):

```
/audit                last 25 entries (newest first)
/audit show <id>      full audit record
/audit verify         verify the hash chain -> {ok, first_bad_index}
```

Corrupt/torn JSONL lines are skipped, never fatal — `corrupt_count()` reports
them, and a torn append never breaks the chain.

**Core API** (`plugins/audit-log/core.py`, pure stdlib):

```python
from audit_log.core import AuditLog

log = AuditLog()  # or AuditLog("/custom/path/audit.jsonl")
rec = log.append("alice@corp.com", "payment.capture", "order-42", "ok",
                 {"amount": 100})
print(log.query(actor="alice@corp.com", limit=50))   # newest-first list
print(log.verify_chain())                            # -> (True, None) or (False, first_bad_index)
print(log.corrupt_count())                           # skipped corrupt lines
```

All read-only helpers never raise; writes are fsync'd before returning.

**Run the suite:**

```bash
cd plugins/audit-log && python -m unittest tests.test_core -q
```
