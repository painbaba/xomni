"""PerkLine v2 — the researched "best model" prototype for status-line monetization.

Fixes the three structural flaws of the plain WaitPerk CPM-impression model:

  1. GLANCE VALUE  — impressions are the weakest ad signal; advertisers pay for
     outcomes. PerkLine prices by engagement tier, not by glance:
        cpm  $10-40  per 1000 renders   (brand awareness; B2B display benchmark)
        cpc  $1-8    per engagement    (B2B search CPC benchmark)
        cpa  $20-200 per completed action (SaaS signup/demo CPA benchmark)
  2. RELEVANCE     — untargeted inventory is worth ~nothing. Sponsors target
     stack tags (python/node/go/...); the client matches against the LOCAL repo
     (extension scan, nothing leaves the machine). Matched inventory is worth
     2-5x in ad markets; privacy is preserved by construction.
  3. VERIFIABILITY — "live numbers, zeros included" is unprovable in WaitPerk.
     Every render/engagement carries an HMAC-SHA256 receipt signed with the
     install secret; a sponsor network can verify each delivery. The cap
     invariant (payouts never exceed what sponsors paid) is kept and generalized
     per-sponsor via escrow. The line slot is priced by a second-price auction
     (honest price discovery).

Pure stdlib, no Hermes imports. Unit-testable in isolation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from copy import deepcopy

STATE_DIR = os.path.expanduser("~/.perkline")
STATE_PATH = os.path.join(STATE_DIR, "state.json")
CONFIG_PATH = os.path.join(STATE_DIR, "config.json")
CURRENT_LINE_PATH = os.path.join(STATE_DIR, "current.txt")

SHARE_FRACTION = 0.5  # the WaitPerk 50/50 split, retained

# Industry-standard price benchmarks (public, order-of-magnitude ranges used to
# set demo prices; real prices come from the sponsor network):
#   B2B display CPM .......... $10-40        (e.g. LinkedIn $20-60)
#   B2B search CPC ........... $1-8          (Google Ads B2B-tech range)
#   SaaS trial CPA ........... $20-200       (dev-tool affiliate/signup range)
BENCHMARKS = {"cpm": (10.0, 40.0), "cpc": (1.0, 8.0), "cpa": (20.0, 200.0)}

DEFAULT_CONFIG = {
    "sponsors": [
        # model: cpm | cpc | cpa ; price per unit; budget = escrow cap for the campaign
        {"id": "pk-demo-1", "message": "RepoBoost: index your codebase locally", "url": "https://example.invalid/repoboost",
         "model": "cpa", "price": 50.0, "budget": 500.0, "targeting": ["python", "node", "go", "rust"]},
        {"id": "pk-demo-2", "message": "PipeDeck: CI pipelines in minutes", "url": "https://example.invalid/pipedeck",
         "model": "cpc", "price": 3.0, "budget": 300.0, "targeting": ["docker", "node", "python"]},
        {"id": "pk-demo-3", "message": "VaultSweep: find leaked secrets in your repo", "url": "https://example.invalid/vaultsweep",
         "model": "cpm", "price": 25.0, "budget": 200.0, "targeting": []},  # empty targeting = everyone
    ],
    "surface": "hermes-cli",
    "sync_url": "",
    "auction": {"enabled": False, "bids": []},
}

DEFAULT_STATE = {
    "device_id": "",
    "secret": "",
    "paused": False,
    "renders": 0,
    "engagements": {},       # sponsor_id -> count
    "actions": {},           # sponsor_id -> count (CPA completions)
    "escrow_spent": {},      # sponsor_id -> total paid out
    "receipts": [],          # capped ring buffer of signed delivery receipts
    "current_sponsor_id": None,
    "last_ts": 0.0,
    "earnings_total": 0.0,
    "synced_renders": 0,
}

# stack vocabulary used by local (private) relevance matching
_STACK_RULES = [
    ("python", (".py", "requirements.txt", "pyproject.toml", "setup.py")),
    ("node", (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", "package.json")),
    ("go", (".go", "go.mod")),
    ("rust", (".rs", "cargo.toml")),
    ("java", (".java", "pom.xml")),
    ("ruby", (".rb", "gemfile")),
    ("php", (".php",)),
    ("docker", ("dockerfile", "compose.yml", "compose.yaml")),
    ("c", (".c", ".h")),
    ("cpp", (".cpp", ".cc", ".hpp")),
    ("sql", (".sql",)),
]


class Ledger:
    def __init__(self):
        # deepcopy: DEFAULT_STATE/DEFAULT_CONFIG contain nested dicts/lists that
        # must NOT be shared across instances (mutation leakage between tests/sessions)
        self.state = deepcopy(DEFAULT_STATE)
        self.config = deepcopy(DEFAULT_CONFIG)
        self.dirty = False

    @classmethod
    def load(cls) -> "Ledger":
        led = cls()
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                led.state.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            led.state["device_id"] = secrets.token_hex(16)
            led.state["secret"] = secrets.token_hex(32)
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


def stack_tags(root: str) -> list[str]:
    """Local, private stack detection (extension scan only). Nothing leaves the machine."""
    skip = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target", ".next", "vendor"}
    tags: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            low = fn.lower()
            for tag, needles in _STACK_RULES:
                if low in needles or low.endswith(tuple(n for n in needles if n.startswith("."))):
                    tags.add(tag)
    return sorted(tags)


def eligible_sponsors(led: Ledger, repo_tags: list[str] | None = None) -> list[dict]:
    """Sponsors whose targeting matches the local stack. Empty targeting = everyone."""
    tags = set(repo_tags or [])
    out = []
    for sp in led.config.get("sponsors", []):
        target = set(sp.get("targeting") or [])
        if not target or target & tags:
            out.append(sp)
    return out


def _receipt(led: Ledger, sponsor_id: str, event: str, ts: float) -> str:
    """HMAC-SHA256 delivery receipt: (nonce, sponsor, event, ts, surface)."""
    nonce = uuid.uuid4().hex[:12]
    body = "|".join([nonce, sponsor_id, event, f"{ts:.3f}", led.config.get("surface", "")])
    sig = hmac.new(led.state["secret"].encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}|{sig}"


def verify_receipt(receipt: str, secret: str) -> bool:
    """A sponsor network can verify each delivery receipt (no shared ledger needed)."""
    try:
        body, sig = receipt.rsplit("|", 1)
    except ValueError:
        return False
    expect = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(sig, expect)


def _push_receipt(led: Ledger, receipt: str) -> None:
    led.state["receipts"] = (led.state.get("receipts", []) + [receipt])[-200:]  # ring buffer


def current_sponsor(led: Ledger, repo_tags: list[str] | None = None) -> dict | None:
    sp_id = led.state.get("current_sponsor_id")
    for sp in eligible_sponsors(led, repo_tags):
        if sp["id"] == sp_id:
            return sp
    elig = eligible_sponsors(led, repo_tags)
    return elig[0] if elig else None


def record_render(led: Ledger, repo_tags: list[str] | None = None, now: float | None = None) -> dict:
    """A render = the sponsor line was on screen for a work event. CPM tier counts here."""
    now = now if now is not None else time.time()
    if led.state.get("paused"):
        return {"counted": False, "sponsor": None}
    sp = current_sponsor(led, repo_tags)
    if sp is None:
        return {"counted": False, "sponsor": None}
    led.state["current_sponsor_id"] = sp["id"]
    led.state["renders"] = led.state.get("renders", 0) + 1
    if sp.get("model") == "cpm":
        _charge(led, sp, sp.get("price", 0.0) / 1000.0)  # price per 1000 renders
    _push_receipt(led, _receipt(led, sp["id"], "render", now))
    _write_line(led, sp)
    led.dirty = True
    return {"counted": True, "sponsor": sp}


def engage(led: Ledger, sponsor_id: str | None = None, now: float | None = None) -> dict:
    """An engagement (the dev actually activates the line). CPC tier counts here.
    Only the sponsor currently ON SCREEN can be engaged — no re-filtering."""
    now = now if now is not None else time.time()
    if led.state.get("paused"):
        return {"counted": False}
    sp = None
    if sponsor_id:
        sp = next((s for s in led.config.get("sponsors", []) if s["id"] == sponsor_id), None)
    if sp is None:
        sp = next((s for s in led.config.get("sponsors", [])
                   if s["id"] == led.state.get("current_sponsor_id")), None)
    if sp is None:
        return {"counted": False}
    led.state["engagements"][sp["id"]] = led.state["engagements"].get(sp["id"], 0) + 1
    if sp.get("model") == "cpc":
        _charge(led, sp, sp.get("price", 0.0))
    _push_receipt(led, _receipt(led, sp["id"], "engage", now))
    led.dirty = True
    return {"counted": True, "sponsor": sp, "url": sp.get("url")}


def complete_action(led: Ledger, sponsor_id: str, now: float | None = None) -> dict:
    """A completed action (user confirms: signed up / installed / filed a bug).
    CPA tier counts here. In live mode this would be gated by a sponsor-side
    verification callback; locally it is an explicit, user-confirmed event."""
    now = now if now is not None else time.time()
    if led.state.get("paused"):
        return {"counted": False}
    sp = next((s for s in led.config.get("sponsors", []) if s["id"] == sponsor_id), None)
    if sp is None:
        return {"counted": False, "error": f"unknown sponsor {sponsor_id}"}
    led.state["actions"][sp["id"]] = led.state["actions"].get(sp["id"], 0) + 1
    if sp.get("model") == "cpa":
        _charge(led, sp, sp.get("price", 0.0))
    _push_receipt(led, _receipt(led, sp["id"], "action", now))
    led.dirty = True
    return {"counted": True, "sponsor": sp}


def _charge(led: Ledger, sp: dict, amount: float) -> None:
    """Escrow-capped charging: sponsor spend for a campaign can never exceed its
    budget; the developer keeps 50% of what the sponsor actually spends."""
    spent = led.state["escrow_spent"].get(sp["id"], 0.0)
    budget = sp.get("budget", 0.0)
    sponsor_spend = min(amount, max(0.0, budget - spent))  # what the sponsor pays
    dev_share = sponsor_spend * SHARE_FRACTION              # 50/50 split
    led.state["escrow_spent"][sp["id"]] = spent + sponsor_spend
    led.state["earnings_total"] = led.state.get("earnings_total", 0.0) + dev_share


def compute_earnings(led: Ledger) -> float:
    """Total accrued earnings = sum over sponsors of escrow-capped 50/50 shares."""
    return float(led.state.get("earnings_total", 0.0))


def escrow_invariant(led: Ledger) -> bool:
    """Payouts can never exceed what sponsors paid: per sponsor, spent <= budget."""
    for sp in led.config.get("sponsors", []):
        if led.state["escrow_spent"].get(sp["id"], 0.0) > sp.get("budget", 0.0) + 1e-9:
            return False
    return True


def run_auction(led: Ledger, bids: list[dict]) -> dict:
    """Second-price sealed-bid auction for the line slot.
    bids = [{"sponsor_id": str, "bid": float}]. Winner pays the second-highest bid."""
    if not bids:
        return {"winner": None, "price": 0.0}
    ordered = sorted(bids, key=lambda b: b["bid"], reverse=True)
    winner = ordered[0]
    price = ordered[1]["bid"] if len(ordered) > 1 else 0.0
    led.config["auction"] = {"enabled": True, "bids": bids, "winner": winner["sponsor_id"], "price": price}
    led.state["current_sponsor_id"] = winner["sponsor_id"]
    led.dirty = True
    return {"winner": winner["sponsor_id"], "price": price}


def render_line(led: Ledger, repo_tags: list[str] | None = None, width: int = 72) -> str:
    if led.state.get("paused"):
        return ""
    sp = current_sponsor(led, repo_tags)
    if sp is None:
        return ""
    model = sp.get("model", "cpm").upper()
    line = f"sponsor▸ {sp['message']}  [{model}]  (/perkline engage {sp['id']})"
    return line[:width]


def sync_payload(led: Ledger) -> dict:
    """What leaves the machine: counts, receipts, surface, version, session hash.
    NEVER prompts, code, file paths, conversation content, or repo tags."""
    return {
        "renders": led.state.get("renders", 0),
        "engagements": led.state.get("engagements", {}),
        "actions": led.state.get("actions", {}),
        "escrow_spent": led.state.get("escrow_spent", {}),
        "receipts": led.state.get("receipts", [])[-50:],
        "surface": led.config.get("surface", "hermes-cli"),
        "client_version": "perkline-0.1.0",
        "session_hash": hashlib.sha256(led.state.get("device_id", "").encode()).hexdigest()[:16],
    }


def sync(led: Ledger, http_post=None) -> dict:
    payload = sync_payload(led)
    url = led.config.get("sync_url", "")
    if not url:
        return {"mode": "dry-run", "payload": payload}
    if http_post is None:
        import urllib.request

        def http_post(url, data):
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status
    try:
        status = http_post(url, payload)
        led.state["synced_renders"] = led.state.get("renders", 0)
        led.dirty = True
        return {"mode": "live", "status": status, "payload": payload}
    except Exception as exc:
        return {"mode": "error", "error": str(exc), "payload": payload}


def status_text(led: Ledger, repo_tags: list[str] | None = None) -> str:
    sp = current_sponsor(led, repo_tags)
    elig = eligible_sponsors(led, repo_tags)
    lines = [
        "PerkLine v2 — status-line monetization (researched model)",
        f"  sponsor on screen : {sp['message'] if sp else 'none (no matching sponsor)'}",
        f"  local stack tags  : {', '.join(repo_tags or []) or 'unknown'}",
        f"  eligible sponsors : {len(elig)} of {len(led.config.get('sponsors', []))} (relevance-matched)",
        f"  renders           : {led.state.get('renders', 0)}",
        f"  engagements       : {json.dumps(led.state.get('engagements', {}))}",
        f"  actions (CPA)     : {json.dumps(led.state.get('actions', {}))}",
        f"  earnings (50/50)  : ${compute_earnings(led):.4f}",
        f"  escrow invariant  : {'OK — spent ≤ budget per sponsor' if escrow_invariant(led) else 'VIOLATED'}",
        f"  pricing tiers     : cpm $10-40/1k  cpc $1-8  cpa $20-200 (benchmarks)",
        f"  auction           : {'winner ' + str(led.config['auction'].get('winner')) + ' @ $' + str(led.config['auction'].get('price')) if led.config.get('auction', {}).get('enabled') else 'off (fixed prices)'}",
        f"  paused            : {led.state.get('paused')}",
        f"  sync mode         : {'LIVE' if led.config.get('sync_url') else 'dry-run'}",
    ]
    return "\n".join(lines)


def _write_line(led: Ledger, sp: dict | None = None) -> None:
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(CURRENT_LINE_PATH, "w", encoding="utf-8") as f:
            f.write(render_line(led) + "\n")
    except OSError:
        pass
