# sandbox-gate

Pre-execution sandbox for the `terminal` tool (Codex P2 discipline port):
high-risk commands are intercepted in `pre_tool_call` and vetoed **before**
they run, unless the command matches an allowlisted prefix or the gate is
paused (`/sandbox off`).

**What it does:** a pure, stdlib-only string classifier (never executes
anything) returns `allow | block | warn` — block verdicts are hard-vetoed,
warn verdicts escalate to the human approval gate, allow proceeds. Blocked
patterns: `rm -rf /`/`~`, `dd` to block devices, `mkfs`/disk format,
pipe-to-shell (`curl|sh`), `chmod 777` on system paths, shutdown/reboot,
fork bombs, raw-device writes. Warned: `git push --force`, `git reset
--hard` on shared branches, `curl -T` upload, netcat/scp exfiltration.

**Windows rule pack:** PowerShell/cmd destructive verbs are blocked —
`Remove-Item -Recurse`, `Clear-Content`, `Format-Volume`/`Format-Partition`,
`diskpart`, `reg delete`, `Set-ExecutionPolicy`, `cmd del /s`, `cmd rd /s`
(`rmdir`), `wmic ... delete`, `schtasks /delete`, `sc stop|delete`. Package
installs warn (human approval): `choco install -y`, `npm i -g`, `pip
install --user`. All patterns are case-insensitive; benign PowerShell
`Get-*`/`Format-Table` and query commands (`reg query`, `sc query`,
`schtasks /query`, `wmic ... get`) stay allowed.

**Commands:** `/sandbox [status|on|off|allow <prefix>|deny <prefix>|test <command>]`
(`test` dry-runs the classifier, never executes).

**Speed posture:** single `pre_tool_call` hook — pure regex, ~0 ms, zero
LLM/network/subprocess; non-terminal tools pass through untouched (no-op).

**Config:** plugin-local `state.json` (`enabled`, `allowlist`); corrupt or
missing state fails **closed** (gate stays on). Override path via
`SANDBOX_GATE_STATE` env var.

```bash
cd plugins/sandbox-gate && python -m unittest discover tests -q
```
