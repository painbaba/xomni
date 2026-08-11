"""WaitPerk-style sponsorship engine — pure stdlib, no Hermes imports.

Implements the fundamental: one sponsor line while the agent works, impressions
tracked per work event, revenue split 50/50 by impression share, payouts capped
at what sponsors paid (by construction). Unit-testable in isolation.
"""
from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field

STATE_DIR = os.path.expanduser("~/.waitperk")
STATE_PATH = os.path.join(STATE_DIR, "state.json")
CONFIG_PATH = os.path.join(STATE_DIR, "config.json")
CURRENT_LINE_PATH = os.path.join(STATE_DIR, "current.txt")

SHARE_FRACTION = 0.5  # the WaitPerk 50/50 split

DEFAULT_CONFIG = {
    # Demo sponsor pool — replace with real sponsors + paid amounts.
    "sponsors": [
        {"id": "demo-001", "message": "Build faster with RepoBoost — try it free", "paid": 100.0},
        {"id": "demo-002", "message": "Ship CI in minutes: PipeDeck", "paid": 100.0},
        {"id": "demo-003", "message": "Secure your keys: VaultSweep", "paid": 100.0},
    ],
    # Simulated network size for impression-share math in demo mode. In live
    # mode the sync server returns the real total and this is ignored.
    "network_total_impressions": 10_000,
    # Empty = local demo mode (sync is a dry run). Set to a real endpoint to go live.
    "sync_url": "",
    "surface": "hermes-cli",
}

DEFAULT_STATE = {
    "device_id": "",
    "paused": False,
    "impressions": 0,
    "active_seconds": 0.0,
    "last_event_ts": 0.0,
    "current_sponsor_idx": 0,
    "earnings_total": 0.0,
    "synced_impressions": 0,
    "sessions": [],
}


@dataclass
class Ledger:
    """Load/save the sponsor state ledger."""

    state: dict = field(default_factory=lambda: deepcopy(DEFAULT_STATE))
    config: dict = field(default_factory=lambda: deepcopy(DEFAULT_CONFIG))
    dirty: bool = False

    @classmethod
    def load(cls) -> "Ledger":
        led = cls()
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                led.state.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            led.state["device_id"] = secrets.token_hex(16)
            led.dirty = True
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                led.config.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return led

    def save(self) -> None:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, sort_keys=True)
        self.dirty = False

    def save_config(self) -> None:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, sort_keys=True)


def current_sponsor(led: Ledger) -> dict:
    """Sponsor currently on screen (round-robin over the pool)."""
    sponsors = led.config.get("sponsors") or []
    if not sponsors:
        return {"id": "none", "message": "no sponsors configured", "paid": 0.0}
    idx = led.state.get("current_sponsor_idx", 0) % len(sponsors)
    return sponsors[idx]


def rotate_sponsor(led: Ledger) -> dict:
    """Advance to the next sponsor (called each session start)."""
    sponsors = led.config.get("sponsors") or []
    if sponsors:
        led.state["current_sponsor_idx"] = (
            led.state.get("current_sponsor_idx", 0) + 1
        ) % len(sponsors)
    return current_sponsor(led)


def record_work_event(led: Ledger, now: float | None = None) -> dict:
    """One impression unit = one agent work event (LLM call or tool call).

    Skips counting while paused (the line is blank, so no impression exists).
    Also accumulates wall-clock active time between events.
    """
    now = now if now is not None else time.time()
    if led.state.get("paused"):
        led.state["last_event_ts"] = now
        return {"counted": False, "impressions": led.state["impressions"]}
    last = led.state.get("last_event_ts") or now
    delta = max(0.0, now - last)
    if delta < 600:  # ignore gaps >10min (idle periods are not screen time)
        led.state["active_seconds"] = led.state.get("active_seconds", 0.0) + delta
    led.state["last_event_ts"] = now
    led.state["impressions"] = led.state.get("impressions", 0) + 1
    _write_current_line(led)
    led.dirty = True
    return {"counted": True, "impressions": led.state["impressions"]}


def start_session(led: Ledger, now: float | None = None) -> dict:
    sponsor = rotate_sponsor(led)
    led.state["sessions"] = led.state.get("sessions", [])
    led.state["sessions"].append(
        {
            "id": uuid.uuid4().hex[:12],
            "start": now if now is not None else time.time(),
            "end": None,
            "sponsor_id": sponsor["id"],
            "impressions": 0,
        }
    )
    _write_current_line(led)
    led.dirty = True
    return sponsor


def end_session(led: Ledger, now: float | None = None) -> dict:
    """Close the open session window; impressions of the whole session were
    already accumulated into the global counter, so record a snapshot here."""
    now = now if now is not None else time.time()
    sessions = led.state.get("sessions", [])
    if sessions and sessions[-1].get("end") is None:
        s = sessions[-1]
        s["end"] = now
        s["impressions"] = led.state["impressions"]
    led.dirty = True
    return sessions[-1] if sessions else {}


def impressions_share(led: Ledger) -> float:
    """Your share of network impressions (0..1)."""
    total = led.config.get("network_total_impressions", 0) or 0
    mine = led.state.get("impressions", 0)
    if total <= 0 or mine <= 0:
        return 0.0
    return min(mine / total, 1.0)


def compute_earnings(led: Ledger, sponsor_paid: float | None = None) -> float:
    """50/50 split by impression share, capped at half the sponsor's payment.

    earnings = 0.5 * P * (your_impressions / total_impressions), capped at 0.5*P.
    """
    paid = sponsor_paid
    if paid is None:
        paid = float(current_sponsor(led).get("paid", 0.0))
    share = impressions_share(led)
    return min(SHARE_FRACTION * paid * share, SHARE_FRACTION * paid)


def payout_invariant(led: Ledger, sponsor_paid: float | None = None) -> bool:
    """Payouts can never exceed what sponsors paid, by construction:
    sum over ALL developers of earnings_i = 0.5*P*sum(share_i) = 0.5*P <= P."""
    paid = sponsor_paid
    if paid is None:
        paid = float(current_sponsor(led).get("paid", 0.0))
    share = impressions_share(led)
    total_payouts = SHARE_FRACTION * paid * share
    return total_payouts <= paid


def render_line(led: Ledger, width: int = 72) -> str:
    """The one sponsor line — the thing that sits on screen while the agent works."""
    if led.state.get("paused"):
        return ""
    sp = current_sponsor(led)
    line = f"sponsor▸ {sp['message']}"
    return line[:width]


def sync_payload(led: Ledger) -> dict:
    """Exactly what leaves the machine on sync: impression IDs, surface, version,
    session hash. NEVER prompts, code, file paths, or conversation content."""
    return {
        "impressions": led.state.get("impressions", 0),
        "synced_impressions": led.state.get("synced_impressions", 0),
        "surface": led.config.get("surface", "hermes-cli"),
        "client_version": "waitperk-module-0.1.0",
        "session_hash": _session_hash(led),
    }


def _session_hash(led: Ledger) -> str:
    """Deterministic hash of device_id — identifies the install, not the content."""
    import hashlib

    dev = led.state.get("device_id", "")
    return hashlib.sha256(dev.encode()).hexdigest()[:16]


def sync(led: Ledger, http_post=None) -> dict:
    """Push the sync payload to the configured endpoint.

    With no sync_url (default) this is a local dry run: returns the exact
    payload that WOULD be sent. http_post is injectable for tests.
    """
    payload = sync_payload(led)
    url = led.config.get("sync_url", "")
    if not url:
        return {"mode": "dry-run", "payload": payload}
    if http_post is None:
        import urllib.request

        def http_post(url, data):
            req = urllib.request.Request(
                url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status

    try:
        status = http_post(url, payload)
        led.state["synced_impressions"] = led.state.get("impressions", 0)
        led.dirty = True
        return {"mode": "live", "status": status, "payload": payload}
    except Exception as exc:  # network failure must never break the agent
        return {"mode": "error", "error": str(exc), "payload": payload}


def status_text(led: Ledger) -> str:
    """Human-readable /sponsor status block."""
    sp = current_sponsor(led)
    share = impressions_share(led)
    earnings = compute_earnings(led)
    lines = [
        "WaitPerk sponsorship module",
        f"  sponsor on screen : {sp['message']}",
        f"  impressions       : {led.state.get('impressions', 0)}",
        f"  active time       : {led.state.get('active_seconds', 0.0):.0f}s",
        f"  impression share  : {share * 100:.4f}% (network total {led.config.get('network_total_impressions')})",
        f"  est. earnings     : ${earnings:.4f}  (50/50 split, capped)",
        f"  payout invariant  : never exceeds sponsor paid — by construction",
        f"  paused            : {led.state.get('paused')}",
        f"  sync mode         : {'LIVE ' + str(led.config.get('sync_url')) if led.config.get('sync_url') else 'dry-run (no sync_url set)'}",
        f"  device_id         : {led.state.get('device_id', '')[:8]}…",
        f"  current line file : {CURRENT_LINE_PATH}",
    ]
    return "\n".join(lines)


def _write_current_line(led: Ledger) -> None:
    """Sink for external statuslines (tmux, terminal title, shell prompt).

    The Hermes equivalent of a Claude Code statusLine surface: any tool can
    tail this file and show the sponsor line while the agent works.
    """
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(CURRENT_LINE_PATH, "w", encoding="utf-8") as f:
            f.write(render_line(led) + "\n")
    except OSError:
        pass
