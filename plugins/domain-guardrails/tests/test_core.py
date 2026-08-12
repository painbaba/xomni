"""domain-guardrails tests — pure core, no host needed."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core


class DomainTests(unittest.TestCase):
    def test_trading_detected(self):
        self.assertEqual(core.classify_domain("place a buy order for AAPL"), "trading")

    def test_money_detected(self):
        self.assertEqual(core.classify_domain("transfer 500 via upi"), "money")

    def test_medical_detected(self):
        self.assertEqual(core.classify_domain("prescribe amoxicillin 500mg"), "medical")

    def test_legal_detected(self):
        self.assertEqual(core.classify_domain("review this contract clause"), "legal")

    def test_crypto_detected(self):
        self.assertEqual(core.classify_domain("swap 1 ETH on the bridge"), "crypto")

    def test_code_exec_detected(self):
        self.assertEqual(core.classify_domain("run pip install vectorbt"), "code-exec")

    def test_unknown_domain(self):
        self.assertEqual(core.classify_domain("what is the weather"), "unknown")


class ActionClassTests(unittest.TestCase):
    def test_execution_detected(self):
        self.assertEqual(core.action_class("place the order"), "execution")

    def test_read_only_detected(self):
        self.assertEqual(core.action_class("fetch the latest price"), "analysis")

    def test_unmarked_defaults_to_analysis(self):
        self.assertEqual(core.action_class("hello there"), "analysis")


class DecideTests(unittest.TestCase):
    def test_trading_execution_requires_approval(self):
        v = core.decide("place a buy order for 100 shares of AAPL")
        self.assertEqual(v["domain"], "trading")
        self.assertEqual(v["action"], "execution")
        self.assertEqual(v["policy"], "block-approval")
        self.assertFalse(v["allowed"])
        self.assertTrue(v["requires_approval"])

    def test_trading_analysis_allowed(self):
        v = core.decide("analyze my AAPL position and suggest entry levels")
        self.assertEqual(v["domain"], "trading")
        self.assertEqual(v["action"], "analysis")
        self.assertTrue(v["allowed"])
        self.assertFalse(v["requires_approval"])

    def test_money_execution_requires_approval(self):
        v = core.decide("send money to the vendor account")
        self.assertTrue(v["requires_approval"])

    def test_medical_analysis_warn(self):
        v = core.decide("review this patient diagnosis report")
        self.assertEqual(v["policy"], "warn")
        self.assertTrue(v["allowed"])

    def test_unknown_execution_warn(self):
        v = core.decide("start the thing now")
        self.assertEqual(v["domain"], "unknown")
        self.assertEqual(v["policy"], "warn")
        self.assertTrue(v["allowed"])

    def test_stack_override_applies(self):
        v = core.decide("place a buy order", stack="trading-stack")
        self.assertEqual(v["policy"], "block-approval")
        self.assertTrue(v["requires_approval"])

    def test_reason_mentions_domain_action(self):
        v = core.decide("place a buy order")
        self.assertIn("trading/execution", v["reason"])

    def test_verdict_keys_complete(self):
        v = core.decide("anything")
        for key in ("domain", "action", "policy", "allowed",
                    "requires_approval", "reason"):
            self.assertIn(key, v)


class DecideToolTests(unittest.TestCase):
    def test_tool_fetch_stock_price_allowed(self):
        v = core.decide_tool("fetch_stock_price",
                             "Fetch the current stock price for a symbol")
        self.assertEqual(v["domain"], "trading")
        self.assertEqual(v["action"], "analysis")
        self.assertEqual(v["policy"], "allow")
        self.assertTrue(v["allowed"])
        self.assertFalse(v["requires_approval"])

    def test_tool_place_order_requires_approval(self):
        v = core.decide_tool("place_order",
                             "Place a market order for the given symbol and quantity")
        self.assertEqual(v["domain"], "trading")
        self.assertEqual(v["action"], "execution")
        self.assertEqual(v["policy"], "block-approval")
        self.assertFalse(v["allowed"])
        self.assertTrue(v["requires_approval"])

    def test_tool_legal_warn(self):
        v = core.decide_tool("contract_draft",
                             "Draft a contract clause with agreement terms")
        self.assertEqual(v["domain"], "legal")
        self.assertEqual(v["policy"], "warn")
        self.assertTrue(v["allowed"])
        self.assertFalse(v["requires_approval"])

    def test_tool_unknown_conservative(self):
        v = core.decide_tool("widget_tool", "frobnicate the widget")
        self.assertEqual(v["domain"], "unknown")
        self.assertIn(v["policy"], ("allow", "warn"))
        self.assertFalse(v["requires_approval"])
        v2 = core.decide_tool("widget_tool", "start the widget daemon")
        self.assertEqual(v2["action"], "execution")
        self.assertEqual(v2["policy"], "warn")
        self.assertTrue(v2["allowed"])


class DecideSkillTests(unittest.TestCase):
    def test_skill_medical_block_approval(self):
        fm = ("---\nname: dose-calculator\ndescription: Calculate patient "
              "medication doses and treatment plans\n---")
        v = core.decide_skill(fm)
        self.assertEqual(v["domain"], "medical")
        self.assertEqual(v["action"], "execution")
        self.assertEqual(v["policy"], "block-approval")
        self.assertFalse(v["allowed"])
        self.assertTrue(v["requires_approval"])

    def test_skill_trading_warn(self):
        v = core.decide_skill("name: trade-bot\ndescription: Automated buy and "
                              "sell order placement")
        self.assertEqual(v["domain"], "trading")
        self.assertEqual(v["action"], "execution")
        self.assertEqual(v["policy"], "warn")
        self.assertTrue(v["allowed"])


class SkillPathTests(unittest.TestCase):
    def test_skill_path_read_and_loud_missing_error(self):
        import tempfile
        plug_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, plug_dir)  # tests/__init__.py would shadow the plugin
        from __init__ import _handle_guardrails
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "SKILL.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("---\nname: med\ndescription: patient medication dosing\n---")
            out = _handle_guardrails(f"check-skill {p}")
            self.assertIn("block-approval", out)
            self.assertIn("medical", out)
            missing = os.path.join(td, "NOPE.md")
            out2 = _handle_guardrails(f"check-skill {missing}")
            self.assertIn("ERROR", out2)
            self.assertIn("not found", out2)
            self.assertIn("NOPE.md", out2)


class PolicyTableTests(unittest.TestCase):
    def test_table_lists_all_domains(self):
        t = core.policy_table()
        for d in core.DOMAIN_POLICIES:
            self.assertIn(d, t)

    def test_table_explains_approval(self):
        self.assertIn("block-approval", core.policy_table())


class NoHooksTests(unittest.TestCase):
    def test_no_hook_api_in_init(self):
        init = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "__init__.py"), encoding="utf-8").read()
        self.assertNotIn("register_hook", init)


if __name__ == "__main__":
    unittest.main()
