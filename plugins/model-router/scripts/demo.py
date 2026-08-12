"""model-router demo — automatic per-task routing + telemetry, at the command
level (drives the same handlers Hermes wires to /route).

Run:  cd plugins/model-router && python scripts/demo.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load the plugin package __init__.py as a module (hyphenated dir name can't
# be imported normally) — same pattern codebase-index tests use.
spec = importlib.util.spec_from_file_location(
    "model_router_plugin", os.path.join(_PLUGIN_DIR, "__init__.py"))
mod = importlib.util.module_from_spec(spec)
mod.__path__ = [_PLUGIN_DIR]
sys.modules["model_router_plugin"] = mod
spec.loader.exec_module(mod)

handle = mod._handle_route  # what Hermes calls for /route <args>

print("=" * 72)
print("DEMO 1 — automatic per-task routing (real omni-registry capabilities)")
print("=" * 72)
for prompt in (
    "why does my backtest lose money?",
    "debug this traceback and find the root cause",
    "read the numbers from this screenshot and OCR the table",
    "summarize this article in 3 bullets",
    "process this entire codebase, keep full context",
    "hello there",
):
    print("\n>>> /route %s" % prompt)
    print(handle(prompt))

print("\n" + "=" * 72)
print("DEMO 2 — telemetry: record routed calls (command-based, zero hooks)")
print("=" * 72)
print("\n>>> /route record deepseek-v4-pro 4100 0 reasoning")
print(handle("record deepseek-v4-pro 4100 0 reasoning"))
print("\n>>> /route record minimax-m3 5200 0 vision")
print(handle("record minimax-m3 5200 0 vision"))
print("\n>>> /route record deepseek-chat 900 0.00082 quick")
print(handle("record deepseek-chat 900 0.00082 quick"))

print("\n" + "=" * 72)
print("DEMO 3 — /route telemetry (last 10 calls: model, ms, $, task type)")
print("=" * 72)
print("\n>>> /route telemetry")
print(handle("telemetry"))
