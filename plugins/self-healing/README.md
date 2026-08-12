# self-healing (U9) — watchdog · postconditions · config-drift auto-fix

A self-healing agent that watches its own cron/scripts and Hermes config, detects
**silent failures that produce no error output** (the `pip install vectorbt`
hanging 180 s case), and fixes config drift automatically — every automatic
action traceable in an audit trail. **Zero hooks** — `/heal` is invoked on
demand (or by cron); nothing is wired to agent events.

## What it does

| Piece | Behavior |
|---|---|
| `run_with_watchdog(cmd, timeout, quiet_after_s)` | Runs a subprocess; kills it if it exceeds `timeout` **or** stays alive with **no output** for `quiet_after_s` (alive + silent = hang). Returns `{ok, timed_out, killed, exit_code, tail, output, elapsed, error}`. Tracks output as bytes, so `\r` progress bars don't false-trigger. Kills the whole tree (`taskkill /T /F` on Windows). |
| `verify_postconditions(cmd_result, expected)` | Checks `file_exists` / `output_contains` / `service_ping` after a run. Catches **exit-0-but-nothing-happened**: install printed success but the binary is missing → `ok=False` with the failing check flagged. |
| `drift_scan(expected_state)` | Compares expected (plugins roster from `xomni_cli.PLUGIN_TESTS`, provider block, canonical `.env` KEY names) vs actual (`config.yaml`, `.env` KEY presence, hermes `plugins/`). Returns `[{key, kind, expected, actual}]`. |
| `fix_drift(drift)` | Restores a missing plugin dir (copytree from repo `plugins/`), re-inserts the provider block (config backed up first), re-adds a missing `.env` **KEY placeholder** (`KEY=`) — **never reads or logs secret values, only KEY presence**. |
| Audit trail | Every watchdog kill, postcondition failure flag, and fix appends `{ts, detector, subject, action, before, after}` to `~/.xomni-heal/heal.jsonl`. |

## Commands (registered by `register(ctx)` — command only, no hooks)

```
/heal scan               run watchdog + postcondition checks (data/heal/checks.json)
                         + drift scan; report everything found
/heal fix <id>           fix one drift, e.g. plugins.omni-registry,
                         provider.block.opencode-go, env.ANTHROPIC_API_KEY
/heal fix all            fix every current drift
/heal status             last 10 audit entries from ~/.xomni-heal/heal.jsonl
```

## Default checks (`data/heal/checks.json`)

* `demo-silent-sleep` — `python -c "import time; time.sleep(300)"` with
  `quiet_after_s: 3` → the watchdog kills it in ~3 s. Proves the kill every scan.
* `vectorbt-install-hang` — the real-world case from the brief, **disabled by
  default** (it's a network install); flip `"enabled": true` to arm it.
* `xomni-cli-present` — postcondition: exit-0 run + `file_exists` on the xomni
  CLI, so a "success" that didn't produce the CLI is flagged.

## Tests

```
cd plugins/self-healing && python -m unittest tests.test_core -q
```

20 tests, all hermetic (env-overridable `XOMNI_HEAL_DIR` / `XOMNI_HERMES_HOME` /
`XOMNI_ROOT` / `XOMNI_CHECKS` — nothing touches the real config, `.env`, or
`heal.jsonl`): watchdog kills silent hangs + audits the kill, timeout respected
even when output flows, quiet detector disabled at 0, output resets the quiet
timer, missing command handled; postconditions pass/fail incl. the
exit-0-nothing-happened flag and service pings; drift detected for missing
plugin dir / provider block / env key and clean state; fixes restore plugin
dirs (audit shape complete), add env KEY placeholders with **secrets never
logged**, re-insert provider blocks with config backup; `/heal scan|fix|status`
end-to-end.

Env overrides (all optional): `XOMNI_HEAL_DIR`, `XOMNI_HERMES_HOME`,
`XOMNI_ROOT`, `XOMNI_CHECKS`.
