# omni-design

Omni Design: generate premium self-contained HTML artifacts from a brief
(`/design`) and audit any HTML against the 10-tell slop diagnostic
(`/design-audit`). Zero hooks, zero per-turn cost.

**What it does:** turns a one-line brief into a single-file HTML artifact
(landing / deck / component-lab template picked from brief keywords) using
one of **4 token presets** (`xomni-dark`, `xomni-light`, `terminal-emerald`,
`plasma-cyan`) and a surface picker (Monitor / Configure / Compare / Explore /
Operate / Decide-Learn); `/design-audit` scores HTML 0-10 across 10 slop
tells (gradients, generic indigo, tile grids, accent rails, blur, monument
stats, icon toppers, centered stacks, default type, wrong surface) with a
ship threshold of ≤2 and a repair register.

**Commands:** `/design <brief> [--preset=...] [--out=...]` ·
`/design-audit <file.html>` — **Tool:** `design_artifact(brief, preset,
out_dir)` (toolset `creative`)

**Speed posture:** no hooks — no LLM calls, requests, or subprocess;
pure-stdlib generation (<1 s/turn).

**Config:** none (presets + output dir are command flags; default out
`./omni-design-output`). Templates live in `templates/`.

```bash
cd plugins/omni-design && python -m unittest tests.test_core -v
```
