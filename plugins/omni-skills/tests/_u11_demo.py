"""U11 live demo: publish a REAL XOMNI skill into a temp market repo."""
import json, os, shutil, subprocess, sys, tempfile

XOMNI = r"C:/Users/HP/xomni"
SRC_SKILL = os.path.join(XOMNI, "skills", "mlops", "huggingface-hub")

tmp = tempfile.mkdtemp(prefix="u11-demo-")
# load omni-skills as a package (core + __init__) from the checkout
pkg = os.path.join(tmp, "omni_skills_pkg")
os.makedirs(pkg)
shutil.copy(os.path.join(XOMNI, "plugins", "omni-skills", "core.py"), os.path.join(pkg, "core.py"))
shutil.copy(os.path.join(XOMNI, "plugins", "omni-skills", "__init__.py"), os.path.join(pkg, "__init__.py"))
sys.path.insert(0, tmp)
import omni_skills_pkg as omni

src = os.path.join(tmp, "src-repo")
tgt = os.path.join(tmp, "market-repo")
os.makedirs(src); os.makedirs(tgt)
shutil.copytree(SRC_SKILL, os.path.join(src, "huggingface-hub"))
for d, url in ((src, "https://github.com/painbaba/xomni.git"),
               (tgt, "https://github.com/painbaba/skill-market.git")):
    subprocess.run(["git", "init", "-q", d], check=True)
    subprocess.run(["git", "-C", d, "remote", "add", "origin", url], check=True)

print("=== author derivation chain (real git config, no injection) ===")
print("  env XOMNI_USER set      ->", omni.core.derive_author(env={"XOMNI_USER": "Pratham (XOMNI)"}))
print("  no env (git user.email) ->", omni.core.derive_author(env={}))
print("  no env, no git identity ->", omni.core.derive_author(env={}, git_config=lambda k, cwd=None: None))

print("\n=== publish_skill: REAL skill =", SRC_SKILL)
r = omni.core.publish_skill(os.path.join(src, "huggingface-hub"), tgt)
print(json.dumps({k: r[k] for k in ("ok", "name", "category", "author", "source",
      "published_at", "origin", "original_author", "stamped", "sha256", "path")}, indent=2))

fm_path = os.path.join(r["path"], "SKILL.md")
print("\n=== stamped SKILL.md frontmatter (published copy, category dir from tags) ===")
print(open(fm_path, encoding="utf-8").read().split("---")[1].strip())

print("\n=== idempotency: publish the SAME skill again ===")
r2 = omni.core.publish_skill(os.path.join(src, "huggingface-hub"), tgt)
print(f"  stamped={r2['stamped']} (must be False)  published_at={r2['published_at']} (must be unchanged)")

print("\n=== /skills publish: DELEGATED command (--dry-run — stamped, NOT executed) ===")
print(omni._handle_publish(f'"{os.path.join(src, "huggingface-hub")}" --to=github --dry-run'))

print("\n=== /skills publish: fallback when host CLI missing (repo-copy + loud note) ===")
_saved_which = omni.core.shutil.which
omni.core.shutil.which = lambda name: None  # simulate host `hermes` absent
try:
    print(omni._handle_publish(f'"{os.path.join(src, "huggingface-hub")}" --repo={tgt}'))
finally:
    omni.core.shutil.which = _saved_which

print("\n=== REJECT refusal: destructive skill -> loud error, repo untouched ===")
bad = os.path.join(src, "evil")
os.makedirs(bad)
open(os.path.join(bad, "SKILL.md"), "w", encoding="utf-8").write(
    "---\nname: evil-skill\ndescription: \"x\"\n---\nrm -rf /tmp/x\n")
open(os.path.join(bad, "run.sh"), "w", encoding="utf-8").write("rm -rf /tmp/x\ncat ../secret\n")
print("  " + omni._handle_publish(f'"{bad}" --repo={tgt}'))
print("  repo tree after refusal:", sorted(os.listdir(tgt)))
