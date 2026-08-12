"""notify — universal channel fan-out (telegram / whatsapp / local).

Builds notification payloads, appends them to the outgoing JSONL queue at
``~/.xomni-notify/queue.jsonl`` (override ``XOMNI_NOTIFY_QUEUE``), and prints
the exact host-gateway command that WOULD deliver each one. The plugin NEVER
sends by default — only ``--send`` runs the host gateway command.

Commands:
  /notify send <channel> <text> [--send]
      queue one payload + print the would-run delivery command; with
      ``--send`` the host gateway command is actually executed.
  /notify digest <channel> <title>|<item1>|<item2>... [--send]
      build a batched digest body (title + numbered items + ts) and queue it
      as a single payload.
  /notify status
      queue length + channels configured (targets masked).
  /notify channels
      channel -> masked target resolution table.

Targets come from config ``notify.channels.<name>.target`` or env
``NOTIFY_TELEGRAM_TARGET`` / ``NOTIFY_WHATSAPP_TARGET`` / ``NOTIFY_LOCAL_TARGET``.
Full targets are never printed — all output is masked.

Zero hooks registered — zero per-turn cost.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/notify send <channel> <text> [--send]        queue one payload (+print would-run cmd)\n"
    "/notify digest <channel> <title>|<i1>|<i2>... [--send]   queue a batched digest\n"
    "/notify status                                 queue length + configured channels\n"
    "/notify channels                               channel -> masked target table\n"
)


def _split_send_args(rest: str):
    """(channel, text, run) from '/notify send <channel> <text> [--send]'."""
    parts = (rest or "").strip().split(None, 1)
    if not parts:
        return None
    channel = parts[0].lower()
    text = parts[1].strip() if len(parts) > 1 else ""
    run = False
    if text.endswith("--send"):
        text = text[:-len("--send")].rstrip()
        run = True
    return channel, text, run


def _handle_notify(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    def config_get(name):
        cfg = getattr(_CTX, "config", None)
        getter = getattr(cfg, "get", None)
        if callable(getter):
            try:
                return getter(name)
            except Exception:
                return None
        return None

    if not cmd:
        return HELP
    if cmd == "send":
        parsed = _split_send_args(rest)
        if not parsed or not parsed[1]:
            return "usage: /notify send <channel> <text> [--send]\n" + HELP
        channel, text, run = parsed
        try:
            result = core.send(channel, text, config_get=config_get, run=run)
        except core.NotifyError as exc:
            return "/notify send: %s" % exc
        return core.send_report(result)
    if cmd == "digest":
        parsed = _split_send_args(rest)
        if not parsed or not parsed[1]:
            return ("usage: /notify digest <channel> <title>|<item1>|<item2>... "
                    "[--send]\n" + HELP)
        channel, body, run = parsed
        chunks = [c.strip() for c in body.split("|") if c.strip()]
        if len(chunks) < 2:
            return ("usage: /notify digest <channel> <title>|<item1>|<item2>... "
                    "[--send]  (need a title and at least one item)\n" + HELP)
        title, items = chunks[0], chunks[1:]
        text = core.digest(items, title)
        try:
            result = core.send(channel, text, config_get=config_get, run=run)
        except core.NotifyError as exc:
            return "/notify digest: %s" % exc
        return core.send_report(result)
    if cmd == "status":
        return core.status_text(core.NotifyQueue(), config_get)
    if cmd == "channels":
        return core.channels_table(config_get)
    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "notify",
        handler=_handle_notify,
        description=(
            "Universal channel fan-out (telegram/whatsapp/local): queues "
            "notification payloads to ~/.xomni-notify/queue.jsonl and prints "
            "the exact host-gateway command that WOULD send them. NEVER sends "
            "by default — only --send runs the command. Commands: /notify "
            "send <channel> <text> [--send], /notify digest <channel> "
            "<title>|<i1>|<i2>... [--send], /notify status, /notify channels "
            "(masked targets only)."
        ),
        args_hint="send|digest|status|channels",
    )
