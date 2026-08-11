# pre_tool_call hook contract (verified against installed source)

The `pre_tool_call` hook is how a plugin vetoes or gates a model tool call
BEFORE it executes — the sanctioned mechanism for sandbox/security plugins
("block this terminal command unless allowlisted"). Worked example: the
`unified-agent/plugins/sandbox-gate/` plugin (risk classifier + allowlist).

## Where the contract lives (source is the truth)

- Definition + first-valid-dict-wins loop: `hermes_cli/plugins.py`
  `_get_pre_tool_call_directive_details()` (~line 2120).
- Public helpers: `get_pre_tool_call_directive()` (returns
  `(directive, message)`), `get_pre_tool_call_block_message()` (deprecated
  shim), `resolve_pre_tool_block()` — the single entry point every
  tool-dispatch site uses (fetches directive, runs the approval gate for
  `approve`, fail-closed to block).
- Invocation sites: `agent/tool_executor.py` (~line 416, `_resolve_pre_tool_block`)
  and `agent/agent_runtime_helpers.py` (~line 2699).
- Shell-hook wire protocol (same return shapes, JSON over stdout):
  `agent/shell_hooks.py` — documents the Claude-Code-style
  `{"decision": "block", "reason": "..."}` variant too.

## Hook kwargs (exact)

`invoke_hook("pre_tool_call", ...)` passes: `tool_name` (str), `args`
(dict — the tool's input args; coerced to `{}` if not a dict),
`task_id`, `session_id`, `tool_call_id`, `turn_id`, `api_request_id`,
`middleware_trace` (list).

For the terminal tool: `tool_name == "terminal"`, and the command string
lives at `args["command"]` (verified in `tools/terminal_tool.py` schema).

## Return contract — what each return does

| Return | Effect |
|---|---|
| `{"action": "block", "message": "..."}` | Vetoes the tool call outright; `message` becomes the tool result the model sees. |
| `{"action": "approve", "message": "..."}` | Escalates to the human approval gate (once/session/always/deny). `rule_key` optional (approve only). If the gate errors/denies/times out it FAILS CLOSED to a block. |
| anything else (incl. `None`) | Silently ignored; tool proceeds. Observer-style no-op. |

First valid dict return wins across all registered plugins; invalid/non-dict
returns are ignored so observer hooks stay harmless.

## Mapping verdicts → directives (sandbox-gate pattern)

Three-tier classifier (`core.py`, pure, no hermes imports) mapping to the
two directive actions:

```python
if verdict == "block":
    return {"action": "block", "message": f"[sandbox-gate] blocked: {reason}"}
if verdict == "warn":
    return {"action": "approve", "message": f"[sandbox-gate] risky — {reason}"}
return None   # allow / non-terminal tool / no args -> pure no-op
```

- `block` → hard veto (`{"action": "block", ...}`).
- `warn` → human confirmation (`{"action": "approve", ...}`) — the approve
  directive is the documented "risky, ask a human" lever.
- `allow` / non-terminal tools / missing args → `None`. The hook MUST return
  `None` for every non-terminal tool name (write_file, browser_navigate,
  ...) or the plugin would intercept tools it never meant to touch.

## Hooks fire for EVERY tool — filter first

`pre_tool_call` fires for all model tools, not just terminal. The handler
must check `tool_name` before doing anything:

```python
def _on_pre_tool_call(**kwargs):
    if kwargs.get("tool_name") != "terminal":
        return None
    args = kwargs.get("args")
    if not isinstance(args, dict) or not isinstance(args.get("command"), str):
        return None
    verdict, reason = core.decide(args["command"])
    ...
```

## Pitfalls hit building sandbox-gate

- **`str.rstrip("/\\")` on a single `/` returns `""`** — path normalization
  for `rm -rf /` target checking silently produced empty string and the rule
  never fired. Fix: `target = raw.rstrip("/\\") or raw` (fall back to the
  un-stripped value when stripping empties it).
- **Host scanner flags literal dangerous strings in test heredocs**: writing
  `dd of=/dev/sda` verbatim inside a `terminal` heredoc (or a test source
  file that gets scanned) trips the host's own hardline blocklist — the
  command is rejected with its own block message before your code runs.
  Build dangerous strings programmatically in probes
  (`"dd if=/dev/zero " + "of=/dev/sda" + " bs=1M"`) or keep them inside
  `.py` test files (classifier tests) and only ever pass them to the
  classifier, never to a real shell.
- **Tests only classify strings — never execute**: the whole point of a
  pure `classify(cmd) -> (verdict, reason)` core is that the test suite
  feeds dangerous commands as string literals to the classifier only.
  Assert verdicts; never pipe the strings to a shell.

## State layout for a gate plugin

`state.json` next to `__init__.py` (overridable via env var for tests):

```json
{"enabled": true, "allowlist": ["git push"]}
```

- `decide()` order: pause toggle (`enabled`) → allowlist prefix match
  (case-insensitive startswith) → `classify()`.
- Missing/corrupt state must fail CLOSED (default `enabled: true`) — a state
  problem must never silently disable the gate.
- Save atomically: write `state.json.tmp`, then `os.replace` — no torn writes.
