# capability-probe

Live-probe ANY provider's `/models` endpoint into the omni-registry
`capabilities.json` — models are **discovered live, never hardcoded**.

## Commands

- `/probe <provider-id>` — GET `{base_url}/models` with the provider key, merge
  the result into the registry with `source='live-probe'`, and show the count +
  diff vs the registry (added / removed / changed). Provider ids resolve from
  the `xomni_cli` PROVIDERS table (display name, env var, or base_url).
- `/probe all` — probe every provider in the table whose key is present in the
  environment (env var first, then `~/AppData/Local/hermes/.env`); keyless
  providers are skipped.

## Behavior contract

- **Both /models shapes parsed**: OpenAI-compatible `{"data": [{"id", ...}]}`
  (bare list tolerated; optional metadata like `context_length`/`vision`/
  `reasoning` extracted, `"128k"`-style strings coerced) and Anthropic
  `{"data": [{"id", "display_name", ...}]}`.
- **Loud failures** (`ProbeError`, names the fix): missing key → env var + .env
  path; 401/403 → key rejected; non-200 → endpoint shape; non-JSON → not a
  /models endpoint; network/timeout → connectivity.
- **Key never printed**: the key only ever goes in the auth header; it never
  appears in output, exceptions, or returned data (tested).
- **Registry merge** (`source='live-probe'` distinct from `'spec'`): existing
  records get a record-level `source='live-probe'` marker + a `live_probe`
  audit block; capability envelopes (context/capabilities/cost) are never
  overwritten (F3: report, don't auto-accept). New ids are appended as
  `status='unverified'` records (listed live, never call-verified — NIM-style
  catalog traps). Tombstones are never touched (KLIP-6). One
  `capability-probe:<provider>` entry is appended to `data['sources']`.
- **Zero hooks**, zero Hermes imports, pure stdlib. The network call is
  injectable (`urlopen=`) so tests need no monkeypatching.

## Tests

```
cd plugins/capability-probe && python -m unittest tests.test_core -q
```

18 methods: OpenAI/Anthropic parsing, metadata extraction, every loud-failure
path, key-hygiene assertions, diff semantics, registry merge (tags, envelopes
preserved, new unverified records, tombstone freeze), `/probe` + `/probe all`
rendering, and the zero-hooks register() check.
