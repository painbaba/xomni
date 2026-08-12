"""Tests for the omni-registry core (capability-declared model registry)."""
import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

import core


class RegistryLoadTests(unittest.TestCase):
    """registry_load / capability / envelope semantics."""

    def test_registry_load_25_active_plus_tombstones(self):
        reg = core.registry_load()
        active = [r for r in reg.values() if r["status"] == "active"]
        self.assertEqual(len(active), 25)
        ids = [r["id"] for r in active]
        self.assertEqual(len(ids), len(set(ids)))  # no duplicates
        self.assertIn("deepseek-v4-flash", ids)
        self.assertIn("minimax-m3", ids)
        # tombstones are preserved, never deleted, and marked removed
        for tid in ("kimi-k2", "glm-4.6"):
            rec = reg.get(tid)
            self.assertIsNotNone(rec, f"tombstone {tid} must be preserved")
            self.assertEqual(rec["status"], "removed")
            self.assertFalse(rec["verified"]["ok"])
            self.assertIn("reason", rec["provenance"])
        self.assertEqual(len(reg), 27)
        # status='any' includes tombstones in capability filters
        self.assertEqual(len(core.filter_by_capability(status="any", tools=True)), 27)
        self.assertIn("kimi-k2", core.filter_by_capability(status="any", tools=True))

    def test_deepseek_v4_flash_context_1m_source_spec(self):
        reg = core.registry_load()
        self.assertEqual(core.context_window("deepseek-v4-flash", reg), 1_000_000)
        env = core.capability("deepseek-v4-flash", "context_window", reg)
        self.assertEqual(env["source"], "spec")
        self.assertIn("models.dev", env["origin"])      # provenance recorded
        self.assertIn("131072", env["origin"])          # old wrong value refuted, auditable

    def test_capability_unknown_returns_none(self):
        self.assertIsNone(core.capability("no-such-model"))
        self.assertIsNone(core.context_window("no-such-model"))

    def test_capability_full_record_fields(self):
        rec = core.capability("deepseek-v4-flash")
        for key in ("id", "name", "provider", "status", "context_window",
                    "capabilities", "cost_per_1m", "verified", "provenance"):
            self.assertIn(key, rec)
        self.assertEqual(rec["provider"], "opencode-zen")
        self.assertEqual(rec["status"], "active")
        self.assertTrue(rec["verified"]["ok"])
        self.assertTrue(rec["verified"]["date"])

    def test_enum_includes_always_thinking_and_video_in(self):
        self.assertIn("always_thinking", core.CAPABILITY_ENUM)
        self.assertIn("video_in", core.CAPABILITY_ENUM)
        self.assertIn("image_in", core.CAPABILITY_ENUM)
        self.assertEqual(len(core.CAPABILITY_ENUM), 6)

    def test_schema_version_mismatch_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bad.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"schema_version": "9.9.9", "models": []}, f)
            with self.assertRaises(ValueError):
                core.registry_load(p)


class CapabilityFilterTests(unittest.TestCase):
    """filter_by_capability / verified_capability semantics."""

    def test_filter_thinking_tools_all_active(self):
        picks = core.filter_by_capability(thinking=True, tools=True)
        self.assertEqual(len(picks), 25)  # every gateway model declares both
        self.assertIn("deepseek-v4-flash", picks)
        self.assertIn("grok-4.5", picks)

    def test_filter_image_in_models(self):
        picks = core.filter_by_capability(image_in=True)
        self.assertEqual(len(picks), 12)  # models.dev attachment intent labels
        self.assertIn("minimax-m3", picks)
        self.assertIn("gpt-5.6-luna", picks)
        self.assertNotIn("deepseek-v4-flash", picks)

    def test_verified_capability_vision_only_minimax(self):
        self.assertEqual(core.verified_capability("image_in"), ["minimax-m3"])

    def test_filter_video_in_models(self):
        picks = core.filter_by_capability(video_in=True)
        self.assertEqual(len(picks), 6)  # models.dev modalities: input includes video
        for mid in ("qwen3.8-max", "qwen3.7-plus", "qwen3.6-plus",
                    "qwen3.5-plus", "mimo-v2-omni", "mimo-v2.5"):
            self.assertIn(mid, picks)

    def test_filter_negative_and_unknown_raises(self):
        no_vision = core.filter_by_capability(image_in=False)
        self.assertNotIn("minimax-m3", no_vision)
        self.assertIn("deepseek-v4-flash", no_vision)
        with self.assertRaises(ValueError):
            core.filter_by_capability(telepathy=True)


class TextAndConflictTests(unittest.TestCase):
    """capabilities_text / conflict_report / recommend / summary."""

    def test_capabilities_text_rows_retired_filter(self):
        t = core.capabilities_text()
        self.assertIn("25 active, 25 verified, 2 retired/tombstoned", t)
        for col in ("ctx", "tools", "think", "vision", "video", "src"):
            self.assertIn(col, t)
        self.assertIn("1,000,000", t)            # deepseek-v4-flash ctx rendered
        self.assertIn("deepseek-v4-flash", t)
        self.assertIn("RETIRED (removed)", t)    # tombstones shown, not hidden
        self.assertIn("kimi-k2", t)
        # capability filter narrows rows; unknown capability raises
        ft = core.capabilities_text(cap_filter="image_in")
        self.assertIn("minimax-m3", ft)
        self.assertNotIn("\n  deepseek-v4-flash", ft)
        with self.assertRaises(ValueError):
            core.capabilities_text(cap_filter="telepathy")

    def test_conflict_report_clean_snapshot_and_bad_enum(self):
        self.assertEqual(core.conflict_report(), "conflict_report: OK")
        # snapshot diff: context mismatch + missing slug (F3 CI report style)
        snap = {
            "deepseek-v4-flash": {"context_window": 131072},
            "never-seen-model": {"context_window": 1000},
        }
        rep = core.conflict_report(snapshot=snap)
        self.assertIn("CTX deepseek-v4-flash: registry=1000000 snapshot=131072", rep)
        self.assertIn("(source=spec)", rep)
        self.assertIn("MISSING-SLUG never-seen-model", rep)
        # internal pass flags unknown enum values on inline registries
        bad = {
            "x": {"id": "x", "name": "X", "provider": "p", "status": "active",
                  "context_window": {"value": 100, "source": "spec", "origin": "o"},
                  "capabilities": ["telepathy"], "capability_sources": {"telepathy": "spec"},
                  "cost_per_1m": {"input": 0, "output": 0, "currency": "USD", "source": "verified"},
                  "verified": {"ok": True, "date": "d", "method": "m", "last_seen": "l"},
                  "provenance": {"primary": "curated", "updated_at": "u"}},
        }
        rep2 = core.conflict_report(bad)
        self.assertIn("CAPABILITY x: ['telepathy']", rep2)
        self.assertIn("issue(s)", rep2)

    def test_recommend_derived(self):
        self.assertEqual(core.recommend(), "deepseek-v4-flash")
        self.assertEqual(core.recommend("vision"), "minimax-m3")  # verified-first
        self.assertEqual(core.recommend("bogus-role"), core.recommend("default"))

    def test_summary_and_detail_text(self):
        s = core.registry_summary_text()
        self.assertIn("active: 25", s)
        self.assertIn("verified: 25", s)
        self.assertIn("removed: 2", s)
        self.assertIn("conflict_report: OK", s)
        d = core.model_detail_text("deepseek-v4-flash")
        self.assertIn("1,000,000", d)
        self.assertIn("(spec)", d)
        self.assertIn("provenance: curated", d)
        self.assertIn("no record for 'zzz'", core.model_detail_text("zzz"))


class DiffSinceTests(unittest.TestCase):
    """diff_since / diff_text — added/removed/changed vs a snapshot (backlog 21)."""

    @staticmethod
    def _snap_from_reg(reg):
        """Registry -> snapshot-map {slug: {status, context_window, max_output}}."""
        return {
            mid: {
                "status": r.get("status"),
                "context_window": (r.get("context_window") or {}).get("value"),
                "max_output": (r.get("max_output") or {}).get("value"),
            }
            for mid, r in reg.items()
        }

    def test_diff_empty_when_snapshot_matches(self):
        reg = core.registry_load()
        d = core.diff_since(self._snap_from_reg(reg), reg)
        self.assertEqual(d["added"], [])
        self.assertEqual(d["removed"], [])
        self.assertEqual(d["changed"], [])
        self.assertEqual(d["captured_at"], None)
        self.assertIn("no changes since snapshot", core.diff_text(self._snap_from_reg(reg), reg))

    def test_diff_changed_field_detected(self):
        reg = core.registry_load()
        snap = self._snap_from_reg(reg)
        snap["deepseek-v4-flash"]["context_window"] = 131072  # old curated value (F3)
        d = core.diff_since(snap, reg)
        self.assertEqual(d["added"], [])
        self.assertEqual(d["removed"], [])
        self.assertEqual(len(d["changed"]), 1)
        c = d["changed"][0]
        self.assertEqual(c["slug"], "deepseek-v4-flash")
        self.assertEqual(c["fields"], ["context"])
        self.assertEqual(c["from"], {"context": 131072})
        self.assertEqual(c["to"], {"context": 1_000_000})
        t = core.diff_text(snap, reg)
        self.assertIn("deepseek-v4-flash", t)
        self.assertIn("context 131,072 -> 1,000,000", t)
        self.assertIn("1 changed", t)

    def test_diff_removed_model_reported(self):
        reg = core.registry_load()
        snap = self._snap_from_reg(reg)
        # tombstone was active at capture time -> reported as removed w/ reason
        snap["kimi-k2"] = {"status": "active", "context_window": 131072}
        # snapshot slug with no registry record -> removed (gone entirely)
        snap["ghost-model"] = {"status": "active", "context_window": 1000}
        # drop a live model from the snapshot -> it becomes added
        del snap["grok-4.5"]
        d = core.diff_since(snap, reg)
        slugs = [r["slug"] for r in d["removed"]]
        self.assertIn("kimi-k2", slugs)
        self.assertIn("ghost-model", slugs)
        by_slug = {r["slug"]: r for r in d["removed"]}
        self.assertIn("superseded by kimi-k3", by_slug["kimi-k2"]["reason"])
        self.assertIsNone(by_slug["ghost-model"]["reason"])
        self.assertIn("grok-4.5", d["added"])
        t = core.diff_text(snap, reg)
        self.assertIn("- kimi-k2", t)
        self.assertIn("- ghost-model (gone from registry)", t)
        self.assertIn("+ grok-4.5", t)


class ModelsDevRefreshTests(unittest.TestCase):
    """refresh_from_models_dev / snapshot_load (fetch mocked via urlopen patch)."""

    PAYLOAD = {
        "testprov": {
            "id": "testprov", "name": "Test Prov",
            "models": {
                "deepseek-v4-flash": {"id": "deepseek-v4-flash",
                                      "limit": {"context": 1048576, "output": 1048576}},
                "deepseek-v4-pro": {"id": "deepseek-v4-pro",
                                    "limit": {"context": 1048576, "output": 1048576}},
                "no-such-model": {"id": "no-such-model",
                                  "limit": {"context": 1000, "output": 1000}},
            },
        }
    }

    def _registry_copy(self, tmpdir):
        """Two-model registry (flash ctx 1M != models.dev, pro ctx == models.dev)."""
        reg = core.registry_load()
        models = [copy.deepcopy(reg["deepseek-v4-flash"]),
                  copy.deepcopy(reg["deepseek-v4-pro"])]
        p = os.path.join(tmpdir, "capabilities.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"schema_version": "1.0.0", "sources": [], "models": models},
                      f, indent=2)
        return p

    @staticmethod
    def _patch_fetch(payload):
        raw = json.dumps(payload).encode("utf-8")
        return mock.patch("urllib.request.urlopen", return_value=io.BytesIO(raw))

    def test_refresh_verified_conflict_snapshot_and_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            data_path = self._registry_copy(d)
            snap_path = os.path.join(d, "models.snapshot.json")
            with self._patch_fetch(self.PAYLOAD):
                rep = core.refresh_from_models_dev(data_path=data_path,
                                                   out_snapshot=snap_path)
            reg = core.registry_load(data_path)
            # agreeing field -> verified with auditable provenance origin
            self.assertEqual(reg["deepseek-v4-pro"]["context_window"]["source"], "verified")
            self.assertIn("models.dev live refresh", reg["deepseek-v4-pro"]["context_window"]["origin"])
            self.assertIn("confirmed", reg["deepseek-v4-pro"]["context_window"]["origin"])
            # disagreeing field -> left at spec value, flagged not auto-accepted
            self.assertEqual(reg["deepseek-v4-flash"]["context_window"]["source"], "spec")
            self.assertEqual(reg["deepseek-v4-flash"]["context_window"]["value"], 1_000_000)
            self.assertIn("!=", reg["deepseek-v4-flash"]["context_window"]["origin"])
            self.assertIn("deepseek-v4-pro", rep["verified"])
            self.assertEqual(rep["conflicts"], ["deepseek-v4-flash"])
            self.assertEqual(rep["matched"], 2)
            self.assertEqual(rep["total_slugs"], 3)
            # capabilities.json extended with snapshot_id + refreshed_at
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["snapshot_id"], rep["snapshot_id"])
            self.assertTrue(data["refreshed_at"])
            # snapshot pinned: matched slugs only, no unknowns
            with open(snap_path, encoding="utf-8") as f:
                snap = json.load(f)
            self.assertEqual(snap["snapshot_id"], rep["snapshot_id"])
            self.assertEqual(snap["matched"], 2)
            self.assertIn("deepseek-v4-flash", snap["models"])
            self.assertNotIn("no-such-model", snap["models"])
            self.assertEqual(snap["models"]["deepseek-v4-pro"]["context_window"], 1048576)
            # conflict_report against the pinned snapshot surfaces the CTX diff
            report = core.conflict_report(registry=reg, snapshot=core.snapshot_load(snap_path))
            self.assertIn("CTX deepseek-v4-flash: registry=1000000 snapshot=1048576", report)
            self.assertIn("(source=spec)", report)

    def test_refresh_network_failure_raises(self):
        with tempfile.TemporaryDirectory() as d:
            data_path = self._registry_copy(d)
            with mock.patch("urllib.request.urlopen",
                            side_effect=urllib.error.URLError("boom")):
                with self.assertRaises(urllib.error.URLError):
                    core.refresh_from_models_dev(data_path=data_path)

    def test_refresh_flat_payload_zero_matches(self):
        with tempfile.TemporaryDirectory() as d:
            data_path = self._registry_copy(d)
            snap_path = os.path.join(d, "models.snapshot.json")
            flat = {"some-other-model": {"limit": {"context": 5, "output": 5}}}
            with self._patch_fetch(flat):
                rep = core.refresh_from_models_dev(data_path=data_path,
                                                   out_snapshot=snap_path)
            self.assertEqual(rep["matched"], 0)
            with open(snap_path, encoding="utf-8") as f:
                snap = json.load(f)
            self.assertEqual(snap["models"], {})

    def test_snapshot_load_shape_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "models.snapshot.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"snapshot_id": "abc", "models": {
                    "m1": {"context_window": 100, "max_output": 50, "name": "M1"}}}, f)
            with open(p, encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(
                core.snapshot_load(p),
                {"m1": {"context_window": 100, "max_output": 50}},
            )
            self.assertEqual(core.snapshot_load(os.path.join(d, "nope.json")), {})


if __name__ == "__main__":
    unittest.main()
