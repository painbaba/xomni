"""skill-drafter demo — draft the synthetic 6-call transcript, save to a
temp skills dir, and mirror the /skill draft -> /skill save command flow.

Run: cd plugins/skill-drafter && python examples/demo_draft.py
"""
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(HERE)
sys.path.insert(0, PLUGIN_DIR)
import core  # noqa: E402

FIXTURE = os.path.join(HERE, "session-6calls.jsonl")

# --- 1. core draft ---------------------------------------------------------
transcript = core.parse_transcript_file(FIXTURE)
draft = core.draft_skill(transcript)
assert draft is not None, core.draft_reason()
print(f"=== DRAFT {draft['name']} — {draft['success_calls']} successful "
      f"tool calls (of {draft['tool_calls']} total)")
print(draft["skill_md"])

# --- 2. command flow (/skill draft -> /skill save) -------------------------
spec = importlib.util.spec_from_file_location(
    "skill_drafter_demo", os.path.join(PLUGIN_DIR, "__init__.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("=== /skill draft examples/session-6calls.jsonl")
print(mod._handle_draft(FIXTURE).split("\n\n", 1)[0])

tmp = tempfile.mkdtemp(prefix="skill-drafter-demo-")
print("\n=== /skill save set-up-python-package --target=<tmp> --category=devops")
print(mod._handle_save(f"set-up-python-package --target={tmp} --category=devops"))

dest = os.path.join(tmp, "devops", "set-up-python-package", "SKILL.md")
assert os.path.isfile(dest), "saved SKILL.md missing!"
demo_md = os.path.join(HERE, "demo-SKILL.md")
shutil.copy(dest, demo_md)
print(f"\nDemo SKILL.md mirrored to: {demo_md}")
print(f"Temp skills dir: {tmp}")
print(f"Saved file verified: {dest}")
