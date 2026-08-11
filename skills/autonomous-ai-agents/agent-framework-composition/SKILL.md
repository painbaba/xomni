---
name: agent-framework-composition
description: When asked to merge coding agents or build a tool prototype.
---

# Agent Framework Composition

How to handle requests like "take the full git source of Hermes + OpenCode + X + Y
and combine them into one best-ever agent" or "if you're not impressed with model
Z, deep-research and build the best prototype". These arrive frequently from this
user (AI-business context). The class: **verify the idea, then compose — never
literally merge.**

## Core principles

1. **Verify before building or pushing back.** 1-2 tool calls settle whether a
   named tool/repo/site is real, its language, stars, license, and size. Use the
   GitHub API:
   ```bash
   curl -s https://api.github.com/repos/<org>/<repo> | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('full_name'), d.get('language'), d.get('stargazers_count'), (d.get('license') or {}).get('spdx_id'), d.get('size'))"
   ```
   - "Moved Permanently" = renamed repo: follow `curl -sI ... | grep -i ^location`.
   - `size` is KB → /1024 for MB; use it to decide shallow-clone vs analyze-only.
   - Check the user's OWN machine first: the host framework may already be a full
     git checkout locally (e.g. Hermes at `~/AppData/Local/hermes/hermes-agent`).
2. **Compose, don't merge.** A literal merge of N codebases in different languages
   (Python + Go + Rust) is a broken monolith, not an agent. Pick ONE host (the
   richest framework — for this user that is Hermes: skills/memory/cron/plugins/
   gateway) and land every other tool's signature strength as an **edge module**
   (plugin, tool, or skill). Host AGENTS.md usually states this itself ("the core
   is a narrow waist; capability lives at the edges") — quote it when the user
   pushes for a literal merge.
3. **License check up front.** All-permissive (MIT/Apache-2.0) = combinable with
   attribution; write a LICENSE-ATTRIBUTION.md. PolyForm/other = concept-only
   reimplementation, never vendored code.

## Steps

1. **Inventory + verify** every named source via GitHub API (batch the curls).
   Resolve redirects; record language/stars/license/size. Also identify unknowns
   (e.g. an unfamiliar tool name) with `api.github.com/search/repositories?q=...`.
2. **Pick the host + write the gap matrix**: per tool, strength → which gap it
   fills → SHIPPED (code) vs port-plan (deferred). This matrix is the heart of
   the honest answer.
3. **Build edge modules as host plugins** with the split-core pattern: `core.py`
   (pure stdlib, zero host imports — fully unit-testable in isolation) +
   `__init__.py` (host wiring: hooks/commands/tools). Never touch host core.
4. **Port at least one signature feature as real code** (proves the pattern,
   e.g. aider-style repo map: symbol regex extraction, skip-dirs, size cap).
5. **Tests**: pure-logic unit tests on core.py; then INSTALL + ENABLE +
   verify discovery (see Pitfalls for the correct API) + one real e2e
   (`hermes chat -q "..."` then read the module's state file to prove hooks
   fired). Live proof beats claims.
6. **Docs**: README (story + matrix), docs/ARCHITECTURE, docs/GAP-ANALYSIS,
   docs/PORT-PLAN (ranked P1-P5 with effort), LICENSE-ATTRIBUTION.
7. **Vendor small references only**: a 1-3MB repo clone as `vendor/<name>` is a
   nice attribution gesture; multi-hundred-MB clones are waste — skip them and
   give the clone commands in the docs.

## Pitfalls

- **Shared-mutable-default bug (Python)**: `state = dict(DEFAULT_STATE)` is a
  SHALLOW copy — nested dicts/lists are shared across all instances. Symptom:
  a test passes alone but fails in the full suite (test-order-dependent), or a
  fresh instance inherits another instance's data. Fix: `copy.deepcopy` the
  defaults in `__init__`/`default_factory`. Watch it in ANY module that keeps a
  state ledger — it silently corrupts real sessions too, not just tests.
- **Host plugin-discovery API drifts**: don't trust attribute names from older
  docs (`_plugin_commands`, `enabled_plugins` may not exist). The working check:
  ```python
  from hermes_cli.plugins import _ensure_plugins_discovered
  d = _ensure_plugins_discovered()
  for p in d.list_plugins():        # returns LIST OF DICTS
      if 'myname' in str(p): print(p['name'], p['source'], p['enabled'], p['commands'], p['hooks'], p['error'])
  ```
  Filter on `str(p)`, not dict-key membership.
- **MSYS path traps on Windows** (repeat offender): native Windows binaries AND
  native python cannot read `/c/...` git-bash paths — `py_compile`/`os.path.isdir`
  fail on them; use `C:/...` form. Destructive `rm -rf` on MSYS paths can resolve
  unexpectedly (deleted a whole `vendor/` dir this session) — use native paths
  for anything destructive.
- **Research sources are often JS-walled**: benchmark pages return empty bodies
  to curl. Use order-of-magnitude industry ranges from domain knowledge,
  LABEL them as such in the code/docs ("benchmark ranges, real prices from the
  network"), and move on — don't burn turns on scraping walls.
- **Test-order-dependent failures = shared state, not flaky tests.** Bisect by
  running test-alone vs pairs vs full suite to identify the polluter, then look
  for module-level mutable defaults.

## Verification

- All test suites green (`python -m unittest tests.test_core -v` per module).
- `hermes plugins list` / discovery shows each plugin enabled with zero errors.
- One real `hermes chat -q` session increments the module's state counters
  (hooks actually fired) and writes its output files.
- The final report maps: which tool filled which gap (code vs deferred), how the
  module works end-to-end, and honest caveats (demo mode, verification limits).

## References

- `references/revenue-model-design.md` — WaitPerk-model critique and the
  PerkLine v2 upgrade (tiered cpm/cpc/cpa pricing, relevance matching, signed
  receipts, escrow caps, second-price auction) — reusable for any monetization-
  module work.
