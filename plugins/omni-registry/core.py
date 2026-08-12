"""omni-registry core — capability-declared model registry (pure stdlib).

Loads data/capabilities.json: one record per gateway model with per-field
source attribution (verified | spec | estimated), origin provenance, a closed
capability enum (kimi-cli precedent + tools/structured_output), and status
tombstones (removed models are preserved, never deleted — KLIP-6 precedent).

Zero hooks, zero Hermes imports, zero network, zero subprocess: the registry
is advisory metadata consumed by /models2 and the registry_status tool.
Schema per .tmp/research-next/CAPABILITY-REGISTRY.md (2026-08-12).

Pure stdlib (json/os) — unit-testable in isolation.
"""
from __future__ import annotations

import json
import os

SCHEMA_VERSION = "1.0.0"
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "capabilities.json")

# Closed capability enum (research F1): kimi-cli's 4 values + tools /
# structured_output from models.dev intent labels. always_thinking is a
# distinct value (thinking that cannot be toggled off).
CAPABILITY_ENUM = ("image_in", "video_in", "thinking", "always_thinking", "tools", "structured_output")
STATUS_ENUM = ("active", "removed", "unverified")  # unverified = never HTTP-200'd
SOURCE_ENUM = ("verified", "spec", "estimated")

_REQUIRED_KEYS = (
    "id", "name", "provider", "status", "context_window",
    "capabilities", "cost_per_1m", "verified", "provenance",
)

# Derived recommendations (research §Consumers): role -> capability filter.
# Prefers records whose primary capability was live-verified over spec claims.
_ROLE_CAPS = {
    "default": {"thinking": True, "tools": True},
    "reasoning": {"thinking": True},
    "coding": {"tools": True, "structured_output": True},
    "vision": {"image_in": True},
    "fast": {"tools": True},
}


def registry_load(path: str | None = None) -> dict[str, dict]:
    """Load capabilities.json -> {model_id: record}.

    Models and tombstones are merged; a tombstone id can never be silently
    re-added (KLIP-6: decommission is marked, not dropped).
    """
    path = path or DATA_PATH
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"schema_version {data.get('schema_version')!r} != {SCHEMA_VERSION} (CI gate)"
        )
    records: dict[str, dict] = {}
    for rec in data.get("models", []):
        records[rec["id"]] = rec
    for rec in data.get("tombstones", []):
        records[rec["id"]] = rec
    return records


def active_records(registry: dict | None = None) -> list[dict]:
    reg = registry if registry is not None else registry_load()
    return [r for r in reg.values() if r.get("status") == "active"]


def verified_count(registry: dict | None = None) -> int:
    """Active models whose verified.ok is true (the '25 verified' stat source)."""
    reg = registry if registry is not None else registry_load()
    return sum(
        1 for r in reg.values()
        if r.get("status") == "active" and (r.get("verified") or {}).get("ok")
    )


def capability(model_id: str, key: str | None = None,
               registry: dict | None = None) -> dict | None:
    """Single-model lookup. key=None -> full record; key -> field value
    (envelope fields return their {value, source, origin} dict)."""
    reg = registry if registry is not None else registry_load()
    rec = reg.get(model_id)
    if rec is None:
        return None
    if key is None:
        return rec
    return rec.get(key)


def context_window(model_id: str, registry: dict | None = None) -> int | None:
    rec = capability(model_id, registry=registry)
    if rec is None:
        return None
    return (rec.get("context_window") or {}).get("value")


def max_output(model_id: str, registry: dict | None = None) -> int | None:
    rec = capability(model_id, registry=registry)
    if rec is None:
        return None
    mo = rec.get("max_output") or {}
    return mo.get("value")


def verified_capability(cap: str, registry: dict | None = None) -> list[str]:
    """Active models whose capability_sources[cap] == 'verified' (live
    spot-checked — e.g. image_in only for minimax-m3)."""
    reg = registry if registry is not None else registry_load()
    return [
        mid for mid, r in reg.items()
        if r.get("status") == "active"
        and cap in r.get("capabilities", [])
        and (r.get("capability_sources") or {}).get(cap) == "verified"
    ]


def filter_by_capability(status: str = "active", registry: dict | None = None,
                         **caps: bool) -> list[str]:
    """Model ids matching capability requirements.

    caps: name -> bool (True = must have, False = must NOT have).
    status='active' (default) skips tombstones; 'any' includes them.
    """
    reg = registry if registry is not None else registry_load()
    unknown = [c for c in caps if c not in CAPABILITY_ENUM]
    if unknown:
        raise ValueError(
            f"unknown capability {unknown}; enum: {', '.join(CAPABILITY_ENUM)}"
        )
    out = []
    for mid, rec in reg.items():
        if status != "any" and rec.get("status") != status:
            continue
        have = set(rec.get("capabilities", []))
        if all(bool(want) == (name in have) for name, want in caps.items()):
            out.append(mid)
    return out


def recommend(role: str | None = None, registry: dict | None = None) -> str:
    """Derived recommendation (research §Consumers): filter_by_capability
    instead of a hand-maintained map. Prefers a verified primary capability
    (e.g. vision -> minimax-m3, the only image_in model spot-checked live)."""
    reg = registry if registry is not None else registry_load()
    role = role or "default"
    caps = _ROLE_CAPS.get(role, _ROLE_CAPS["default"])
    picks = filter_by_capability("active", reg, **caps)
    if not picks:
        return ""
    primary = next(iter(caps))
    verified = [
        m for m in picks
        if (reg[m].get("capability_sources") or {}).get(primary) == "verified"
    ]
    return (verified or picks)[0]


def capabilities_text(registry: dict | None = None,
                      cap_filter: str | None = None) -> str:
    """/models2 output: per-model ctx/tools/think/vision/video columns with
    per-field source tags; retired rows rendered as tombstones."""
    reg = registry if registry is not None else registry_load()
    if cap_filter and cap_filter not in CAPABILITY_ENUM:
        raise ValueError(
            f"unknown capability {cap_filter!r}; enum: {', '.join(CAPABILITY_ENUM)}"
        )
    active = [r for r in reg.values() if r.get("status") == "active"]
    retired = [r for r in reg.values() if r.get("status") != "active"]
    verified = verified_count(reg)
    lines = [
        f"model registry v{SCHEMA_VERSION} — {len(active)} active, "
        f"{verified} verified, {len(retired)} retired/tombstoned",
        "src: v=verified s=spec e=estimated · retired rows are tombstones (never deleted)",
        f"  {'model':<22} {'ctx':>9} {'out':>8} {'tools':>5} {'think':>5} "
        f"{'vision':>5} {'video':>5} src",
    ]
    if cap_filter:
        active = [r for r in active if cap_filter in r.get("capabilities", [])]

    def _flag(rec: dict, cap: str) -> str:
        return "yes" if cap in rec.get("capabilities", []) else "no"

    for rec in active:
        cw = rec.get("context_window") or {}
        mo = rec.get("max_output") or {}
        src = {"verified": "v", "spec": "s", "estimated": "e"}.get(cw.get("source"), "?")
        lines.append(
            f"  {rec['id']:<22} {cw.get('value', 0):>9,} {mo.get('value', 0):>8,} "
            f"{_flag(rec, 'tools'):>5} {_flag(rec, 'thinking'):>5} "
            f"{_flag(rec, 'image_in'):>5} {_flag(rec, 'video_in'):>5} {src}"
        )
    for rec in retired:
        lines.append(f"  {rec['id']:<22} RETIRED ({rec.get('status')})")
    return "\n".join(lines)


def model_detail_text(model_id: str, registry: dict | None = None) -> str:
    """Single-model view with per-field source + origin provenance."""
    reg = registry if registry is not None else registry_load()
    rec = reg.get(model_id)
    if rec is None:
        return f"no record for '{model_id}'"
    cw = rec.get("context_window") or {}
    mo = rec.get("max_output") or {}
    cs = rec.get("capability_sources") or {}
    caps = ", ".join(rec.get("capabilities", []))
    cap_srcs = ", ".join(f"{c}={cs.get(c, 'spec')}" for c in rec.get("capabilities", []))
    cost = rec.get("cost_per_1m") or {}
    ver = rec.get("verified") or {}
    prov = rec.get("provenance") or {}
    lines = [
        rec["id"],
        f"  name:       {rec.get('name', '?')}",
        f"  provider:   {rec.get('provider', '?')}  status: {rec.get('status', '?')}",
        f"  context:    {cw.get('value', 0):,} ({cw.get('source', '?')}) — {cw.get('origin', '')}",
    ]
    if mo.get("value"):
        lines.append(f"  max_output: {mo['value']:,} ({mo.get('source', '?')}) — {mo.get('origin', '')}")
    lines.append(f"  capabilities: {caps}  [{cap_srcs}]")
    lines.append(
        f"  cost_per_1m: ${cost.get('input', 0):.2f} in / ${cost.get('output', 0):.2f} out "
        f"({cost.get('currency', 'USD')}, {cost.get('source', '?')}) — {cost.get('origin', '')}"
    )
    lines.append(
        f"  verified:   ok={ver.get('ok')} ({ver.get('date', '?')}, "
        f"{ver.get('method', '?')}; last_seen {ver.get('last_seen', '?')})"
    )
    lines.append(f"  provenance: {prov.get('primary', '?')} · updated {prov.get('updated_at', '?')}")
    return "\n".join(lines)


def registry_summary_text(registry: dict | None = None) -> str:
    """Compact status for the registry_status tool (no args)."""
    reg = registry if registry is not None else registry_load()
    statuses: dict[str, int] = {}
    for r in reg.values():
        s = r.get("status", "?")
        statuses[s] = statuses.get(s, 0) + 1
    verified = verified_count(reg)
    return "\n".join([
        f"model registry v{SCHEMA_VERSION} — {len(reg)} records total",
        f"  active: {statuses.get('active', 0)} | verified: {verified} | "
        f"removed: {statuses.get('removed', 0)} | unverified: {statuses.get('unverified', 0)}",
        f"  capabilities enum: {' '.join(CAPABILITY_ENUM)}",
        f"  {conflict_report(reg).splitlines()[0]}",
    ])


def conflict_report(registry: dict | None = None,
                    snapshot: dict | None = None) -> str:
    """CI-readable consistency report (research F3: report, don't auto-accept).

    Always runs an internal pass (required fields, enum membership, envelope
    shapes, tombstone integrity). With `snapshot` ({slug: {context_window,
    max_output}}) diffs registry vs the pinned external snapshot and emits
    MISSING-SLUG / CTX / OUT mismatch lines. Plain lines, no markdown —
    greppable in CI. Returns 'conflict_report: OK' when clean.
    """
    reg = registry if registry is not None else registry_load()
    issues: list[str] = []
    for mid, rec in reg.items():
        missing = [k for k in _REQUIRED_KEYS if k not in rec]
        if missing:
            issues.append(f"MISSING-FIELD {mid}: {','.join(missing)}")
            continue
        if rec["status"] not in STATUS_ENUM:
            issues.append(f"STATUS {mid}: {rec['status']!r} not in {STATUS_ENUM}")
        bad_caps = [c for c in rec["capabilities"] if c not in CAPABILITY_ENUM]
        if bad_caps:
            issues.append(f"CAPABILITY {mid}: {bad_caps} not in enum {CAPABILITY_ENUM}")
        for cap, src in (rec.get("capability_sources") or {}).items():
            if cap not in CAPABILITY_ENUM:
                issues.append(f"CAP-SOURCE {mid}: unknown capability {cap!r}")
            if src not in SOURCE_ENUM:
                issues.append(f"CAP-SOURCE {mid}: {cap}={src!r} not in {SOURCE_ENUM}")
        for field in ("context_window", "max_output"):
            env = rec.get(field)
            if env is None:
                continue
            if not isinstance(env, dict) or not isinstance(env.get("value"), int):
                issues.append(f"ENVELOPE {mid}.{field}: expected {{value:int, source, origin}}")
            elif env["value"] <= 0:
                issues.append(f"ENVELOPE {mid}.{field}: value {env['value']} <= 0")
            if env.get("source") not in SOURCE_ENUM:
                issues.append(f"ENVELOPE {mid}.{field}: source {env.get('source')!r} not in {SOURCE_ENUM}")
            if not env.get("origin"):
                issues.append(f"ENVELOPE {mid}.{field}: missing origin provenance")
        cost = rec.get("cost_per_1m") or {}
        if not isinstance(cost.get("input"), (int, float)) or \
           not isinstance(cost.get("output"), (int, float)):
            issues.append(f"COST {mid}: input/output must be numbers")
        if cost.get("source") not in SOURCE_ENUM:
            issues.append(f"COST {mid}: source {cost.get('source')!r} not in {SOURCE_ENUM}")
        ver = rec.get("verified") or {}
        if not isinstance(ver.get("ok"), bool):
            issues.append(f"VERIFIED {mid}: ok must be bool")
    if snapshot:
        for slug, snap in snapshot.items():
            rec = reg.get(slug)
            if rec is None:
                issues.append(f"MISSING-SLUG {slug}: in snapshot, not in registry")
                continue
            sv = (rec.get("context_window") or {}).get("value")
            if sv is not None and snap.get("context_window") is not None and sv != snap["context_window"]:
                issues.append(
                    f"CTX {slug}: registry={sv} snapshot={snap['context_window']} "
                    f"(source={rec['context_window'].get('source')})"
                )
            ov = (rec.get("max_output") or {}).get("value")
            if ov is not None and snap.get("max_output") is not None and ov != snap["max_output"]:
                issues.append(f"OUT {slug}: registry={ov} snapshot={snap['max_output']}")
    if not issues:
        return "conflict_report: OK"
    return f"conflict_report: {len(issues)} issue(s)\n" + "\n".join(issues)
