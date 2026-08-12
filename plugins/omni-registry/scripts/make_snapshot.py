"""Generate data/models.snapshot.json — the item-01 baseline snapshot.

Captures the registry as of the previous refresh cycle (2026-08-11, one day
before capabilities.json's generated_at). Three documented deltas vs the
current registry make /models2 diff meaningful:

  * deepseek-v4-flash context_window = 131072  (old curated value, refuted by
    research F3 — README "deepseek-v4-flash context correction")
  * kimi-k2  status = active                    (decommissioned this cycle,
  * glm-4.6  status = active                     tombstoned in current registry)

Every other model carries its current value — the snapshot is the "what we
knew at last refresh" pin, not a fiction.

Per-model snapshot fields: {status, context_window, max_output} — the exact
field set conflict_report() already diffs against (slug/ctx/out precedent).
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # plugin root
REG = os.path.join(HERE, "data", "capabilities.json")
OUT = os.path.join(HERE, "data", "models.snapshot.json")

with open(REG, encoding="utf-8") as f:
    data = json.load(f)

models: dict[str, dict] = {}
for rec in data["models"] + data["tombstones"]:
    mid = rec["id"]
    snap = {
        "status": rec["status"],
        "context_window": (rec.get("context_window") or {}).get("value"),
    }
    mo = rec.get("max_output")
    if mo and mo.get("value") is not None:
        snap["max_output"] = mo["value"]
    models[mid] = snap

# --- documented pre-refresh deltas (see module docstring) ---
models["deepseek-v4-flash"]["context_window"] = 131072  # pre-correction (F3)
for tid in ("kimi-k2", "glm-4.6"):
    models[tid]["status"] = "active"  # decommissioned after this capture

snapshot = {
    "schema_version": "1.0.0",
    "captured_at": "2026-08-11T00:00:00Z",
    "source": "opencode-zen gateway /models refresh pin (KLIP-6-style)",
    "models": dict(sorted(models.items())),
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"wrote {OUT}: {len(models)} models, captured_at={snapshot['captured_at']}")
