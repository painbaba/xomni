"""capability-probe core — live-probe ANY provider's /models into the registry.

One live GET {base_url}/models with the provider key, normalized into
registry entries ({id, context_window, vision, reasoning, source:'live-probe',
probed_at}), then merged into the omni-registry capabilities.json with
source='live-probe' kept distinct from spec-derived records (F3 precedent:
report, don't auto-accept — capability envelopes are never overwritten).

Both /models shapes are parsed:

  OpenAI-compatible   {"data": [{"id": ..., "object": ..., "owned_by": ...}]}
                      (a bare list is tolerated; optional metadata keys like
                      context_length / vision / reasoning are extracted when
                      present)
  Anthropic           {"data": [{"type": "model", "id": ...,
                      "display_name": ..., "created_at": ...}]}

Failures are LOUD: every error path raises ProbeError naming the fix (missing
key -> env var + .env path, 401/403 -> key rejected, non-200 -> endpoint
shape, non-JSON -> not a /models endpoint, network/timeout -> connectivity).
The API key is used only in the Authorization / x-api-key header and NEVER
appears in output, exceptions, or returned data.

Zero hooks, zero Hermes imports, pure stdlib (json/os/re/urllib/socket).
The network call is injectable (urlopen=...) so tests need no monkeypatching.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_TIMEOUT = 15
SOURCE = "live-probe"
ENV_PATH = os.path.expanduser("~/AppData/Local/hermes/.env")
UA = {"User-Agent": "xomni-capability-probe/0.1 (live /models probe)"}

# Registry file this plugin refreshes (sibling omni-registry plugin).
REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "omni-registry", "data", "capabilities.json",
)

# Metadata keys that /models payloads commonly use for capability hints.
_CTX_KEYS = ("context_length", "context_window", "max_context", "context",
             "input_token_limit", "max_input_tokens")
_VISION_KEYS = ("vision", "supports_vision", "image_input", "multimodal")
_REASONING_KEYS = ("reasoning", "supports_reasoning", "thinking")


class ProbeError(Exception):
    """Loud, actionable probe failure. Never contains an API key."""


# ---------------------------------------------------------------------------
# keys + time
# ---------------------------------------------------------------------------

def load_key(key_env: str) -> str:
    """Read an API key: os.environ first, then ~/AppData/Local/hermes/.env.

    Returns '' when unset. Never prints or logs the value.
    """
    if key_env:
        val = os.environ.get(key_env)
        if val:
            return val.strip()
        try:
            with open(ENV_PATH, encoding="utf-8") as f:
                for line in f:
                    m = re.match(rf"\s*{re.escape(key_env)}\s*=\s*\"?([^\"\s]+)", line)
                    if m:
                        return m.group(1)
        except OSError:
            pass
    return ""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# parsing: OpenAI-compatible + Anthropic shapes -> normalized entries
# ---------------------------------------------------------------------------

def _meta_value(item: dict, keys: tuple) -> object:
    """Case-insensitive scan for the first present metadata key."""
    lowered = {str(k).lower(): v for k, v in item.items() if isinstance(k, str)}
    for k in keys:
        if k in lowered and lowered[k] is not None:
            return lowered[k]
    return None


def _coerce_ctx(value) -> int | None:
    """context metadata -> int. Accepts ints and '128k'/'1m' style strings."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip().lower().replace(",", "")
        mult = 1
        if s.endswith("k"):
            mult, s = 1024, s[:-1]
        elif s.endswith("m"):
            mult, s = 1024 * 1024, s[:-1]
        try:
            return int(float(s) * mult)
        except ValueError:
            return None
    return None


def _flag(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "supported")
    return bool(value)


def _normalize(item: dict, probed_at: str, name_key: str) -> dict:
    mid = str(item["id"])
    ctx = _coerce_ctx(_meta_value(item, _CTX_KEYS))
    return {
        "id": mid,
        "name": item.get(name_key) or item.get("name") or mid,
        "context_window": ctx,
        "vision": _flag(_meta_value(item, _VISION_KEYS)),
        "reasoning": _flag(_meta_value(item, _REASONING_KEYS)),
        "source": SOURCE,
        "probed_at": probed_at,
    }


def _extract_data(payload, api_type: str) -> list:
    """Pull the model list out of either /models shape (or a bare list)."""
    data = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(data, dict):  # some gateways nest {"models": [...]}
        data = data.get("models") or data.get("data")
    if not isinstance(data, list):
        raise ProbeError(
            f"response shape not parseable as api_type={api_type!r}: expected "
            f'{{"data": [...]}} (OpenAI) / {{"data": [{{"id", "display_name"}}]}} '
            f"(Anthropic) or a bare list, got {type(payload).__name__}. "
            f"Fix: check api_type / base_url."
        )
    return data


def parse_openai(payload, probed_at: str | None = None) -> list[dict]:
    """OpenAI-compatible /models -> normalized entries.

    Accepts {"data": [...]}, a bare list, or {"models": [...]}. Optional
    per-model metadata (context_length, vision, reasoning, ...) is extracted
    when present; unknown fields are ignored.
    """
    probed_at = probed_at or now_iso()
    out = []
    for item in _extract_data(payload, "openai"):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        out.append(_normalize(item, probed_at, "name"))
    return out


def parse_anthropic(payload, probed_at: str | None = None) -> list[dict]:
    """Anthropic /v1/models -> normalized entries.

    Shape: {"data": [{"type": "model", "id": ..., "display_name": ...,
    "created_at": ...}]}. Also tolerates the OpenAI {"data": [...]} shape.
    """
    probed_at = probed_at or now_iso()
    out = []
    for item in _extract_data(payload, "anthropic"):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        out.append(_normalize(item, probed_at, "display_name"))
    return out


def parse_models(payload, api_type: str = "openai",
                 probed_at: str | None = None) -> list[dict]:
    if (api_type or "openai").lower() == "anthropic":
        return parse_anthropic(payload, probed_at)
    return parse_openai(payload, probed_at)


# ---------------------------------------------------------------------------
# live probe: one GET {base_url}/models, loud failures, key never printed
# ---------------------------------------------------------------------------

def probe(provider_id: str, base_url: str, key_env: str | None = None,
          api_type: str = "openai", key: str | None = None,
          timeout: int = DEFAULT_TIMEOUT, urlopen=None) -> dict:
    """Live GET {base_url}/models and normalize -> summary dict.

    Returns {provider_id, base_url, api_type, key_env, http, count, models,
    probed_at}. Raises ProbeError (naming the fix) on: missing key, network /
    timeout, 401/403 key rejected, other non-200, non-JSON body, unparseable
    shape. The key is only ever placed in the auth header.
    """
    urlopen = urlopen or urllib.request.urlopen
    base_url = (base_url or "").rstrip("/")
    if not base_url:
        raise ProbeError(f"probe {provider_id}: empty base_url — Fix: pass a base_url.")
    api_type = (api_type or "openai").lower()
    key_env = key_env or ""
    key = key if key is not None else load_key(key_env)
    if not key:
        raise ProbeError(
            f"probe {provider_id}: no API key — env '{key_env or '?'}' is empty. "
            f"Fix: set {key_env or 'KEY'} in {ENV_PATH} (or export it), then retry."
        )
    url = f"{base_url}/models"
    headers = dict(UA)
    if api_type == "anthropic":
        headers["x-api-key"] = key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ProbeError(
                f"probe {provider_id}: HTTP {exc.code} — key rejected "
                f"(env '{key_env}'). Fix: refresh the key in {ENV_PATH}."
            ) from None
        raise ProbeError(
            f"probe {provider_id}: HTTP {exc.code} from {url} — unexpected "
            f"endpoint for api_type={api_type}. Fix: verify base_url points at "
            f"the provider root (…/v1 for OpenAI-compatible, api.anthropic.com "
            f"for Claude)."
        ) from None
    except urllib.error.URLError as exc:
        raise ProbeError(
            f"probe {provider_id}: network error reaching {url} "
            f"({exc.reason}). Fix: check connectivity/DNS/VPN, or that "
            f"base_url is correct."
        ) from None
    except socket.timeout:
        raise ProbeError(
            f"probe {provider_id}: timeout after {timeout}s on {url}. "
            f"Fix: check connectivity or raise the timeout."
        ) from None
    except OSError as exc:
        raise ProbeError(
            f"probe {provider_id}: network error reaching {url} ({exc}). "
            f"Fix: check connectivity/DNS/VPN."
        ) from None
    except Exception as exc:  # loud by default: never swallow
        raise ProbeError(
            f"probe {provider_id}: unexpected error on {url} "
            f"({type(exc).__name__}: {exc}). Fix: investigate the endpoint."
        ) from None

    if status != 200:
        raise ProbeError(
            f"probe {provider_id}: HTTP {status} from {url} — expected 200. "
            f"Fix: verify base_url / endpoint shape for api_type={api_type}."
        )
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except ValueError as exc:
        raise ProbeError(
            f"probe {provider_id}: {url} returned non-JSON body ({exc}). "
            f"Fix: the endpoint may not expose /models; check api_type/base_url."
        ) from None

    probed_at = now_iso()
    models = parse_models(payload, api_type, probed_at)
    return {
        "provider_id": provider_id, "base_url": base_url, "api_type": api_type,
        "key_env": key_env, "http": status, "count": len(models),
        "models": models, "probed_at": probed_at,
    }


# ---------------------------------------------------------------------------
# registry: diff + merge (source='live-probe' kept distinct from 'spec')
# ---------------------------------------------------------------------------

def registry_load(data_path: str | None = None) -> dict[str, dict]:
    """Load capabilities.json -> {model_id: record} (models + tombstones).

    Loud ProbeError when the registry file is missing/unreadable — the probe
    needs omni-registry's data to diff against.
    """
    data_path = data_path or REGISTRY_PATH
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise ProbeError(
            f"registry_load: cannot read {data_path} ({exc}). "
            f"Fix: ensure the omni-registry plugin's data/capabilities.json exists."
        ) from None
    except ValueError as exc:
        raise ProbeError(
            f"registry_load: {data_path} is not valid JSON ({exc}). "
            f"Fix: repair the registry file."
        ) from None
    records = {}
    for rec in data.get("models", []):
        records[rec["id"]] = rec
    for rec in data.get("tombstones", []):
        records[rec["id"]] = rec
    return records


def diff_against(probed_models: list[dict],
                 registry: dict[str, dict]) -> dict:
    """Probed entries vs registry records -> {added, removed, changed}.

    added    — id in the probe, not in the registry
    removed  — registry record (status=active, or previously live-probed) not
               in the probe; tombstones are already removed and never re-flagged
    changed  — id in both; probe exposes a context_window int that differs from
               the registry envelope value (F3: reported, never auto-accepted)
    """
    probed_set = {m["id"] for m in probed_models}
    active = {mid for mid, r in registry.items() if r.get("status") == "active"}
    probe_marked = {mid for mid, r in registry.items() if r.get("source") == SOURCE}
    added = sorted(probed_set - set(registry))
    removed = sorted((active | probe_marked) - probed_set)
    changed = []
    by_id = {m["id"]: m for m in probed_models}
    for mid in sorted(probed_set & set(registry)):
        p = by_id[mid].get("context_window")
        r = (registry[mid].get("context_window") or {}).get("value")
        if p is not None and r is not None and p != r:
            changed.append({"id": mid, "from": r, "to": p})
    return {"added": added, "removed": removed, "changed": changed}


def merge_into_registry(probed_models: list[dict], data_path: str | None = None,
                        provider_id: str = "unknown", base_url: str | None = None,
                        now: str | None = None) -> dict:
    """Append/merge probed models into the registry capabilities.json.

    Existing records: tagged with a record-level ``source='live-probe'`` marker
    (distinct from spec-derived records, which carry no such field), gain a
    ``live_probe`` audit block, and provenance.updated_at is bumped.
    Capability envelopes (context_window/capabilities/cost) are NEVER
    overwritten — the live /models list exposes ids, not verified capabilities
    (F3: report, don't auto-accept; NIM-style catalog traps: listing != callable).

    New ids: appended as status='unverified' records (listed live but never
    call-verified) with context_window=null (unknown), source='live-probe'.

    Tombstones are never touched (KLIP-6: frozen history).

    data['sources'] gains one capability-probe entry. Returns a summary dict
    {provider, probed_at, probed, added, updated, registry_total, data_path}.
    """
    data_path = data_path or REGISTRY_PATH
    now_iso_ = now or now_iso()
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise ProbeError(
            f"merge: cannot read registry {data_path} ({exc}). "
            f"Fix: ensure the omni-registry plugin's data/capabilities.json exists."
        ) from None
    except ValueError as exc:
        raise ProbeError(
            f"merge: {data_path} is not valid JSON ({exc}). Fix: repair the registry file."
        ) from None

    models = data.setdefault("models", [])
    by_id = {rec["id"]: rec for rec in models}
    tombstones = {rec["id"] for rec in data.get("tombstones", [])}

    added: list[str] = []
    updated: list[str] = []
    for m in probed_models:
        mid = m["id"]
        rec = by_id.get(mid)
        if rec is None:
            rec = {
                "id": mid,
                "name": m.get("name") or mid,
                "provider": provider_id,
                "status": "unverified",  # listed live, never call-verified
                "context_window": None,  # unknown — /models exposes no limits
                "max_output": None,
                "capabilities": [],
                "capability_sources": {},
                "cost_per_1m": {
                    "input": 0.0, "output": 0.0, "currency": "USD",
                    "source": "estimated",
                    "origin": "unknown — live /models probe exposes no pricing",
                },
                "verified": {"ok": False, "method": "live-probe", "date": now_iso_},
                "provenance": {
                    "primary": "live-probe", "updated_at": now_iso_,
                    "reason": "discovered by capability-probe /models live probe",
                },
                "source": SOURCE,
            }
            models.append(rec)
            by_id[mid] = rec
            added.append(mid)
        elif mid not in tombstones:  # never re-tag frozen history
            rec["source"] = SOURCE
            rec["live_probe"] = {
                "probed_at": m.get("probed_at") or now_iso_,
                "provider": provider_id,
                "base_url": base_url,
                "context_window": m.get("context_window"),
                "vision": m.get("vision"),
                "reasoning": m.get("reasoning"),
            }
            (rec.setdefault("provenance", {}))["updated_at"] = now_iso_
            updated.append(mid)

    data.setdefault("sources", []).append({
        "name": f"capability-probe:{provider_id}",
        "url": f"{base_url}/models" if base_url else None,
        "fetched_at": now_iso_,
        "note": (f"live /models probe via capability-probe — "
                 f"{len(probed_models)} ids, source={SOURCE}"),
    })

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "provider": provider_id, "probed_at": now_iso_, "probed": len(probed_models),
        "added": sorted(added), "updated": sorted(updated),
        "registry_total": len(by_id), "data_path": data_path,
    }


# ---------------------------------------------------------------------------
# provider table: read live from xomni_cli / provider-pool, never hardcoded
# ---------------------------------------------------------------------------

def providers_table() -> list[dict]:
    """[(name, env, base_url, api_type), ...] for /probe resolution.

    Reads the PROVIDERS env-var table from xomni_cli when importable, else the
    provider-pool FREE_CHANNELS (imported by file path — 'provider-pool' is not
    a valid module name). api_type is inferred from the name/base_url
    (Anthropic -> anthropic, everything else OpenAI-compatible).
    """
    try:
        import xomni_cli  # repo-root install (pip install .) provides it
        table = getattr(xomni_cli, "PROVIDERS", None)
        if table:
            out = []
            for name, env, base, _note in table:
                api = "anthropic" if "anthropic" in (name + base).lower() else "openai"
                out.append({"name": name, "env": env, "base_url": base, "api_type": api})
            return out
    except Exception:
        pass
    # fallback: provider-pool channels (same repo, loaded by path)
    try:
        pp_core = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "provider-pool", "core.py",
        )
        if os.path.isfile(pp_core):
            spec = importlib.util.spec_from_file_location("provider_pool_core", pp_core)
            pp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pp)
            return [
                {"name": ch["name"], "env": ch["key_env"].split(",")[0],
                 "base_url": ch["base_url"], "api_type": "openai"}
                for ch in getattr(pp, "FREE_CHANNELS", [])
            ]
    except Exception:
        pass
    return []


def resolve_provider(pid: str, table: list[dict] | None = None) -> dict | None:
    """Match a /probe argument against the provider table.

    Accepts the display name, the env var name, or the base_url (all
    case-insensitive, substring allowed).
    """
    table = table if table is not None else providers_table()
    pid = (pid or "").strip().lower()
    if not pid:
        return None
    for p in table:
        if pid in (p["name"].lower(), p["env"].lower(), p["base_url"].lower()):
            return p
    return None


# ---------------------------------------------------------------------------
# command rendering: /probe <id> and /probe all
# ---------------------------------------------------------------------------

def _render_probe_result(res: dict, diff: dict, merge: dict | None) -> str:
    ids = [m["id"] for m in res["models"]]
    shown = ", ".join(ids[:12]) + (f", … (+{len(ids) - 12} more)" if len(ids) > 12 else "")
    lines = [
        f"/probe {res['provider_id']} — LIVE ✓ HTTP {res['http']} — "
        f"{res['count']} models ({res['base_url']}/models, api_type={res['api_type']})",
        f"  probed {res['probed_at']} · key from env '{res['key_env']}' (never printed)",
    ]
    if merge:
        lines.append(
            f"  merged: +{len(merge['added'])} new, {len(merge['updated'])} tagged "
            f"source=live-probe (registry total {merge['registry_total']})"
        )
    lines.append(
        f"  diff vs registry: {len(diff['added'])} added, {len(diff['removed'])} "
        f"removed, {len(diff['changed'])} changed"
    )
    if diff["added"]:
        lines.append("  added:   " + ", ".join(diff["added"]))
    if diff["removed"]:
        lines.append("  removed: " + ", ".join(diff["removed"]))
    if diff["changed"]:
        lines.append("  changed: " + ", ".join(
            f"{c['id']} ctx {c['from']:,}->{c['to']:,}" for c in diff["changed"]))
    lines.append(f"  models:  {shown}")
    return "\n".join(lines)


def probe_command_text(raw: str, table: list[dict] | None = None,
                       urlopen=None, data_path: str | None = None,
                       do_merge: bool = True) -> str:
    """/probe <provider-id> — probe, merge into the registry, render count+diff."""
    pid = (raw or "").strip()
    table = table if table is not None else providers_table()
    prov = resolve_provider(pid, table)
    if prov is None:
        known = ", ".join(f"{p['name']} ({p['env']})" for p in table) or (
            "none — xomni_cli / provider-pool not importable; Fix: install xomni "
            "or run from the repo root")
        return f"/probe: unknown provider '{pid}'. Known: {known}"
    try:
        res = probe(prov["name"], prov["base_url"], key_env=prov["env"],
                    api_type=prov["api_type"], urlopen=urlopen)
        d = diff_against(res["models"], registry_load(data_path))
        m = (merge_into_registry(res["models"], data_path=data_path,
                                 provider_id=prov["name"],
                                 base_url=prov["base_url"]) if do_merge else None)
    except ProbeError as exc:
        return f"/probe {pid}: {exc}"
    return _render_probe_result(res, d, m)


def probe_all_command_text(table: list[dict] | None = None, urlopen=None,
                           data_path: str | None = None) -> str:
    """/probe all — probe every provider whose key is present; merge + render."""
    table = table if table is not None else providers_table()
    if not table:
        return ("/probe all: no provider table available (xomni_cli / "
                "provider-pool not importable). Fix: install xomni or run from "
                "the repo root.")
    lines = [f"/probe all — {len(table)} providers in table; probing those with a key present"]
    ok = fail = 0
    agg: dict = {"added": [], "removed": [], "changed": []}
    for p in table:
        if not load_key(p["env"]):
            lines.append(f"  — {p['name']}: no key (env '{p['env']}' empty) — skipped")
            continue
        try:
            res = probe(p["name"], p["base_url"], key_env=p["env"],
                        api_type=p["api_type"], urlopen=urlopen)
            d = diff_against(res["models"], registry_load(data_path))
            m = merge_into_registry(res["models"], data_path=data_path,
                                    provider_id=p["name"], base_url=p["base_url"])
            agg["added"] += d["added"]
            agg["removed"] += d["removed"]
            agg["changed"] += d["changed"]
            ok += 1
            lines.append(
                f"  ✓ {p['name']}: LIVE HTTP {res['http']} — {res['count']} models "
                f"(+{len(m['added'])} new, {len(m['updated'])} tagged live-probe)"
            )
        except ProbeError as exc:
            fail += 1
            lines.append(f"  ✗ {p['name']}: {exc}")
    lines.append(
        f"probed {ok} provider(s), {fail} failed — aggregate diff: "
        f"{len(agg['added'])} added, {len(agg['removed'])} removed, "
        f"{len(agg['changed'])} changed"
    )
    return "\n".join(lines)
