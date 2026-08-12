"""notify core — universal channel fan-out (pure stdlib, zero hooks).

Builds notification payloads for the host gateway channels (``telegram``,
``whatsapp``, ``local``), persists them to an outgoing JSONL queue at
``~/.xomni-notify/queue.jsonl`` (override ``XOMNI_NOTIFY_QUEUE``), and prints
the exact host-gateway delivery command that WOULD send each payload.

SAFETY CONTRACT — NEVER SENDS BY DEFAULT:

* ``send()`` with ``run=False`` (the default) only appends the payload to the
  queue and returns the would-run command. Nothing is ever transmitted.
* ``send(..., run=True)`` executes the delivery command through the host
  gateway (``hermes send --channel <ch> --to <target> --text <text>``); the
  runner is injectable so tests can mock it.
* Targets are resolved from config (``notify.channels.<name>.target``) or env
  (``NOTIFY_TELEGRAM_TARGET`` / ``NOTIFY_WHATSAPP_TARGET``) and are ALWAYS
  masked in human-readable output (``mask_target`` keeps only the last 4
  chars). The literal delivery command necessarily carries the real target —
  that is the command the host would run — but every report/table/status line
  shows the masked form only.

``digest(items, title)`` builds a batched notification body (title + numbered
items + ts) ready to be queued as one payload.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone

CHANNELS = ("telegram", "whatsapp", "local")

# env var per channel for the target; "local" targets the local terminal
ENV_TARGETS = {
    "telegram": "NOTIFY_TELEGRAM_TARGET",
    "whatsapp": "NOTIFY_WHATSAPP_TARGET",
    "local": "NOTIFY_LOCAL_TARGET",
}

DEFAULT_QUEUE_DIR = os.path.expanduser("~/.xomni-notify")
DEFAULT_QUEUE_PATH = os.path.join(DEFAULT_QUEUE_DIR, "queue.jsonl")

# env override for the host gateway binary name (default: hermes)
ENV_SENDER = "NOTIFY_SENDER"


class NotifyError(Exception):
    """Loud failure: unknown channel, unreadable queue (write-side)."""


# ─── paths & resolution ─────────────────────────────────────────────────────

def queue_path() -> str:
    """Outgoing queue path — ``XOMNI_NOTIFY_QUEUE`` override, else default."""
    return os.environ.get("XOMNI_NOTIFY_QUEUE") or DEFAULT_QUEUE_PATH


def resolve_target(channel: str, config_get=None,
                   env: dict | None = None) -> str:
    """Resolve a channel's delivery target.

    Precedence: config getter (``notify.channels.<channel>.target``) > env
    var (``NOTIFY_<CHANNEL>_TARGET``) > channel name itself (``local`` only —
    every other channel is loud when unconfigured).
    """
    if channel not in CHANNELS:
        raise NotifyError(
            "unknown channel %r — known: %s" % (channel, ", ".join(CHANNELS)))
    if config_get is not None:
        try:
            got = config_get("notify.channels.%s.target" % channel)
        except Exception:
            got = None
        if isinstance(got, str) and got.strip():
            return got.strip()
    env = os.environ if env is None else env
    var = ENV_TARGETS[channel]
    if env.get(var):
        return env[var].strip()
    if channel == "local":
        return "local"
    raise NotifyError(
        "channel %r has no target: set config notify.channels.%s.target "
        "or env %s" % (channel, channel, var))


def mask_target(target: str) -> str:
    """Mask a delivery target — never print the full value.

    Keeps the last 4 characters (enough to disambiguate in logs), replaces
    everything before with ``***``. Local targets are already opaque.
    """
    t = (target or "").strip()
    if not t or t == "local":
        return t or "(unset)"
    if len(t) <= 4:
        return "***"
    return "***" + t[-4:]


# ─── payloads ───────────────────────────────────────────────────────────────

def build_payload(channel: str, text: str, target: str) -> dict:
    """One queued notification payload."""
    return {
        "id": "N%x-%s" % (int(time.time() * 1000), uuid.uuid4().hex[:6]),
        "channel": channel,
        "target": target,
        "text": text,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def delivery_command(payload: dict, sender: str | None = None) -> str:
    """The exact host-gateway command that WOULD deliver ``payload``.

    ``sender`` defaults to the ``NOTIFY_SENDER`` env var or ``hermes``.
    Everything is shell-quoted so the string is safe to run as-is.
    """
    sender = sender or os.environ.get(ENV_SENDER) or "hermes"
    return "%s send --channel %s --to %s --text %s" % (
        sender,
        shlex.quote(payload["channel"]),
        shlex.quote(payload["target"]),
        shlex.quote(payload["text"]),
    )


# ─── queue ──────────────────────────────────────────────────────────────────

class NotifyQueue:
    """Append-only outgoing payload queue (JSONL)."""

    def __init__(self, path: str | None = None):
        self.path = path or queue_path()

    def append(self, payload: dict) -> dict:
        """Append one payload -> the payload (also the JSONL line)."""
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return payload

    def read(self) -> list[dict]:
        """All queued payloads, oldest first. Corrupt lines are skipped."""
        out = []
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue  # torn append — never raise on read
        except FileNotFoundError:
            return []
        return out

    def count(self) -> int:
        return len(self.read())

    def clear(self) -> int:
        """Drop the queue; returns the number of payloads removed."""
        n = self.count()
        try:
            os.remove(self.path)
        except FileNotFoundError:
            n = 0
        return n


# ─── send ───────────────────────────────────────────────────────────────────

def _default_runner(cmd: str) -> None:
    """Run the delivery command through the host gateway."""
    subprocess.run(cmd, shell=True, check=False)


def send(channel: str, text: str, *, config_get=None, run: bool = False,
         path: str | None = None, env: dict | None = None,
         runner=None) -> dict:
    """Queue one notification; NEVER transmits unless ``run=True``.

    Returns ``{"payload": ..., "command": ..., "ran": bool, "queued": True}``.
    ``runner`` is injectable for tests (default: subprocess via the host
    gateway binary). Unknown channels raise ``NotifyError`` and leave the
    queue untouched.
    """
    target = resolve_target(channel, config_get, env)
    payload = build_payload(channel, text, target)
    q = NotifyQueue(path or queue_path())
    q.append(payload)
    cmd = delivery_command(payload)
    ran = False
    if run:
        (runner or _default_runner)(cmd)
        ran = True
    return {"payload": payload, "command": cmd, "ran": ran, "queued": True}


# ─── digest ─────────────────────────────────────────────────────────────────

def digest(items: list[str], title: str) -> str:
    """Build a batched digest body: title + numbered items + ts."""
    lines = ["%s (%s)" % (title.strip() or "Digest",
                          datetime.now(timezone.utc)
                          .isoformat(timespec="seconds"))]
    for i, item in enumerate(items, 1):
        lines.append("  %d. %s" % (i, str(item).strip()))
    return "\n".join(lines)


# ─── reports (all targets MASKED) ───────────────────────────────────────────

def channels_table(config_get=None, env: dict | None = None) -> str:
    """Channel -> masked target table. Full targets are never printed."""
    rows = []
    for ch in CHANNELS:
        try:
            target = resolve_target(ch, config_get, env)
            shown = mask_target(target)
        except NotifyError:
            shown = "(unconfigured)"
        rows.append("  %-9s %s" % (ch, shown))
    return "channels (masked targets):\n" + "\n".join(rows)


def status_text(queue: NotifyQueue, config_get=None,
                env: dict | None = None) -> str:
    """Queue length + which channels are configured (masked)."""
    n = queue.count()
    configured, unconfigured = [], []
    for ch in CHANNELS:
        try:
            resolve_target(ch, config_get, env)
            configured.append(ch)
        except NotifyError:
            unconfigured.append(ch)
    lines = [
        "notify status:",
        "  queue: %d pending payload(s) @ %s" % (n, queue.path),
        "  channels configured: %s" % (", ".join(configured) or "none"),
    ]
    if unconfigured:
        lines.append("  channels unconfigured: %s" % ", ".join(unconfigured))
    return "\n".join(lines)


def send_report(result: dict) -> str:
    """Human-readable send result — target shown MASKED only.

    The literal ``command`` line is the actionable artifact the host would
    run; everything else (the summary line) uses the masked target.
    """
    p = result["payload"]
    state = "SENT" if result["ran"] else "queued (not sent)"
    return (
        "[notify] %s: #%s -> %s (target %s)\n"
        "[notify] would run: %s\n"
        "[notify] to actually send now, re-run with --send"
        % (state, p["id"], p["channel"], mask_target(p["target"]),
           result["command"])
    )
