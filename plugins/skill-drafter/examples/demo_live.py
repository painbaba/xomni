"""U-SURF-2 LIVE DEMO — full pipeline + cross-profile sync dry-run (real state)."""
import importlib.util
import os
import sys

PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
spec = importlib.util.spec_from_file_location("skill_drafter_demo",
                                              os.path.join(PLUGIN_DIR, "__init__.py"))
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, PLUGIN_DIR)
spec.loader.exec_module(mod)

print("#" * 78)
print("# DEMO 1: /skill from-session <REAL session id> — full lifecycle")
print("#" * 78)
out = mod._handle_from_session("20260812_182545_d22b70")
print(out)

print()
print("#" * 78)
print("# DEMO 2: /skill sync --dry-run (host <-> xomni profile, no writes)")
print("#" * 78)
print(mod._handle_sync("--dry-run"))
