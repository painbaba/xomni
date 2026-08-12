"""Live demo: draft_last_session + /skill draft-last + /skill save --yes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core  # noqa: E402
import __init__ as plugin  # noqa: E402 (bare-file load, same as tests)

print("=" * 72)
print("DEMO 1: core.draft_last_session()  (real host session store)")
print("=" * 72)
result = core.draft_last_session()
print("ok:", result.get("ok"))
print("session_id:", result.get("session_id"))
print("name:", result.get("name"))
print("success_calls:", result.get("success_calls"))
print("tool_calls:", result.get("tool_calls"))
print("steps:", len(result.get("steps", [])))
print("skill_md head:", repr((result.get("skill_md") or "")[:120]))

print()
print("=" * 72)
print("DEMO 2: /skill draft-last  (handler wiring)")
print("=" * 72)
out = plugin._handle_draft_last("")
first_line = out.splitlines()[0]
print(first_line)
print("...")
print("tail:", out.splitlines()[-1])

print()
print("=" * 72)
print("DEMO 3: /skill save <name> --yes  -> host skills dir (real write)")
print("=" * 72)
saved = plugin._handle_save(f"{result['name']} --yes")
print(saved)
dest = saved.split("->")[-1].split("(")[0].strip()
sk = os.path.join(dest, "SKILL.md")
print("SKILL.md exists:", os.path.isfile(sk), "| size:", os.path.getsize(sk) if os.path.isfile(sk) else 0)
