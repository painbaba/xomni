"""OmniDesign — XOMNI plugin wiring.

Commands: /design <brief> [--preset=name] [--out=dir]  -> generate artifact
          /design-audit <file.html>                    -> 10-tell slop report
Tool:     design_artifact(brief, preset, out_dir)      -> generate artifact
No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP_DESIGN = (
    "/design <brief> [--preset=xomni-dark|xomni-light|terminal-emerald|plasma-cyan] "
    "[--out=dir]\nGenerate a self-contained single-file HTML artifact from a brief."
)
HELP_AUDIT = "/design-audit <file.html>\nRun the 10-tell slop diagnostic on an HTML file."

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "brief": {"type": "string", "description": "What to design, e.g. 'a landing page for a terminal AI agent'"},
        "preset": {"type": "string", "description": "Token preset: xomni-dark, xomni-light, terminal-emerald, plasma-cyan"},
        "out_dir": {"type": "string", "description": "Output directory (default: ./omni-design-output)"},
    },
    "required": ["brief"],
}


def _parse_args(raw: str) -> tuple:
    """Split brief text from --preset= / --out= flags."""
    preset, out = "xomni-dark", "./omni-design-output"
    parts = (raw or "").split()
    keep = []
    for p in parts:
        if p.startswith("--preset="):
            preset = p.split("=", 1)[1].strip()
        elif p.startswith("--out="):
            out = p.split("=", 1)[1].strip()
        else:
            keep.append(p)
    return " ".join(keep).strip(), preset, out


def _handle_design(raw: str) -> str:
    if not raw.strip():
        return HELP_DESIGN
    brief, preset, out = _parse_args(raw)
    if preset not in core.TOKEN_PRESETS:
        return (f"Unknown preset '{preset}'. Choose from: "
                + ", ".join(sorted(core.TOKEN_PRESETS)))
    try:
        path = core.generate_artifact(brief, preset=preset, out_dir=out)
        surface = core.pick_surface(brief)
        return f"DESIGN OK — {path}\nSurface: {surface} | Preset: {preset}"
    except Exception as exc:
        return f"/design failed: {exc}"


def _handle_audit(raw: str) -> str:
    path = (raw or "").strip()
    if not path:
        return HELP_AUDIT
    try:
        with open(path, encoding="utf-8") as f:
            html = f.read()
    except Exception as exc:
        return f"/design-audit: cannot read {path}: {exc}"
    result = core.slop_score(html)
    lines = [f"SLOP SCORE: {result['score']}/10 (ship threshold: <=2)"]
    if result["tells"]:
        lines.append("Tells fired:")
        lines += [f"  - {t}" for t in result["tells"]]
    else:
        lines.append("No tells fired.")
    lines.append("Repair register: " + (", ".join(result["repair"]) if result["repair"] else "none"))
    return "\n".join(lines)


def _tool_design_artifact(params: dict) -> str:
    try:
        brief = (params or {}).get("brief") or ""
        preset = (params or {}).get("preset") or "xomni-dark"
        out = (params or {}).get("out_dir") or "./omni-design-output"
        path = core.generate_artifact(brief, preset=preset, out_dir=out)
        return f"DESIGN OK — {path} (surface: {core.pick_surface(brief)})"
    except Exception as exc:
        return f"design_artifact failed: {exc}"


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command("design", handler=_handle_design,
                         description="Generate a self-contained HTML artifact from a brief (Omni Design).",
                         args_hint="<brief> [--preset=...] [--out=...]")
    ctx.register_command("design-audit", handler=_handle_audit,
                         description="Run the 10-tell slop diagnostic on an HTML file.",
                         args_hint="<file.html>")
    ctx.register_tool("design_artifact", toolset="creative", schema=TOOL_SCHEMA,
                      handler=_tool_design_artifact,
                      description="Generate a self-contained single-file HTML artifact (landing/deck/component-lab) from a brief using the Omni Design token system.")
