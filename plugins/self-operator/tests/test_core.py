"""Tests for the self-operator core (stdlib unittest, no third-party deps)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import core
from core import (
    OperatorError,
    approve_plan,
    audit_trail,
    execute_approved,
    parse_backlog,
    pending_approvals,
    propose_plan,
    reject_plan,
    run_cycle,
    submit_plan,
)

# [x] done, [~] in progress, [ ] open, plus non-item lines and traps:
# indented task (does not match ^- \[ \] ) and uppercase [X] (case-sensitive).
SAMPLE_BACKLOG = """\
# Backlog

## Done
- [x] shipped thing

## In progress
- [~] wip thing

## Open
- [ ] first open
- [ ] second open
plain text line, not a task
- [ ] third open
  - [ ] indented nested task
- [X] uppercase marker is not open
"""

OPEN_ITEMS = ["first open", "second open", "third open"]
OPEN_LINES = [10, 11, 13]


class FakeRunner:
    """Records every item title it is handed; always succeeds."""

    def __init__(self):
        self.calls = []

    def __call__(self, item_title):
        self.calls.append(item_title)
        return {"ok": True, "note": "handled: " + item_title}


class SelfOperatorCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_backlog(self, text=SAMPLE_BACKLOG):
        path = Path(self._tmp.name) / "BACKLOG.md"
        path.write_text(text, encoding="utf-8")
        return path

    def submitted_approved_plan(self, max_items=None):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        if max_items is not None:
            plan = propose_plan(parse_backlog(self.write_backlog()), max_items=max_items)
        submit_plan(plan, self.state_dir)
        approve_plan(plan["plan_id"], self.state_dir)
        return plan

    # -- parse -------------------------------------------------------------

    def test_parse_backlog_finds_only_open_items(self):
        items = parse_backlog(self.write_backlog())
        self.assertEqual([i["title"] for i in items], OPEN_ITEMS)

    def test_parse_backlog_line_numbers(self):
        items = parse_backlog(self.write_backlog())
        self.assertEqual([i["line"] for i in items], OPEN_LINES)

    # -- propose -----------------------------------------------------------

    def test_propose_plan_preserves_order_and_caps_at_max_items(self):
        items = parse_backlog(self.write_backlog())
        plan = propose_plan(items, max_items=2)
        self.assertEqual(plan["items"], ["first open", "second open"])
        self.assertEqual(plan["count"], 2)
        self.assertTrue(plan["plan_id"].startswith("plan-"))
        self.assertIsInstance(plan["proposed_at"], float)

    def test_propose_plan_empty_backlog_returns_zero_item_plan(self):
        plan = propose_plan([])
        self.assertEqual(plan["items"], [])
        self.assertEqual(plan["count"], 0)
        self.assertTrue(plan["plan_id"].startswith("plan-"))

    # -- approve / execute happy path --------------------------------------

    def test_submit_approve_execute_happy_path(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        submit_plan(plan, self.state_dir)
        approvals = json.loads(
            (self.state_dir / "approvals.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(approvals["plans"]), 1)
        self.assertEqual(approvals["plans"][0]["status"], "pending")
        self.assertEqual(approvals["plans"][0]["plan_id"], plan["plan_id"])

        self.assertEqual(approve_plan(plan["plan_id"], self.state_dir), "approved")
        runner = FakeRunner()
        results = execute_approved(plan["plan_id"], self.state_dir, runner)
        self.assertEqual(runner.calls, plan["items"])
        self.assertEqual([r["item"] for r in results], plan["items"])
        self.assertTrue(all(r["ok"] for r in results))

    def test_execute_approved_passes_item_titles_to_runner(self):
        plan = propose_plan(parse_backlog(self.write_backlog()), max_items=2)
        submit_plan(plan, self.state_dir)
        approve_plan(plan["plan_id"], self.state_dir)
        runner = FakeRunner()
        execute_approved(plan["plan_id"], self.state_dir, runner)
        self.assertEqual(runner.calls, ["first open", "second open"])

    # -- fail-loud gates ---------------------------------------------------

    def test_execute_on_pending_plan_raises(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        submit_plan(plan, self.state_dir)
        with self.assertRaisesRegex(OperatorError, "human approval required"):
            execute_approved(plan["plan_id"], self.state_dir, FakeRunner())

    def test_execute_on_rejected_plan_raises(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        submit_plan(plan, self.state_dir)
        reject_plan(plan["plan_id"], self.state_dir)
        with self.assertRaisesRegex(OperatorError, "human approval required"):
            execute_approved(plan["plan_id"], self.state_dir, FakeRunner())

    def test_approve_twice_raises(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        submit_plan(plan, self.state_dir)
        approve_plan(plan["plan_id"], self.state_dir)
        with self.assertRaises(OperatorError):
            approve_plan(plan["plan_id"], self.state_dir)

    def test_reject_after_approve_raises(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        submit_plan(plan, self.state_dir)
        approve_plan(plan["plan_id"], self.state_dir)
        with self.assertRaises(OperatorError):
            reject_plan(plan["plan_id"], self.state_dir)

    def test_unknown_plan_raises(self):
        with self.assertRaisesRegex(OperatorError, "unknown plan"):
            approve_plan("plan-999", self.state_dir)
        with self.assertRaisesRegex(OperatorError, "never submitted"):
            execute_approved("plan-999", self.state_dir, FakeRunner())

    # -- pending / audit ---------------------------------------------------

    def test_pending_approvals_lists_pending_only(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        submit_plan(plan, self.state_dir)
        self.assertEqual(
            [p["plan_id"] for p in pending_approvals(self.state_dir)],
            [plan["plan_id"]],
        )
        approve_plan(plan["plan_id"], self.state_dir)
        self.assertEqual(pending_approvals(self.state_dir), [])

    def test_audit_trail_appends_and_parses_back_with_ok_flags(self):
        plan = self.submitted_approved_plan()
        execute_approved(plan["plan_id"], self.state_dir, FakeRunner())
        trail = audit_trail(self.state_dir)
        self.assertEqual(len(trail), plan["count"])
        for entry, title in zip(trail, plan["items"]):
            self.assertEqual(entry["plan_id"], plan["plan_id"])
            self.assertEqual(entry["item"], title)
            self.assertIs(entry["ok"], True)
            self.assertIn("ts", entry)

    def test_audit_trail_empty_state_returns_empty_list(self):
        self.assertEqual(audit_trail(self.state_dir), [])

    # -- run_cycle ---------------------------------------------------------

    def test_run_cycle_awaiting_approval_without_auto_approve(self):
        result = run_cycle(self.write_backlog(), self.state_dir)
        self.assertEqual(result["status"], "awaiting_approval")
        self.assertTrue(result["plan_id"].startswith("plan-"))
        self.assertEqual(len(pending_approvals(self.state_dir)), 1)

    def test_run_cycle_waiting_on_existing_pending_plan(self):
        first = run_cycle(self.write_backlog(), self.state_dir)
        second = run_cycle(self.write_backlog(), self.state_dir)
        self.assertEqual(second["status"], "awaiting_approval")
        self.assertEqual(second["plan_id"], first["plan_id"])
        self.assertEqual(len(pending_approvals(self.state_dir)), 1)

    def test_run_cycle_auto_approve_uses_default_runner(self):
        result = run_cycle(
            self.write_backlog(), self.state_dir, auto_approve=True
        )
        self.assertEqual(result["status"], "executed")
        self.assertEqual(len(result["results"]), 3)
        self.assertTrue(
            all(r["ok"] and r["note"] == "dry-run" for r in result["results"])
        )
        self.assertEqual(len(audit_trail(self.state_dir)), 3)

    def test_run_cycle_auto_approve_uses_custom_runner(self):
        runner = FakeRunner()
        result = run_cycle(
            self.write_backlog(),
            self.state_dir,
            runner=runner,
            auto_approve=True,
        )
        self.assertEqual(result["status"], "executed")
        self.assertEqual(runner.calls, OPEN_ITEMS)
        self.assertEqual([r["item"] for r in result["results"]], OPEN_ITEMS)

    # -- module STATE_DIR fallback -----------------------------------------

    def test_state_dir_module_var_is_used_by_default(self):
        plan = propose_plan(parse_backlog(self.write_backlog()))
        with mock.patch.object(core, "STATE_DIR", self.state_dir):
            submit_plan(plan)
            approve_plan(plan["plan_id"])
            results = execute_approved(plan["plan_id"], runner=FakeRunner())
        self.assertEqual(len(results), 3)
        self.assertTrue((self.state_dir / "approvals.json").exists())
        self.assertTrue((self.state_dir / "operator.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
