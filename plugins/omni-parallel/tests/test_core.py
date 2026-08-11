"""Unit tests for the omni-parallel plugin core (pure stdlib, no host)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (  # noqa: E402
    DELIVERABLE_CONTRACT,
    TaskQueue,
    judge_results,
    make_context_pack,
    merge_plan,
    split_diff,
)


def _tmp_state():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    return path


class TestTaskQueue(unittest.TestCase):
    def test_add_and_list(self):
        path = _tmp_state()
        q = TaskQueue(path)
        q.add_task("t1", "scan vendor A")
        q.add_task("t2", "scan vendor B")
        items = q.list()
        self.assertEqual(len(items), 2)
        self.assertEqual([t["status"] for t in items], ["pending", "pending"])
        self.assertEqual(q.list(status="pending"), items)
        self.assertEqual(q.list(status="done"), [])

    def test_dedupe_by_id(self):
        path = _tmp_state()
        q = TaskQueue(path)
        first = q.add_task("t1", "brief one")
        again = q.add_task("t1", "brief two")
        self.assertIs(first, again)
        self.assertEqual(len(q.list()), 1)
        self.assertEqual(first["brief"], "brief one")

    def test_transitions(self):
        path = _tmp_state()
        q = TaskQueue(path)
        q.add_task("t1", "do it")
        self.assertEqual(q.claim("t1")["status"], "in_progress")
        self.assertEqual(q.complete("t1", result="ok")["status"], "done")
        self.assertEqual(q.get("t1")["result"], "ok")
        q.add_task("t2", "fail me")
        self.assertEqual(q.fail("t2", error="boom")["status"], "failed")
        self.assertEqual(q.retry("t2")["status"], "pending")
        self.assertIsNone(q.claim("nope"))

    def test_persist_reload_roundtrip(self):
        path = _tmp_state()
        q1 = TaskQueue(path)
        q1.add_task("a", "brief A")
        q1.add_task("b", "brief B")
        q1.complete("a", result="done-a")
        q2 = TaskQueue(path)  # fresh instance, same file
        self.assertEqual(len(q2.list()), 2)
        by_id = {t["id"]: t for t in q2.list()}
        self.assertEqual(by_id["a"]["status"], "done")
        self.assertEqual(by_id["a"]["result"], "done-a")
        self.assertEqual(by_id["b"]["status"], "pending")

    def test_corrupt_state_falls_back_cleanly(self):
        path = _tmp_state()
        Path(path).write_text("{this is not json!!", encoding="utf-8")
        q = TaskQueue(path)  # must not raise
        self.assertTrue(q.corrupt)
        self.assertEqual(q.list(), [])
        q.add_task("t1", "still works")
        self.assertEqual(len(q.list()), 1)

    def test_missing_state_file(self):
        q = TaskQueue("/nonexistent/dir/state.json")
        self.assertEqual(q.list(), [])
        self.assertFalse(q.corrupt)


class TestContextPack(unittest.TestCase):
    def test_contains_contract_and_brief(self):
        pack = make_context_pack("build a search index", template="default")
        self.assertIn("build a search index", pack)
        self.assertIn(DELIVERABLE_CONTRACT, pack)
        self.assertIn("VERDICT:", pack)
        self.assertIn("<out>", pack)

    def test_templates_differ_by_mode(self):
        r = make_context_pack("research x", template="research")
        c = make_context_pack("code y", template="coding")
        self.assertIn("SOURCES", r)
        self.assertIn("TESTS SECTION", c)
        self.assertNotEqual(r, c)

    def test_missing_template_falls_back(self):
        pack = make_context_pack("z", template="does-not-exist")
        self.assertIn(DELIVERABLE_CONTRACT, pack)  # builtin default, no raise

    def test_repo_path_rendered(self):
        pack = make_context_pack("w", repo_path="C:/repo/x", template="default")
        self.assertIn("C:/repo/x", pack)


class TestJudge(unittest.TestCase):
    STRONG = {
        "id": "worker-a",
        "brief": "build a search index for vendors with tests",
        "deliverable_path": "out/index.py",
        "summary": "Built index.\nWrote out/index.py.\nRan tests.\nVERDICT: done",
        "text": "wrote out/index.py, ran tests, search index complete",
    }
    WEAK = {
        "id": "worker-b",
        "brief": "build a search index for vendors with tests",
        "summary": "I thought about it a lot.\n" * 60,  # 60 lines, no verdict, no path
    }

    def test_judge_picks_better(self):
        out = judge_results([self.STRONG, self.WEAK], rubric="code")
        by_id = {s["id"]: s for s in out["results"]}
        self.assertGreater(by_id["worker-a"]["score"], by_id["worker-b"]["score"])
        self.assertEqual(out["best"]["id"], "worker-a")
        self.assertIn("rationale", out["best"])

    def test_weak_result_scores_low(self):
        out = judge_results([self.WEAK], rubric="default")
        self.assertEqual(out["results"][0]["score"], 0)  # nothing matched

    def test_research_rubric_rewards_sources(self):
        strong_r = {
            "id": "r1",
            "brief": "compare five pricing engines",
            "deliverable_path": "out/report.md",
            "summary": "Compared engines.\nVERDICT: done",
            "text": "See https://a.example/x and https://b.example/y and [1] [2].",
        }
        weak_r = {"id": "r2", "brief": "compare five pricing engines",
                  "summary": "Done.\nVERDICT: done", "text": "no sources at all"}
        out = judge_results([strong_r, weak_r], rubric="research")
        by_id = {s["id"]: s for s in out["results"]}
        self.assertGreater(by_id["r1"]["score"], by_id["r2"]["score"])
        self.assertEqual(out["best"]["id"], "r1")

    def test_empty_results(self):
        out = judge_results([], rubric="default")
        self.assertIsNone(out["best"])
        self.assertEqual(out["results"], [])

    def test_deterministic_tiebreak(self):
        a = {"id": "a", "brief": "x", "summary": "S.\nVERDICT: done"}
        b = {"id": "b", "brief": "x", "summary": "S.\nVERDICT: done"}
        out1 = judge_results([b, a])
        out2 = judge_results([a, b])
        self.assertEqual(out1["best"]["id"], out2["best"]["id"])  # same winner


class TestSplitDiff(unittest.TestCase):
    DIFF = """diff --git a/plugins/alpha/run.py b/plugins/alpha/run.py
--- a/plugins/alpha/run.py
+++ b/plugins/alpha/run.py
@@ -1 +1 @@
-old
+new
diff --git a/plugins/alpha/helper.py b/plugins/alpha/helper.py
--- a/plugins/alpha/helper.py
+++ b/plugins/alpha/helper.py
@@ -1 +1 @@
-oldh
+newh
diff --git a/plugins/beta/main.py b/plugins/beta/main.py
--- a/plugins/beta/main.py
+++ b/plugins/beta/main.py
@@ -1 +1 @@
-oldb
+newb
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-oldr
+newr
"""

    def test_groups_by_prefix(self):
        chunks = split_diff(self.DIFF, max_chunks=4)
        self.assertEqual([c["title"] for c in chunks], ["README.md", "plugins/alpha", "plugins/beta"])
        alpha = chunks[1]
        self.assertEqual(alpha["files"], ["plugins/alpha/run.py", "plugins/alpha/helper.py"])
        self.assertIn("run.py", alpha["diff"])

    def test_max_chunks_cap_folds_tail(self):
        diff = self.DIFF + """diff --git a/plugins/gamma/x.py b/plugins/gamma/x.py
--- a/plugins/gamma/x.py
+++ b/plugins/gamma/x.py
@@ -1 +1 @@
-oldg
+newg
"""
        chunks = split_diff(diff, max_chunks=2)
        self.assertEqual(len(chunks), 2)
        # tail prefixes folded into one extra chunk (alpha has 2 files)
        self.assertEqual(len(chunks[-1]["files"]), 4)
        self.assertEqual(chunks[-1]["title"], "misc")

    def test_commit_messages_emitted(self):
        chunks = split_diff(self.DIFF)
        for c in chunks:
            self.assertIn("feat(", c["commit_message"])
            self.assertIn(c["title"], c["commit_message"])

    def test_empty_diff(self):
        self.assertEqual(split_diff(""), [])
        self.assertIn("no diff chunks", merge_plan([]))

    def test_merge_plan_report(self):
        plan = merge_plan(split_diff(self.DIFF))
        self.assertIn("MERGE PLAN", plan)
        self.assertIn("PR 1", plan)
        self.assertIn("suggested commit", plan)


if __name__ == "__main__":
    unittest.main()
