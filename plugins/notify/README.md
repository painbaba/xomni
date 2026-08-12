# notify — universal channel fan-out

Queues notification payloads for the host gateway channels (**telegram**,
**whatsapp**, **local**) and prints the exact host-gateway delivery command
that WOULD send each one. The plugin only ever *constructs* messages and
channel targets — actual delivery is the host gateway's job, and it only
happens when you explicitly pass `--send`.

## Safety contract

- **NEVER sends by default.** `/notify send` appends the payload to the
  outgoing queue and prints the would-run command. Nothing is transmitted.
- `--send` executes the host-gateway command (`hermes send --channel <ch>
  --to <target> --text <text>`; binary override via `NOTIFY_SENDER`).
- **Masked targets.** All human-readable output (`/notify status`,
  `/notify channels`, send reports) shows only `***last4` of a target. The
  literal delivery command carries the real target because that is the
  command the host would run — every report line around it is masked.

## Queue

Append-only JSONL at `~/.xomni-notify/queue.jsonl` (override
`XOMNI_NOTIFY_QUEUE`). One payload per line:

```json
{"id": "N...", "channel": "telegram", "target": "...", "text": "...", "ts": "..."}
```

Torn/corrupt lines are skipped on read and never raise. `count()` / `read()`
/ `clear()` never raise.

## Commands

```
/notify send <channel> <text> [--send]
/notify digest <channel> <title>|<item1>|<item2>... [--send]
/notify status
/notify channels
```

`/notify digest` builds `title (ts)` + numbered items and queues it as ONE
payload. Unknown channels fail loud with a `NotifyError` and leave the queue
untouched.

## Target resolution

`config notify.channels.<name>.target` > env (`NOTIFY_TELEGRAM_TARGET`,
`NOTIFY_WHATSAPP_TARGET`, `NOTIFY_LOCAL_TARGET`) > `local` (local channel
targets itself). A configured-but-unresolvable channel is loud; `local`
never needs configuration.

## Test

```
cd plugins/notify && python -m unittest tests.test_core -q
```

Zero hooks registered — zero per-turn cost.
