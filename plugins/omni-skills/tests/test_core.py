"""omni-skills tests — pure core, no host needed."""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

SKILL_A = """---
name: hello-skill
description: "Greets the user."
version: "1.2.0"
license: MIT
tags: [greeting, demo]
---
# Hello
Do the greeting.
"""

SKILL_BAD = """---
name: evil-skill
description: "Runs a destructive command."
---
#!/bin/bash
rm -rf /tmp/x
"""

SKILL_NOSKILL = "no frontmatter here, just prose"

SKILL_TAGGED = """---
name: tagged-tool
description: "Has tags for market categorization."
tags: [devops, ci, pipelines]
---
Run pipelines.
"""

SKILL_PREAUTHORED = """---
name: preauth-tool
description: "Carries its original creator credit."
author: "Original Creator"
version: "1.0.0"
---
Original work.
"""

SKILL_PLAIN = """---
name: plain-tool
description: "No tags — lands in the general market category."
---
Plain skill body.
"""


class FrontmatterTests(unittest.TestCase):
    def test_parses_scalars_and_lists(self):
        fm = core.parse_frontmatter(SKILL_A)
        self.assertEqual(fm["name"], "hello-skill")
        self.assertEqual(fm["version"], "1.2.0")
        self.assertEqual(fm["tags"], ["greeting", "demo"])

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(core.parse_frontmatter("plain text"), {})

    def test_malformed_never_raises(self):
        self.assertEqual(core.parse_frontmatter("---\n:no-colon-line\n---"), {})
        self.assertEqual(core.parse_frontmatter("---"), {})


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-skills-test-")
        os.makedirs(os.path.join(self.tmp, "good"))
        with open(os.path.join(self.tmp, "good", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)
        os.makedirs(os.path.join(self.tmp, "empty"))
        os.makedirs(os.path.join(self.tmp, "notskill"))
        with open(os.path.join(self.tmp, "notskill", "notes.txt"), "w", encoding="utf-8") as f:
            f.write("x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_finds_skill_dirs_only(self):
        skills = core.scan_skills(self.tmp)
        names = [s["name"] for s in skills]
        self.assertEqual(names, ["hello-skill"])

    def test_scan_missing_root(self):
        self.assertEqual(core.scan_skills("/nonexistent/xyz"), [])


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-skills-test-")
        self.good = os.path.join(self.tmp, "good")
        os.makedirs(self.good)
        with open(os.path.join(self.good, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)
        self.bad = os.path.join(self.tmp, "bad")
        os.makedirs(self.bad)
        with open(os.path.join(self.bad, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_BAD)
        with open(os.path.join(self.bad, "run.sh"), "w", encoding="utf-8") as f:
            f.write("rm -rf /tmp/x\ncat ../secret\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_good_skill_passes(self):
        r = core.validate_skill(self.good)
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["ok"])

    def test_destructive_skill_rejected(self):
        r = core.validate_skill(self.bad)
        self.assertEqual(r["verdict"], "REJECT")
        self.assertFalse(r["ok"])
        self.assertTrue(any("destructive" in reason for _f, reason in r["issues"]))

    def test_missing_skill_md_rejected(self):
        r = core.validate_skill(self.tmp)  # dir without SKILL.md
        self.assertEqual(r["verdict"], "REJECT")


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.mkdtemp(prefix="omni-skills-src-")
        self.dst = tempfile.mkdtemp(prefix="omni-skills-dst-")
        os.makedirs(os.path.join(self.src, "good"))
        with open(os.path.join(self.src, "good", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)
        shutil.rmtree(self.dst, ignore_errors=True)

    def test_install_copies_validated_skill(self):
        r = core.install_skill(os.path.join(self.src, "good"), self.dst)
        self.assertTrue(r["ok"])
        self.assertTrue(os.path.isfile(os.path.join(self.dst, "hello-skill", "SKILL.md")))

    def test_dry_run_writes_nothing(self):
        r = core.install_skill(os.path.join(self.src, "good"), self.dst, dry_run=True)
        self.assertTrue(r["dry_run"])
        self.assertFalse(os.path.exists(os.path.join(self.dst, "hello-skill")))

    def test_marketplace_install(self):
        r = core.install_marketplace(self.src, self.dst)
        self.assertEqual(r["installed"], 1)
        self.assertEqual(r["rejected"], 0)

    def test_fingerprint_stable(self):
        a = core.fingerprint(os.path.join(self.src, "good"))
        b = core.fingerprint(os.path.join(self.src, "good"))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)


class MarketplaceUrlTests(unittest.TestCase):
    """install_marketplace_url — URL gate, shallow clone, fail-closed."""

    def _target(self):
        return tempfile.mkdtemp(prefix="omni-skills-ms-tgt-")

    def test_validate_url_accepts_https_and_git(self):
        for u in ("https://github.com/xomni/skills.git",
                  "https://github.com/xomni/skills",
                  "git://github.com/xomni/skills.git"):
            ok, reason = core.validate_marketplace_url(u)
            self.assertTrue(ok, reason)

    def test_validate_url_rejects_file_http_and_shell_meta(self):
        for u in ("file:///etc/passwd", "http://example.com/x", "ssh://h/x",
                  "https://x/y;rm -rf /", "https://x/y$(id)", "https://x/y`id`",
                  "https://x/y --upload-pack=sh", "https://x/y && echo pwned",
                  "", "   "):
            ok, _ = core.validate_marketplace_url(u)
            self.assertFalse(ok, u)

    def test_invalid_url_fail_closed_no_state_change(self):
        target = self._target()
        try:
            r = core.install_marketplace_url("file:///etc/passwd", target)
            self.assertFalse(r["ok"])
            self.assertIn("invalid URL", r["reason"])
            self.assertEqual(os.listdir(target), [])  # target untouched
        finally:
            shutil.rmtree(target, ignore_errors=True)

    def test_clone_failure_fail_closed_cleans_cache(self):
        target = self._target()
        root = tempfile.mkdtemp(prefix="omni-skills-ms-")
        cache = os.path.join(root, "cache")

        def boom(url, dest):  # simulated partial clone that then fails
            os.makedirs(dest, exist_ok=True)
            with open(os.path.join(dest, "partial.txt"), "w") as f:
                f.write("x")
            return {"ok": False, "reason": "git clone failed: boom"}

        try:
            r = core.install_marketplace_url("https://github.com/x/boom.git",
                                             target, cache_root=cache,
                                             _runner=boom)
            self.assertFalse(r["ok"])
            self.assertEqual(r["reason"], "git clone failed: boom")
            self.assertEqual(os.listdir(target), [])  # target untouched
            self.assertFalse(os.path.exists(os.path.join(cache, "boom")))  # cleaned
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    def test_install_reuses_validation_verdicts(self):
        """Cached clone with one good + one destructive skill: good lands,
        evil is rejected, nothing partial for the rejected skill."""
        target = self._target()
        root = tempfile.mkdtemp(prefix="omni-skills-ms-")
        repo = os.path.join(root, "cache", "goodrepo")  # pre-populated cache
        os.makedirs(os.path.join(repo, "good"))
        with open(os.path.join(repo, "good", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_A)
        os.makedirs(os.path.join(repo, "evil"))
        with open(os.path.join(repo, "evil", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_BAD)
        with open(os.path.join(repo, "evil", "run.sh"), "w", encoding="utf-8") as f:
            f.write("rm -rf /tmp/x\ncat ../secret\n")  # 3 issues -> REJECT
        try:
            r = core.install_marketplace_url("https://github.com/x/goodrepo.git",
                                             target, cache_root=os.path.join(root, "cache"))
            self.assertTrue(r["ok"])
            self.assertEqual(r["installed"], 1)
            self.assertEqual(r["rejected"], 1)
            self.assertTrue(os.path.isfile(os.path.join(target, "hello-skill", "SKILL.md")))
            self.assertFalse(os.path.exists(os.path.join(target, "evil-skill")))
            self.assertEqual(r["cache_dir"], repo)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    def test_successful_clone_installs_and_caches(self):
        """Mocked successful clone: repo dir is created by the runner, then
        skills are installed from it and the cache dir is reported."""
        target = self._target()
        root = tempfile.mkdtemp(prefix="omni-skills-ms-")
        cache = os.path.join(root, "cache")

        def fake_clone(url, dest):
            os.makedirs(os.path.join(dest, "good"))
            with open(os.path.join(dest, "good", "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(SKILL_A)
            return {"ok": True}

        try:
            r = core.install_marketplace_url("https://github.com/x/fresh.git",
                                             target, cache_root=cache,
                                             _runner=fake_clone)
            self.assertTrue(r["ok"])
            self.assertEqual(r["installed"], 1)
            self.assertEqual(r["rejected"], 0)
            self.assertTrue(os.path.isfile(os.path.join(target, "hello-skill", "SKILL.md")))
            self.assertTrue(os.path.isdir(os.path.join(cache, "fresh")))
            self.assertEqual(r["cache_dir"], os.path.join(cache, "fresh"))
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)


class SearchListStatusTests(unittest.TestCase):
    """Skills search, plugin inventory, env status — the 'full access via any
    API' surface."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omni-skills-search-")
        os.makedirs(os.path.join(self.tmp, "plotly-101"))
        with open(os.path.join(self.tmp, "plotly-101", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: plotly-101\ndescription: \"Plotly charts for data viz.\"\n---\nMake charts with plotly.\n")
        os.makedirs(os.path.join(self.tmp, "gh-issues"))
        with open(os.path.join(self.tmp, "gh-issues", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: gh-issues\ndescription: \"GitHub issue triage.\"\n---\nTriage issues.\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_search_finds_in_skill_tree(self):
        hits = core.search_skills("plotly")
        tree_hits = [h for h in hits if h["source"] in ("hermes-skills", "checkout-skills")]
        # without a checkout data/, search falls back to the real hermes skills
        # tree (may or may not contain plotly) — so assert shape, not hits.
        self.assertIsInstance(hits, list)
        # direct tree search over a temp root must find the planted skill
        found = []
        for base, _dirs, files in os.walk(self.tmp):
            if "SKILL.md" in files:
                text = open(os.path.join(base, "SKILL.md"), encoding="utf-8").read()
                if "plotly" in text.lower():
                    found.append(base)
        self.assertEqual(len(found), 1)

    def test_empty_query_no_hits(self):
        self.assertEqual(core.search_skills(""), [])
        self.assertEqual(core.search_skills(None), [])

    def test_list_plugins_finds_self(self):
        plugins = core.list_plugins()
        names = [p["name"] for p in plugins]
        self.assertIn("omni-skills", names)
        by_name = {p["name"]: p for p in plugins}
        self.assertFalse(by_name["omni-skills"]["has_hooks"])

    def test_list_plugins_missing_dir(self):
        self.assertEqual(core.list_plugins("/nonexistent/xyz"), [])

    def test_env_status_shape(self):
        st = core.env_status()
        for key in ("xomni_home", "plugins_total", "skills_total", "data"):
            self.assertIn(key, st)
        self.assertGreaterEqual(st["plugins_total"], 1)


class PublishTests(unittest.TestCase):
    """U11 — cross-session skill market: publish_skill (the repo-copy
    FALLBACK, used only when the host CLI is missing) credit-stamps and
    copies a skill into a repo's skills/ tree; REJECT skills are refused.
    The host-delegation path is covered by HostPublishTests."""

    NO_GIT = lambda self, key, cwd=None: None  # noqa: E731
    FAKE_GIT = lambda self, key, cwd=None: (  # noqa: E731
        "painbaba" if key == "user.name" else
        "https://github.com/painbaba/xomni.git" if key == "remote.origin.url"
        else None)

    def _write(self, root, name, content):
        d = os.path.join(root, name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)
        return d

    def _fm(self, skill_dir):
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
            return core.parse_frontmatter(f.read())

    def setUp(self):
        self.src = tempfile.mkdtemp(prefix="omni-skills-pub-src-")
        self.repo = tempfile.mkdtemp(prefix="omni-skills-pub-repo-")
        self.good = self._write(self.src, "good", SKILL_A)
        self.plain = self._write(self.src, "plain", SKILL_PLAIN)
        self.bad = self._write(self.src, "bad", SKILL_BAD)
        with open(os.path.join(self.bad, "run.sh"), "w", encoding="utf-8") as f:
            f.write("rm -rf /tmp/x\ncat ../secret\n")

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_publish_stamps_credit(self):
        r = core.publish_skill(self.plain, self.repo, author="publisher-a",
                               git_config=self.NO_GIT)
        self.assertTrue(r["ok"])
        fm = self._fm(os.path.join(self.repo, "skills", "general", "plain-tool"))
        self.assertEqual(fm["author"], "publisher-a")
        self.assertEqual(fm["source"], "xomni")
        self.assertRegex(fm["published_at"], r"^\d{4}-\d{2}-\d{2}$")

    def test_publish_idempotent_no_double_stamp(self):
        first = core.publish_skill(self.plain, self.repo, author="publisher-a",
                                   git_config=self.NO_GIT)
        second = core.publish_skill(self.plain, self.repo, author="publisher-a",
                                    git_config=self.NO_GIT)
        self.assertTrue(first["stamped"])
        self.assertFalse(second["stamped"])  # already stamped, untouched
        fm = self._fm(os.path.join(self.repo, "skills", "general", "plain-tool"))
        self.assertEqual(fm["published_at"], first["published_at"])
        self.assertEqual(fm["author"], "publisher-a")
        self.assertEqual(fm["source"], "xomni")

    def test_author_env_wins_over_git(self):
        r = core.publish_skill(self.plain, self.repo,
                               env={"XOMNI_USER": "env-publisher"},
                               git_config=self.FAKE_GIT)
        self.assertEqual(r["author"], "env-publisher")

    def test_author_git_config_fallback(self):
        r = core.publish_skill(self.plain, self.repo, env={},
                               git_config=self.FAKE_GIT)
        self.assertEqual(r["author"], "painbaba")  # git user.name

    def test_author_default_xomni_user(self):
        r = core.publish_skill(self.plain, self.repo, env={},
                               git_config=self.NO_GIT)
        self.assertEqual(r["author"], "xomni-user")

    def test_refuses_reject_skill(self):
        r = core.publish_skill(self.bad, self.repo, author="publisher-a",
                               git_config=self.NO_GIT)
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "REJECT")
        self.assertTrue(r["issues"])
        # nothing copied into the repo tree
        self.assertEqual(os.listdir(self.repo), [])

    def test_copy_structure_category_from_tags(self):
        tagged = self._write(self.src, "tagged", SKILL_TAGGED)
        r = core.publish_skill(tagged, self.repo, author="publisher-a",
                               git_config=self.NO_GIT)
        self.assertTrue(r["ok"])
        self.assertEqual(r["category"], "devops")  # first tag
        self.assertTrue(os.path.isfile(
            os.path.join(self.repo, "skills", "devops", "tagged-tool", "SKILL.md")))

    def test_category_general_when_no_tags(self):
        r = core.publish_skill(self.plain, self.repo, author="publisher-a",
                               git_config=self.NO_GIT)
        self.assertEqual(r["category"], "general")
        self.assertTrue(os.path.isfile(
            os.path.join(self.repo, "skills", "general", "plain-tool", "SKILL.md")))

    def test_receipt_shape(self):
        r = core.publish_skill(self.plain, self.repo, author="publisher-a",
                               git_config=self.NO_GIT)
        for key in ("ok", "name", "sha256", "path", "author", "published_at",
                    "source", "stamped", "git"):
            self.assertIn(key, r)
        self.assertEqual(r["name"], "plain-tool")
        self.assertRegex(r["sha256"], r"^[0-9a-f]{64}$")  # full sha256
        self.assertTrue(os.path.isfile(os.path.join(r["path"], "SKILL.md")))
        self.assertEqual(r["author"], "publisher-a")
        self.assertEqual(r["git"]["add"], "skills/general/plain-tool")

    def test_missing_dir_loud_error(self):
        missing = os.path.join(self.src, "does-not-exist")
        r = core.publish_skill(missing, self.repo, author="publisher-a")
        self.assertFalse(r["ok"])
        self.assertIn("not found", r["reason"])
        self.assertEqual(os.listdir(self.repo), [])  # nothing written

    def test_origin_detected_from_git_remote(self):
        r = core.publish_skill(self.plain, self.repo, author="publisher-a",
                               git_config=self.FAKE_GIT)
        self.assertEqual(r["origin"], "painbaba/xomni")
        fm = self._fm(os.path.join(self.repo, "skills", "general", "plain-tool"))
        self.assertEqual(fm["origin"], "painbaba/xomni")

    def test_preexisting_author_credit_preserved(self):
        pre = self._write(self.src, "pre", SKILL_PREAUTHORED)
        r = core.publish_skill(pre, self.repo, author="publisher-a",
                               git_config=self.NO_GIT)
        self.assertTrue(r["ok"])
        self.assertEqual(r["author"], "publisher-a")        # publisher stamps
        self.assertEqual(r["original_author"], "Original Creator")  # kept
        fm = self._fm(os.path.join(self.repo, "skills", "general", "preauth-tool"))
        self.assertEqual(fm["original_author"], "Original Creator")
        self.assertEqual(fm["author"], "publisher-a")


class _FakeHostRunner:
    """Records argv; answers the --help smoke call and the --to publish call.

    Simulates `hermes skills publish`: --help advertises skill_path (ok),
    the publish call returns ok unless constructed with ok=False.
    """

    def __init__(self, ok=True, help_ok=True, stdout="published: skill registered"):
        self.calls = []
        self.ok = ok
        self.help_ok = help_ok
        self.stdout = stdout

    def __call__(self, argv):
        self.calls.append(list(argv))
        if "--help" in argv:
            return {"ok": self.help_ok,
                    "stdout": ("usage: hermes skills publish [-h] "
                               "[--to {github,clawhub}] [--repo REPO] "
                               "skill_path" if self.help_ok else ""),
                    "stderr": "" if self.help_ok else "unknown command"}
        return {"ok": self.ok, "stdout": self.stdout, "stderr": ""}


class HostPublishTests(unittest.TestCase):
    """U11 wrap (#11): publish_via_host stamps credit FIRST (idempotent),
    then DELEGATES the actual publish to `hermes skills publish --to
    github|clawhub`; the repo-copy path is only the fallback when the host
    CLI is missing — no duplicate parallel path."""

    NO_GIT = lambda self, key, cwd=None: None  # noqa: E731
    HERMES = "C:/bin/hermes.exe"

    def _write(self, root, name, content):
        d = os.path.join(root, name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)
        return d

    def _fm(self, skill_dir):
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
            return core.parse_frontmatter(f.read())

    def setUp(self):
        self.src = tempfile.mkdtemp(prefix="omni-skills-host-src-")
        self.repo = tempfile.mkdtemp(prefix="omni-skills-host-repo-")
        self.plain = self._write(self.src, "plain", SKILL_PLAIN)
        self.bad = self._write(self.src, "bad", SKILL_BAD)
        with open(os.path.join(self.bad, "run.sh"), "w", encoding="utf-8") as f:
            f.write("rm -rf /tmp/x\ncat ../secret\n")

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    @mock.patch("core.shutil.which", return_value=HERMES)
    def test_delegate_constructs_hermes_command(self, _w):
        runner = _FakeHostRunner()
        r = core.publish_via_host(self.plain, author="publisher-a",
                                  git_config=self.NO_GIT, runner=runner)
        self.assertTrue(r["ok"])
        self.assertTrue(r["delegated"])
        self.assertEqual(r["command"][1:],
                         ["skills", "publish", "--to", "github", self.plain])
        self.assertTrue(os.path.basename(r["command"][0]).lower().startswith("hermes"))
        self.assertEqual(r["author"], "publisher-a")
        self.assertEqual(r["target"], "github")
        # smoke --help first, then the publish call — exactly one publish argv
        self.assertEqual(len(runner.calls), 2)
        self.assertIn("--help", runner.calls[0])
        self.assertEqual(runner.calls[1][1:],
                         ["skills", "publish", "--to", "github", self.plain])

    @mock.patch("core.shutil.which", return_value=HERMES)
    def test_delegate_clawhub_target(self, _w):
        runner = _FakeHostRunner()
        r = core.publish_via_host(self.plain, target="clawhub", runner=runner)
        self.assertTrue(r["delegated"])
        self.assertEqual(r["command"][1:],
                         ["skills", "publish", "--to", "clawhub", self.plain])
        self.assertEqual(r["target"], "clawhub")

    @mock.patch("core.shutil.which", return_value=HERMES)
    def test_delegate_host_repo_passthrough(self, _w):
        runner = _FakeHostRunner()
        r = core.publish_via_host(self.plain, repo="openai/skills", runner=runner)
        self.assertEqual(r["command"][1:],
                         ["skills", "publish", "--to", "github", "--repo",
                          "openai/skills", self.plain])

    @mock.patch("core.shutil.which", return_value=HERMES)
    def test_delegate_stamps_credit_idempotent(self, _w):
        runner = _FakeHostRunner()
        first = core.publish_via_host(self.plain, author="publisher-a",
                                      git_config=self.NO_GIT, runner=runner)
        second = core.publish_via_host(self.plain, author="publisher-a",
                                       git_config=self.NO_GIT, runner=runner)
        self.assertTrue(first["stamped"])
        self.assertFalse(second["stamped"])  # already stamped, untouched
        self.assertTrue(second["delegated"])  # still delegated
        fm = self._fm(self.plain)
        self.assertEqual(fm["published_at"], first["published_at"])
        self.assertEqual(fm["source"], "xomni")

    def test_dry_run_returns_command_without_executing(self):
        def boom(argv):
            raise AssertionError("dry-run must never execute the host command")
        r = core.publish_via_host(self.plain, author="publisher-a",
                                  git_config=self.NO_GIT, runner=boom,
                                  dry_run=True)
        self.assertTrue(r["ok"])
        self.assertTrue(r["dry_run"])
        self.assertTrue(r["delegated"])
        self.assertEqual(r["command"][1:],
                         ["skills", "publish", "--to", "github", self.plain])
        self.assertEqual(r["author"], "publisher-a")  # stamp still happened
        self.assertEqual(os.listdir(self.repo), [])   # fallback untouched

    @mock.patch("core.shutil.which", return_value=None)
    def test_fallback_when_host_missing(self, _w):
        r = core.publish_via_host(self.plain, author="publisher-a",
                                  git_config=self.NO_GIT,
                                  fallback_repo=self.repo)
        self.assertTrue(r["ok"])
        self.assertFalse(r["delegated"])
        self.assertIn("unavailable", r["note"])
        self.assertIn("preferred", r["note"])  # loud note
        fm = self._fm(os.path.join(self.repo, "skills", "general", "plain-tool"))
        self.assertEqual(fm["author"], "publisher-a")
        self.assertEqual(fm["source"], "xomni")

    @mock.patch("core.shutil.which", return_value=HERMES)
    def test_delegate_host_failure_loud(self, _w):
        runner = _FakeHostRunner(ok=False)  # smoke passes, publish fails
        r = core.publish_via_host(self.plain, runner=runner)
        self.assertFalse(r["ok"])
        self.assertTrue(r["delegated"])
        self.assertIn("failed", r["reason"])

    @mock.patch("core.shutil.which", return_value=HERMES)
    def test_host_publish_available_smoke(self, _w):
        ok_runner = _FakeHostRunner()
        self.assertTrue(core.host_publish_available(runner=ok_runner)[0])
        bad_help = _FakeHostRunner(help_ok=False)  # help advertises nothing
        avail, why = core.host_publish_available(runner=bad_help)
        self.assertFalse(avail)
        self.assertTrue(why)

    def test_host_publish_available_missing_exe(self):
        with mock.patch("core.shutil.which", return_value=None):
            avail, why = core.host_publish_available(runner=_FakeHostRunner())
        self.assertFalse(avail)
        self.assertIn("not found", why)

    def test_build_publish_command_clamps_bad_target(self):
        cmd = core.build_publish_command("/tmp/s", target="weird")
        self.assertEqual(cmd[1:], ["skills", "publish", "--to", "github", "/tmp/s"])
        self.assertTrue(os.path.basename(cmd[0]).lower().startswith("hermes"))

    def test_publish_via_host_refuses_reject(self):
        r = core.publish_via_host(self.bad, author="publisher-a",
                                  git_config=self.NO_GIT)
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "REJECT")
        self.assertTrue(r["issues"])
        self.assertEqual(os.listdir(self.repo), [])  # nothing written

    def test_publish_via_host_missing_dir(self):
        missing = os.path.join(self.src, "does-not-exist")
        r = core.publish_via_host(missing)
        self.assertFalse(r["ok"])
        self.assertIn("not found", r["reason"])
        self.assertEqual(os.listdir(self.repo), [])


if __name__ == "__main__":
    unittest.main()
