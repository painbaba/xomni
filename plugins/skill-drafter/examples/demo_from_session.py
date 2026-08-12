"""U-SURF-2 live demo probe — /skill from-session <id> --no-save on real sessions."""
import importlib.util
import os
import sys

PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
spec = importlib.util.spec_from_file_location("skill_drafter_demo",
                                              os.path.join(PLUGIN_DIR, "__init__.py"))
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, PLUGIN_DIR)
spec.loader.exec_module(mod)

for sid in sys.argv[1:]:
    print("=" * 78)
    out = mod._handle_from_session(sid + " --no-save")
    # trim the full SKILL.md body for the probe — show head only
    head, sep, _tail = out.partition("--- SKILL.md ---")
    body_head = ""
    if sep:
        _b, _s, rest = out.partition("--- SKILL.md ---")
        body, _s2, tail = rest.partition("\n---")
        body_head = body.splitlines()[:6]
        tail_lines = tail.strip().splitlines()
    print(head.rstrip())
    if sep:
        print("--- SKILL.md --- (first 6 lines)")
        print("\n".join(body_head))
        print("...")
        print("\n".join(tail_lines))
