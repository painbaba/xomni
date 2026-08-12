"""Tests for model-router — automatic per-task model routing + telemetry.

Covers: task-type detection (reasoning/vision/quick keyword sets and
precedence), routing over a FAKE 20-model registry with MIXED pick sources
(live-probe > verified > spec tie-breaks: live-probe picks win, vision NEVER
routes to a vision=False model, heavy picks the biggest context, empty
registry -> LOUD fallback + live provider /models probe fallback), the config
switch command, alternatives, pool size + pick source reporting, the
cost-tracker-compatible telemetry ledger roundtrip, and /route telemetry
rendering (model, ms, $, task type).

Run: cd plugins/model-router && python -m unittest tests.test_core -q
"""
import datetime
import importlib.util
import inspect
import os
import statistics
import sys
import tempfile
import time
import unittest
from unittest import mock

import core


def _ts(y, m, d, hh=12, mm=0):
    return datetime.datetime(y, m, d, hh, mm).timestamp()


def _rec(mid, ctx, caps, tier, latency=4100, cap_src=None, provider="opencode-zen"):
    """One registry record in the LIVE capabilities.json schema.

    tier='live-probe'  -> source='live-probe' marker + verified.method http200
                          (the registry's own live spot-check evidence)
    tier='verified'    -> verified.ok with a non-live method
    tier='spec'        -> verified.ok=False, nothing but spec declarations
    """
    cap_src = cap_src or {}
    return {
        "id": mid,
        "name": mid,
        "provider": provider,
        "status": "active",
        "context_window": {"value": ctx, "source": "spec", "origin": "fixture"},
        "max_output": {"value": 8192, "source": "spec", "origin": "fixture"},
        "capabilities": list(caps),
        "capability_sources": {c: cap_src.get(c, "spec") for c in caps},
        "cost_per_1m": {"input": 0.0, "output": 0.0, "currency": "USD",
                        "source": "verified", "origin": "fixture"},
        "latency_ms": {"median": latency, "samples": 30, "source": "estimated",
                       "origin": "fixture"},
        "verified": {
            "ok": tier != "spec",
            "method": ("http200 spot-check" if tier == "live-probe"
                       else "vendor cross-check" if tier == "verified" else "spec"),
            "date": "2026-08-10", "last_seen": "2026-08-12T00:00:00Z"},
        "provenance": {"primary": "curated", "updated_at": "2026-08-12T00:00:00Z"},
        "source": "live-probe" if tier == "live-probe" else None,
    }


def _fake_registry():
    """Deterministic 20-model fixture with MIXED pick sources (never the live
    file — tests must be immune to parallel registry refreshes).

    7 live-probe (http200 spot-checked), 7 verified (ok but not live),
    6 spec-only. Ids come from the real gateway model set so provider-pool
    tags (fast/reasoning/default/vision) still apply.
    """
    reg = {}
    for mid, ctx, caps in (
        # live-probe tier (7)
        ("deepseek-v4-pro", 1048576, ("thinking", "tools")),
        ("minimax-m3", 1048576, ("thinking", "tools", "structured_output", "image_in")),
        ("gpt-5.6-luna", 1050000, ("thinking", "tools", "structured_output", "image_in")),
        ("kimi-k3", 1048576, ("thinking", "tools", "structured_output", "image_in")),
        ("qwen3.7-plus", 1000000, ("thinking", "tools", "structured_output", "image_in", "video_in")),
        ("kimi-k2.7-code", 262144, ("thinking", "tools", "structured_output", "image_in")),
        ("hy3", 256000, ("thinking", "tools")),
    ):
        reg[mid] = _rec(mid, ctx, caps, "live-probe")
    for mid, ctx, caps in (
        # verified tier (7)
        ("deepseek-v4-flash", 1000000, ("thinking", "tools")),
        ("glm-5.2", 1048576, ("thinking", "tools", "structured_output")),
        ("minimax-m2.7", 196608, ("thinking", "tools", "structured_output")),
        ("mimo-v2-pro", 1048576, ("thinking", "tools")),
        ("qwen3.8-max", 1000000, ("thinking", "tools", "structured_output", "image_in", "video_in")),
        ("kimi-k2.6", 262144, ("thinking", "tools", "structured_output", "image_in")),
        ("grok-4.5", 500000, ("thinking", "tools", "structured_output", "image_in")),
    ):
        reg[mid] = _rec(mid, ctx, caps, "verified")
    for mid, ctx, caps in (
        # spec tier (6)
        ("glm-5.1", 202752, ("thinking", "tools", "structured_output")),
        ("glm-5", 202752, ("thinking", "tools", "structured_output")),
        ("qwen3.7-max", 1000000, ("thinking", "tools", "structured_output")),
        ("qwen3.6-plus", 1000000, ("thinking", "tools", "structured_output", "image_in", "video_in")),
        ("minimax-m2.5", 196680, ("thinking", "tools", "structured_output")),
        ("hy3-preview", 256000, ("thinking", "tools", "structured_output")),
    ):
        reg[mid] = _rec(mid, ctx, caps, "spec")
    # minimax-m3 is the ONLY image_in capability spot-checked live (as real)
    reg["minimax-m3"]["capability_sources"]["image_in"] = "verified"
    assert len(reg) == 20
    return reg


class DetectTaskTypeTests(unittest.TestCase):
    def test_backtest_query_detects_reasoning(self):
        ttype, kws = core.detect_task_type("why does my backtest lose money?")
        self.assertEqual(ttype, "reasoning")
        self.assertIn("why", kws)
        self.assertIn("backtest", kws)

    def test_screenshot_wins_over_summarize(self):
        # vision > quick precedence: a screenshot-summary needs image input
        ttype, _ = core.detect_task_type("summarize this screenshot for me")
        self.assertEqual(ttype, "vision")

    def test_plain_summarize_goes_quick(self):
        ttype, kws = core.detect_task_type("summarize this article briefly")
        self.assertEqual(ttype, "quick")
        self.assertIn("summarize", kws)

    def test_no_keywords_defaults(self):
        ttype, kws = core.detect_task_type("hello there")
        self.assertEqual(ttype, "default")
        self.assertEqual(kws, [])


class RoutingTests(unittest.TestCase):
    """Every task type must route to a capability-matching model from the
    FAKE 20-model registry (active status + capability gate), never a
    tombstone, with live-probe > verified > spec tie-breaks."""

    def setUp(self):
        self.registry = _fake_registry()
        self.pool = [r for r in self.registry.values()
                     if r.get("status") in core.CANDIDATE_STATUSES]

    def _picked(self, res):
        return self.registry[res["model"]]

    def test_quick_routes_to_low_latency_capable_model(self):
        res = core.route("summarize this quickly", registry=self.registry)
        rec = self._picked(res)
        self.assertEqual(res["task_type"], "quick")
        self.assertEqual(rec["status"], "active")
        self.assertIn("tools", rec.get("capabilities", []))
        lat = (rec.get("latency_ms") or {}).get("median")
        self.assertLess(lat, core.LATENCY_THRESHOLD_MS)

    def test_reasoning_routes_to_thinking_model(self):
        res = core.route("why does my backtest lose money?", registry=self.registry)
        rec = self._picked(res)
        self.assertEqual(res["task_type"], "reasoning")
        self.assertEqual(rec["status"], "active")
        self.assertTrue("thinking" in rec.get("capabilities", [])
                        or "always_thinking" in rec.get("capabilities", []))

    def test_reasoning_pick_is_reasoning_tier(self):
        # deterministic reasoning-tier pick (matches provider-pool RECOMMENDED)
        res = core.route("debug why the error occurs", registry=self.registry)
        self.assertEqual(res["model"], "deepseek-v4-pro")

    def test_vision_routes_to_vision_model(self):
        res = core.route("read the text from this screenshot", registry=self.registry)
        rec = self._picked(res)
        self.assertEqual(res["task_type"], "vision")
        self.assertIn("image_in", rec.get("capabilities", []))

    def test_vision_never_routes_to_non_vision_model(self):
        # HARD GATE: every vision route must land on an image_in model
        for prompt in ("ocr this image", "what is in this screenshot",
                       "describe the chart", "scan this photo"):
            res = core.route(prompt, registry=self.registry)
            rec = self._picked(res)
            self.assertIn("image_in", rec.get("capabilities", []),
                          f"{prompt!r} routed to non-vision {res['model']}")

    def test_vision_prefers_live_verified_image_in(self):
        res = core.route("describe this screenshot", registry=self.registry)
        rec = self._picked(res)
        self.assertEqual(res["model"], "minimax-m3")
        self.assertEqual(
            (rec.get("capability_sources") or {}).get("image_in"), "verified")

    def test_heavy_routes_to_max_context_model(self):
        res = core.route("process this entire codebase repo", registry=self.registry)
        rec = self._picked(res)
        self.assertEqual(res["task_type"], "heavy")
        ctx = (rec.get("context_window") or {}).get("value")
        max_ctx = max((r.get("context_window") or {}).get("value", 0)
                      for r in self.pool)
        self.assertEqual(ctx, max_ctx)

    def test_default_routes_workhorse_model(self):
        res = core.route("hello there", registry=self.registry)
        rec = self._picked(res)
        self.assertEqual(res["task_type"], "default")
        self.assertIn("tools", rec.get("capabilities", []))
        self.assertIn("thinking", rec.get("capabilities", []))
        self.assertEqual(res["model"], "deepseek-v4-flash")

    def test_config_command_present(self):
        res = core.route("summarize this quickly", registry=self.registry)
        self.assertEqual(res["config_command"],
                         f"hermes config set model {res['model']}")
        self.assertIn(res["model"], res["config_command"])

    def test_alternatives_match_capability(self):
        res = core.route("ocr this image", registry=self.registry)
        for alt in res["alternatives"]:
            rec = self.registry.get(alt["model"])
            self.assertIsNotNone(rec)
            self.assertIn("image_in", rec.get("capabilities", []))
        res = core.route("debug the error", registry=self.registry)
        for alt in res["alternatives"]:
            rec = self.registry.get(alt["model"])
            self.assertTrue("thinking" in rec.get("capabilities", [])
                            or "always_thinking" in rec.get("capabilities", []))

    def test_fallback_without_registry(self):
        # empty registry -> LOUD deterministic fallback tier table, same picks;
        # the provider /models probe is unavailable, so no network is touched
        with mock.patch.object(core, "auto_probe_live", return_value=None):
            for prompt, expect in (
                ("summarize quickly", "minimax-m2.5"),
                ("why did it fail", "deepseek-v4-pro"),
                ("ocr the screenshot", "minimax-m3"),
                ("entire repo", "gpt-5.6-luna"),
                ("hello", "deepseek-v4-flash"),
            ):
                res = core.route(prompt, registry={})
                self.assertEqual(res["model"], expect, prompt)
                self.assertEqual(res["registry_source"], "fallback")
                self.assertEqual(res["pool_size"], 0)
                self.assertEqual(res["pick_source"], "fallback")
                self.assertIn("config_command", res)

    # ---- U-CORE-2: live registry pool, source tie-breaks, probe fallback ----

    def test_live_probe_pick_wins(self):
        # three capability-identical models (heavy: ctx 1M each) differing only
        # in source tier — the live-probed one must win the tie
        reg = {
            "aaa-probed": _rec("aaa-probed", 1000000, ("thinking", "tools"), "spec"),
            "bbb-verified": _rec("bbb-verified", 1000000, ("thinking", "tools"), "verified"),
            "ccc-live": _rec("ccc-live", 1000000, ("thinking", "tools"), "live-probe"),
        }
        res = core.route("entire repo", registry=reg)
        self.assertEqual(res["model"], "ccc-live")  # live-probe beats verified+spec
        self.assertEqual(res["pick_source"], "live-probe")
        # a FRESH live probe elevates the spec model into the live-probe tier
        # and it then wins the tie (id tie-break among live-probe candidates)
        res2 = core.route("entire repo", registry=reg,
                          probe={"ids": ["aaa-probed"], "provider": "opencode-zen"})
        self.assertEqual(res2["model"], "aaa-probed")
        self.assertEqual(res2["pick_source"], "live-probe")
        # verified never beats a live-probed model on a capability tie
        self.assertNotEqual(res["model"], "bbb-verified")

    def test_pool_size_and_pick_source_reported(self):
        res = core.route("hello there", registry=self.registry)
        self.assertEqual(res["pool_size"], 20)
        bd = res["pool_breakdown"]
        self.assertEqual(bd, {"live-probe": 7, "verified": 7, "spec": 6})
        self.assertEqual(sum(bd.values()), res["pool_size"])
        self.assertIn(res["pick_source"], core.SOURCE_TIERS)
        self.assertEqual(res["pick_source"], "verified")  # default -> deepseek-v4-flash (verified tier)
        text = core.route_text(res)
        self.assertIn("pool:", text)
        self.assertIn("20 live models", text)
        self.assertIn("live-probe=7", text)
        self.assertIn("pick source:", text)
        self.assertIn("verified", text)

    def test_empty_registry_loud_fallback(self):
        # registry empty AND probe unavailable -> LOUD, never silent
        with mock.patch.object(core, "auto_probe_live", return_value=None):
            res = core.route("why did it fail", registry={})
            self.assertEqual(res["registry_source"], "fallback")
            self.assertEqual(res["pool_size"], 0)
            self.assertEqual(res["pick_source"], "fallback")
            self.assertTrue(res.get("loud"))
            self.assertIn("NO LIVE MODELS AVAILABLE", res["reason"])
            text = core.route_text(res)
            self.assertIn("0 live models", text)
            self.assertIn("pick source:  fallback", text)

    def test_empty_registry_probe_fallback_picks_live(self):
        # registry empty but the provider /models probe SUCCEEDS: the pick
        # comes from the LIVE ids (source=live-probe), never the tier table
        live = {"ids": ["deepseek-v4-pro", "minimax-m3", "kimi-k3"],
                "provider": "opencode-zen", "probed_at": "2026-08-13T00:00:00Z"}
        with mock.patch.object(core, "auto_probe_live", return_value=live):
            res = core.route("why did it fail", registry={})
            self.assertEqual(res["model"], "deepseek-v4-pro")  # task default IS live
            self.assertEqual(res["registry_source"], "probe:opencode-zen")
            self.assertEqual(res["pool_size"], 3)
            self.assertEqual(res["pick_source"], "live-probe")
            # default not among the live ids -> first live id (stable order)
            live2 = {"ids": ["minimax-m3", "kimi-k3"], "provider": "opencode-zen"}
            with mock.patch.object(core, "auto_probe_live", return_value=live2):
                res2 = core.route("entire repo", registry={})
                self.assertEqual(res2["model"], "kimi-k3")
                self.assertEqual(res2["pick_source"], "live-probe")
                self.assertEqual(res2["pool_size"], 2)


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self._tmp.name, "route.db")
        self.addCleanup(self._tmp.cleanup)

    def _tel(self):
        return core.RouteTelemetry(self.db)

    def test_record_call_roundtrip(self):
        tel = self._tel()
        r = tel.record_call("deepseek-v4-pro", latency_ms=4100, est_cost=0.0,
                            task_type="reasoning", provider="opencode-zen",
                            ts=_ts(2026, 8, 12, 10))
        self.assertTrue(r["logged"])
        rows = tel.recent_calls()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["model"], "deepseek-v4-pro")
        self.assertEqual(row["latency_ms"], 4100)
        self.assertEqual(row["est_cost"], 0.0)
        self.assertEqual(row["task_type"], "reasoning")
        self.assertEqual(row["provider"], "opencode-zen")

    def test_record_call_estimates_cost_via_cost_tracker(self):
        # reuse of cost-tracker's CostTracker math: deepseek-chat is priced
        # (0.27, 1.10) there — (0.27*1000 + 1.10*500)/1M = $0.00082
        tel = self._tel()
        r = tel.record_call("deepseek-chat", latency_ms=900, tokens_in=1000,
                            tokens_out=500, task_type="quick",
                            ts=_ts(2026, 8, 12, 10))
        self.assertAlmostEqual(r["est_cost"], 0.00082, places=8)
        self.assertFalse(r["flagged"])

    def test_unknown_model_flagged_fallback(self):
        tel = self._tel()
        r = tel.record_call("future-model-x", latency_ms=300, tokens_in=1000,
                            tokens_out=500, task_type="quick",
                            ts=_ts(2026, 8, 12, 10))
        # fallback rates (0.50*1000 + 1.50*500)/1M = $0.00125
        self.assertAlmostEqual(r["est_cost"], 0.00125, places=8)
        self.assertTrue(r["flagged"])

    def test_recent_calls_newest_first_limit_10(self):
        tel = self._tel()
        for i in range(12):
            tel.record_call(f"model-{i}", latency_ms=100 + i, est_cost=0.01 * i,
                            task_type="quick", ts=_ts(2026, 8, 12, 10 + i))
        rows = tel.recent_calls(10)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["model"], "model-11")
        self.assertEqual(rows[-1]["model"], "model-2")

    def test_telemetry_text_renders_model_ms_dollar_task(self):
        tel = self._tel()
        tel.record_call("deepseek-v4-pro", latency_ms=4100, est_cost=0.0,
                        task_type="reasoning", ts=_ts(2026, 8, 12, 10))
        tel.record_call("minimax-m3", latency_ms=5200, est_cost=0.0,
                        task_type="vision", ts=_ts(2026, 8, 12, 11))
        tel.record_call("deepseek-chat", latency_ms=900, tokens_in=1000,
                        tokens_out=500, task_type="quick",
                        ts=_ts(2026, 8, 12, 12))
        text = tel.telemetry_text()
        for needle in ("deepseek-v4-pro", "minimax-m3", "deepseek-chat",
                       "ms", "$", "reasoning", "vision", "quick"):
            self.assertIn(needle, text)
        # newest first: deepseek-chat row on top
        self.assertLess(text.index("deepseek-chat"),
                        text.index("minimax-m3"))


class AutoRouteHookTests(unittest.TestCase):
    """pre_llm_call automatic-routing hook — deterministic, config-gated,
    I/O-free (<1ms), telemetry auto-record; /route stays advisory."""

    @classmethod
    def setUpClass(cls):
        # Load plugins/model-router/__init__.py as an isolated package (same
        # loader ci_gate/bench use) so `from . import core` resolves to its
        # own module instance (mr.core) — hook state lives there.
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        spec = importlib.util.spec_from_file_location(
            "model_router_pkg", os.path.join(plugin_dir, "__init__.py"),
            submodule_search_locations=[plugin_dir])
        cls.mr = importlib.util.module_from_spec(spec)
        cls.mr.__package__ = "model_router_pkg"
        cls.mr.__path__ = [plugin_dir]
        sys.modules["model_router_pkg"] = cls.mr
        spec.loader.exec_module(cls.mr)

    def setUp(self):
        self.mr._CTX = None
        self.mr.core._PENDING_TELEMETRY.clear()
        self.mr.core._LAST_SUGGESTION = None

    def test_hook_classifies_each_task_type(self):
        # deterministic keyword-only classification for every task type
        cases = [
            ("summarize this article quickly", "quick", "minimax-m2.5"),
            ("debug why this fails", "reasoning", "deepseek-v4-pro"),
            ("ocr this screenshot", "vision", "minimax-m3"),
            ("process the entire repo", "heavy", "gpt-5.6-luna"),
            ("hello there", "default", "deepseek-v4-flash"),
        ]
        for prompt, ttype, model in cases:
            ctx = _HookCtx({"model-router": {"auto_route": True}}, model="some-model")
            self.mr.register(ctx)
            out = self.mr._on_pre_llm_call(user_message=prompt)
            sug = self.mr.core.last_suggestion()
            self.assertEqual(sug["task_type"], ttype, prompt)
            self.assertEqual(sug["suggested_model"], model, prompt)
            self.assertTrue(sug["differs"], prompt)
            self.assertIsNotNone(out, prompt)  # override hint returned
            self.assertEqual(out["model_router"]["suggested_model"], model, prompt)
            self.assertEqual(ctx.model_router_suggestion["task_type"], ttype, prompt)

    def test_auto_route_disabled_records_nothing(self):
        ctx = _HookCtx({"model-router": {"auto_route": False}}, model="some-model")
        self.mr.register(ctx)
        out = self.mr._on_pre_llm_call(user_message="debug why this fails")
        self.assertIsNone(out)
        self.assertIsNone(self.mr.core.last_suggestion())
        self.assertEqual(self.mr.core._PENDING_TELEMETRY, [])
        self.assertIsNone(ctx.model_router_suggestion)

    def test_matching_model_returns_no_override_hint(self):
        # configured model already == suggested: no hint, but telemetry still
        # records the classified call ("keep" decision)
        ctx = _HookCtx({"model-router": {"auto_route": True}}, model="minimax-m2.5")
        self.mr.register(ctx)
        out = self.mr._on_pre_llm_call(user_message="summarize this quickly")
        self.assertIsNone(out)
        sug = self.mr.core.last_suggestion()
        self.assertFalse(sug["differs"])
        self.assertEqual(sug["action"], "keep")
        self.assertEqual(len(self.mr.core._PENDING_TELEMETRY), 1)

    def test_hook_never_calls_llm(self):
        # (a) source scan: handler must be free of ci_gate's forbidden tokens
        src = inspect.getsource(self.mr._on_pre_llm_call)
        for token in (".complete(", "requests.", "subprocess"):
            self.assertNotIn(token, src)
        # (b) mock: a ctx whose llm.complete raises must never be hit
        ctx = _HookCtx({"model-router": {"auto_route": True}}, model="some-model")
        self.mr.register(ctx)
        for _ in range(3):
            self.mr._on_pre_llm_call(user_message="summarize quickly")
        self.assertEqual(len(self.mr.core._PENDING_TELEMETRY), 3)

    def test_hook_under_1ms_budget(self):
        ctx = _HookCtx({"model-router": {"auto_route": True}}, model="some-model")
        self.mr.register(ctx)
        samples = []
        for _ in range(200):
            t0 = time.perf_counter()
            self.mr._on_pre_llm_call(
                user_message="debug why my backtest loses money")
            samples.append((time.perf_counter() - t0) * 1000)
        med = statistics.median(samples)
        self.assertLess(med, 1.0,
                        f"hook median {med:.4f}ms >= 1ms budget")

    def test_telemetry_auto_records_classified_calls(self):
        # hook classifications are recorded in memory, flushed into the
        # cost-tracker ledger on the next /route telemetry read
        ctx = _HookCtx({"model-router": {"auto_route": True}}, model="some-model")
        self.mr.register(ctx)
        self.mr._on_pre_llm_call(user_message="debug why this fails")
        self.mr._on_pre_llm_call(user_message="ocr the screenshot")
        self.assertEqual(len(self.mr.core._PENDING_TELEMETRY), 2)
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "route.db")
            orig = self.mr.core.RouteTelemetry

            class _TmpTel(orig):
                def __init__(self, db_path=None):
                    super().__init__(db_path or db)

            self.mr.core.RouteTelemetry = _TmpTel
            try:
                text = self.mr.core.route_telemetry_text()
            finally:
                self.mr.core.RouteTelemetry = orig
            # pending queue drained into the ledger + rendered by /route
            self.assertEqual(self.mr.core._PENDING_TELEMETRY, [])
            rows = orig(db).recent_calls()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["task_type"], "vision")
            self.assertEqual(rows[0]["model"], "minimax-m3")
            self.assertEqual(rows[1]["task_type"], "reasoning")
            self.assertEqual(rows[1]["model"], "deepseek-v4-pro")
            self.assertIn("minimax-m3", text)
            self.assertIn("reasoning", text)

    def test_route_command_stays_advisory(self):
        ctx = _HookCtx({"model-router": {"auto_route": True}}, model="some-model")
        self.mr.register(ctx)
        self.assertIn("pre_llm_call", ctx.hooks)  # hook registered
        self.assertIn("route", ctx.commands)      # /route still registered
        text = ctx.commands["route"]("summarize this quickly")
        self.assertIn("model:", text)
        self.assertIn("switch:", text)  # prints the config command — advisory
        self.assertIn("config set model", text)
        # advisory: /route <prompt> records nothing and switches nothing
        self.assertEqual(self.mr.core._PENDING_TELEMETRY, [])
        self.assertIsNone(ctx.model_router_suggestion)


class _HookCtx:
    """Minimal host ctx for hook tests: config + model + hook/command capture.
    llm.complete raises on any call — a hook touching the LLM fails the test."""

    def __init__(self, config=None, model=None):
        self.config = config or {}
        self.model = model
        self.hooks = {}
        self.commands = {}
        self.model_router_suggestion = None
        self.llm = _FailingLlm()

    def register_hook(self, name, fn):
        self.hooks.setdefault(name, []).append(fn)

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands[name] = handler


class _FailingLlm:
    def complete(self, *a, **k):
        raise AssertionError("a hook called the LLM — forbidden")


if __name__ == "__main__":
    unittest.main()