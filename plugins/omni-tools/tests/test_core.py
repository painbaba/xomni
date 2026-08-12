"""omni-tools test suite — pure stdlib, no network, no host imports.

Run:  python -m unittest tests.test_core -q
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core  # noqa: E402


def _entry(name, source="mcp", kind="mcp_server", description="", category=""):
    return {
        "source": source, "kind": kind, "name": name,
        "description": description, "category": category, "status": "catalog",
        "hint": "hint", "id": f"{source}:{kind}:{name}:0",
    }


def _planted_corpus():
    """Synthetic corpus across all kinds with distinctive vocab."""
    docs = [
        _entry("describe_image", "plugin", "tool",
               "Read a local image file and produce a detailed vision model description"),
        _entry("fetch_page", "plugin", "tool",
               "Fetch a web page over http and return clean readable text"),
        _entry("playwright", "mcp", "mcp_server",
               "Browser automation and web scraping with headless chromium"),
        _entry("sqlite-server", "mcp", "mcp_server",
               "SQLite database queries, local db files, sql statements"),
        _entry("memory-consolidate", "plugin", "command",
               "Consolidate short term memories into long term recall store"),
        _entry("youtube-transcript", "mcp", "mcp_server",
               "YouTube video transcripts and subtitles as text"),
        _entry("pdf", "skill", "skill", "Create merge split fill and secure PDF files"),
        _entry("gh", "plugin", "command",
               "GitHub workflows via the gh cli: pull requests, issues, auth"),
        _entry("cloudflare", "mcp", "mcp_server",
               "Cloudflare workers deploy and DNS management"),
        _entry("web-search", "mcp", "mcp_server",
               "Search the web, retrieve pages, find answers"),
        _entry("mediascan", "plugin", "command",
               "Scan a media directory and caption images, ocr text"),
        _entry("image-magick", "mcp", "mcp_server",
               "Convert and process image files, resize and crop"),
        _entry("browser-ctrl", "skill", "skill",
               "Control a browser, fill forms, take screenshots"),
        _entry("db-query", "plugin", "tool", "Run sql queries against a database"),
        _entry("vector-memory", "mcp", "mcp_server",
               "Persistent embedding memory that survives across sessions"),
        _entry("video-edit", "skill", "skill",
               "Cut trim transcode video clips with ffmpeg"),
        _entry("doc-parser", "mcp", "mcp_server",
               "Parse pdf documents and extract tables and text"),
        _entry("deploy-ctl", "plugin", "tool",
               "Deploy workers to the cloud, manage serverless functions"),
        _entry("search-api", "skill", "skill",
               "Call a search engine api to find documents and pages"),
        _entry("ffmpeg", "mcp", "mcp_server",
               "Video audio processing clip transcode extract frames"),
        _entry("caption", "plugin", "command",
               "Generate image captions with the vision model"),
        _entry("ocr", "plugin", "command", "Extract text from images with ocr"),
        _entry("slides", "skill", "skill",
               "Build slide decks and presentations from outlines"),
        _entry("geocode", "mcp", "mcp_server",
               "Geocode addresses to coordinates with openstreetmap"),
        _entry("notion", "mcp", "mcp_server",
               "Read and write Notion pages and databases"),
        _entry("spreadsheet", "skill", "skill",
               "Create and edit excel xlsx spreadsheets and csv files"),
    ]
    for i, e in enumerate(docs):
        e["id"] = f"{e['source']}:{e['kind']}:{e['name']}:{i}"
    return docs


_PLANTED_QUERIES = [
    ("describe image vision", "describe_image"),
    ("browser automation", "playwright"),
    ("sqlite query database", "sqlite-server"),
    ("consolidate memory recall", "memory-consolidate"),
    ("youtube transcript", "youtube-transcript"),
    ("merge split pdf", "pdf"),
    ("github pull request", "gh"),
    ("deploy cloudflare worker", "cloudflare"),
    ("search web engine", "web-search"),
    ("scan media captions", "mediascan"),
]


# Ground truth verified against the live corpus on 2026-08-12 (see build report).
_REAL_QUERIES = [
    ("vision image describe", "describe_image"),
    ("browser automation web scraping", "playwright"),
    ("sqlite database query", "sqlite"),
    ("youtube transcript subtitles", "youtube-transcript"),
    ("memory consolidate recall", "memory-consolidate"),
    ("mcp server catalog add", "mcp add"),
    ("pdf extract document", "pdf"),
    ("picture photo visual", "describe_image"),
    ("web scraping dom", "playwright"),
    ("cloudflare workers deploy", "cloudflare"),
    ("ocr scan text", "ocr"),
    ("video transcript", "youtube-transcript"),
]


class TestTokenize(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(core.tokenize("Vision Image Describe!"), ["vision", "image", "describe"])
        # stopwords + 1-char tokens dropped
        self.assertEqual(core.tokenize("a the of to x vision"), ["vision"])
        self.assertEqual(core.tokenize(""), [])
        self.assertEqual(core.tokenize("   "), [])


class TestBM25(unittest.TestCase):
    def _index(self, docs):
        return core.BM25().index([(d["id"], core.tokenize(d["name"] + " " + d["description"])) for d in docs])

    def test_bm25_ranks_relevant_first(self):
        docs = [
            _entry("alpha", description="red apples and orange fruit"),
            _entry("beta", description="blue sky and red sunset"),
            _entry("gamma", description="green leaves on trees"),
        ]
        bm25 = self._index(docs)
        hits = bm25.search(core.tokenize("red fruit"), limit=3)
        self.assertEqual(hits[0][0], docs[0]["id"])  # most relevant first
        self.assertEqual(len(hits), 2)  # gamma has no query term

    def test_bm25_edge_cases(self):
        # empty corpus -> no hits
        bm25 = self._index([])
        self.assertEqual(bm25.search(["anything"]), [])
        # empty query -> no hits
        docs = [_entry("alpha", description="red apples")]
        bm25 = self._index(docs)
        self.assertEqual(bm25.search([]), [])
        # ties resolve deterministically by doc_id
        docs = [_entry("beta", description="red red red"), _entry("alpha", description="red red red")]
        bm25 = self._index(docs)
        hits = bm25.search(["red"], limit=5)
        self.assertEqual([h[0] for h in hits], [d["id"] for d in sorted(docs, key=lambda d: d["id"])])


class TestCorpusCoverage(unittest.TestCase):
    """The three surfaces TOOL-SEARCH.md indexes, on the real repo data."""

    @classmethod
    def setUpClass(cls):
        cls.index = core.rebuild(use_cache=False)

    def test_mcp_catalog_coverage(self):
        mcp = [e for e in self.index.corpus if e["source"] == "mcp"]
        self.assertGreaterEqual(len(mcp), 300, f"expected >=300 MCP servers, got {len(mcp)}")

    def test_skills_coverage(self):
        skills = [e for e in self.index.corpus if e["source"] == "skill"]
        self.assertGreaterEqual(len(skills), 150, f"expected >=150 skills, got {len(skills)}")

    def test_plugin_surface_coverage(self):
        plugins = [e for e in self.index.corpus if e["source"] == "plugin"]
        self.assertGreaterEqual(len(plugins), 60, f"expected >=60 plugin surfaces, got {len(plugins)}")
        kinds = {e["kind"] for e in plugins}
        self.assertTrue({"tool", "command"} <= kinds, f"plugin surfaces must include tools+commands: {kinds}")

    def test_corpus_total_and_stats(self):
        stats = self.index.stats()
        self.assertGreaterEqual(stats["total"], 510)
        self.assertEqual(stats["by_source"]["mcp"], stats["by_kind"]["mcp_server"])
        self.assertEqual(
            stats["by_source"]["skill"], stats["by_kind"]["skill"]
        )


class TestSearchBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = core.rebuild(use_cache=False)

    def test_search_kind_filter(self):
        idx = self.index
        expected_source = {"skill": "skill", "mcp_server": "mcp", "tool": "plugin", "command": "plugin"}
        for kind in ("skill", "command", "mcp_server", "tool"):
            res = idx.search("image", kind=kind, limit=10)
            self.assertTrue(res, f"no results for kind={kind}")
            for r in res:
                self.assertEqual(r["kind"], kind)
                self.assertEqual(r["source"], expected_source[kind])
        # 'all' returns mixed sources
        res = idx.search("image", kind="all", limit=10)
        self.assertGreater(len({r["source"] for r in res}), 1)

    def test_search_limit_and_empty_query(self):
        res = self.index.search("video", limit=3)
        self.assertLessEqual(len(res), 3)
        self.assertEqual([r["rank"] for r in res], [1, 2, 3])
        self.assertEqual(self.index.search(""), [])
        self.assertEqual(self.index.search("   !!!"), [])

    def test_name_substring_fallback(self):
        # Doc whose token stream has NO overlap with the query token, but whose
        # name contains it -> the zero-IDF name-substring fallback must fire.
        doc = _entry("zzqzx-special", source="plugin", kind="command",
                     description="completely unrelated words here")
        doc["_keywords"] = ["unrelated", "words", "completely"]
        idx = core.ToolSearchIndex([doc] + _planted_corpus())
        res = idx.search("qzx", limit=5)
        self.assertTrue(any(r["name"] == "zzqzx-special" for r in res),
                        f"substring fallback failed: {[r['name'] for r in res]}")

    def test_deterministic_ordering(self):
        q = "database query"
        first = [r["name"] for r in self.index.search(q, limit=10)]
        second = [r["name"] for r in self.index.search(q, limit=10)]
        self.assertEqual(first, second)
        rebuilt = core.rebuild(use_cache=False)
        third = [r["name"] for r in rebuilt.search(q, limit=10)]
        self.assertEqual(first, third)


class TestRecall(unittest.TestCase):
    def test_top5_recall_planted(self):
        idx = core.ToolSearchIndex(_planted_corpus())
        hits = 0
        for query, expected in _PLANTED_QUERIES:
            names = [r["name"] for r in idx.search(query, limit=5)]
            if any(expected in n for n in names):
                hits += 1
        recall = hits / len(_PLANTED_QUERIES)
        self.assertGreaterEqual(recall, 0.9, f"planted top-5 recall {recall:.2f} < 0.9")

    def test_top5_recall_real(self):
        idx = core.rebuild(use_cache=False)
        hits = 0
        for query, expected in _REAL_QUERIES:
            names = [r["name"] for r in idx.search(query, limit=5)]
            if any(expected in n for n in names):
                hits += 1
        recall = hits / len(_REAL_QUERIES)
        self.assertGreaterEqual(recall, 0.9, f"real-corpus top-5 recall {recall:.2f} < 0.9 "
                                             f"({hits}/{len(_REAL_QUERIES)})")


class TestEvalRecall(unittest.TestCase):
    """Backlog 04: built-in eval set + core.eval_recall() + /tools-stats."""

    @classmethod
    def setUpClass(cls):
        cls.idx = core.rebuild(use_cache=False)

    def test_eval_recall_runs(self):
        ev = core.eval_recall(index=self.idx)
        self.assertIsInstance(ev, dict)
        self.assertGreaterEqual(len(core.EVAL_SET), 20,
                                f"built-in eval set must have ~20 queries, got {len(core.EVAL_SET)}")
        self.assertEqual(ev["queries"], len(core.EVAL_SET))
        self.assertTrue(0.0 <= ev["recall"] <= 1.0)
        self.assertLessEqual(ev["hits"], ev["queries"])
        self.assertTrue(ev["last_eval"], "last_eval timestamp must be set")
        self.assertEqual(len(ev["results"]), len(core.EVAL_SET))
        # every expected hit must be findable in the corpus (sanity: no typos)
        corpus_names = [e["name"].lower() for e in self.idx.corpus]
        for query, expected in core.EVAL_SET:
            self.assertTrue(
                any(expected.lower() in n for n in corpus_names),
                f"eval target {expected!r} (query {query!r}) not in corpus",
            )

    def test_eval_recall_planted_set(self):
        ev = core.eval_recall(index=self.idx)
        self.assertGreaterEqual(
            ev["recall"], 0.9,
            f"built-in eval set top-5 recall {ev['recall']:.2f} < 0.9 "
            f"({ev['hits']}/{ev['queries']})",
        )

    def test_eval_persist_and_stats_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cache.sqlite3"
            ev = core.eval_recall(index=self.idx, persist=True, cache_path=db)
            loaded = core.load_eval(db)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["hits"], ev["hits"])
            self.assertAlmostEqual(loaded["recall"], ev["recall"], places=6)
            self.assertEqual(loaded["last_eval"], ev["last_eval"])
            # /tools-stats rendering: corpus size + recall + last eval time
            report = core.stats_report(index=self.idx)
            self.assertIn("corpus:", report)
            self.assertIn("recall:", report)
            self.assertIn("last eval:", report)
            self.assertIn(str(ev["recall"])[:5], report)


class TestRouterTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx = core.rebuild(use_cache=False)

    def test_xomni_capabilities_router(self):
        out = core.xomni_capabilities("video", index=self.idx)
        self.assertIn("top", out)
        self.assertIn("[mcp:", out)  # source tag on hits
        self.assertIn("status=", out)  # status on hits
        # load hints present on every hit (skill_view / mcp add / tool_describe)
        hint_markers = ("skill_view", "/mcp add", "tool_describe", "run /")
        self.assertTrue(
            any(m in out for m in hint_markers),
            f"expected a load hint in router output: {out[:200]}",
        )
        lines = out.splitlines()[1:]
        self.assertGreaterEqual(len(lines), 1)

    def test_xomni_capabilities_args(self):
        out = core.xomni_capabilities("video", kind="skill", limit=1, index=self.idx)
        lines = out.splitlines()[1:]
        self.assertEqual(len(lines), 1)
        self.assertIn("[skill:skill]", lines[0])
        # limit clamps to [1, 20]
        out = core.xomni_capabilities("video", limit=0, index=self.idx)
        self.assertEqual(len(out.splitlines()[1:]), 1)
        out = core.xomni_capabilities("video", limit=999, index=self.idx)
        self.assertLessEqual(len(out.splitlines()[1:]), 20)
        # no-match message (token absent from corpus + no name substring)
        out = core.xomni_capabilities("zzzzzqxyz", index=self.idx)
        self.assertIn("no matches", out)

    def test_vision_query_spec(self):
        """Spec check: 'vision' must surface context-loader/omni-media plugin
        surfaces AND MCP servers in one result set."""
        res = self.idx.search("vision", limit=10)
        sources = {r["source"] for r in res}
        self.assertIn("mcp", sources)
        self.assertIn("plugin", sources)
        plugin_names = {r["name"] for r in res if r["source"] == "plugin"}
        self.assertTrue(
            plugin_names & {"describe_image", "describe", "caption", "mediascan", "ocr"},
            f"expected context-loader/omni-media surfaces in 'vision' results: {plugin_names}",
        )


class TestCache(unittest.TestCase):
    def test_sqlite_cache_roundtrip(self):
        corpus = _planted_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cache.sqlite3"
            mtimes = {"a": 1.0, "b": 2.0}
            core.save_cache(db, corpus, mtimes)
            loaded = core.load_cache(db, mtimes)
            self.assertIsNotNone(loaded)
            self.assertEqual([e["id"] for e in loaded], [e["id"] for e in corpus])
            self.assertEqual(loaded[0]["name"], corpus[0]["name"])
            # stale mtimes -> cache invalidated
            self.assertIsNone(core.load_cache(db, {"a": 9.0, "b": 2.0}))
            # missing file -> None
            self.assertIsNone(core.load_cache(Path(tmp) / "nope.sqlite3", mtimes))

    def test_rebuild_uses_cache_when_fresh(self):
        corpus = _planted_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mcp_file = tmp / "mcp.json"
            skills_file = tmp / "skills.json"
            mcp_file.write_text("[]")
            skills_file.write_text("[]")
            db = tmp / "cache.sqlite3"
            mtimes = core._source_mtimes(tmp, mcp_file, skills_file)
            core.save_cache(db, corpus, mtimes)
            idx = core.rebuild(
                use_cache=True, cache_path=db,
                plugins_dir=tmp, mcp_path=mcp_file, skills_path=skills_file,
            )
            self.assertEqual(idx.stats()["total"], len(corpus))


class TestCrossSurfaceEval(unittest.TestCase):
    """Cross-surface recall eval: 50 mixed-surface cases + runner."""

    @classmethod
    def setUpClass(cls):
        cls.cases_path = Path(core.__file__).resolve().parent / "data" / "cross_surface_eval.json"
        cls.cases = json.loads(cls.cases_path.read_text(encoding="utf-8"))

    def test_exactly_50_cases_with_valid_ids(self):
        self.assertEqual(len(self.cases), 50)
        ids = [c["id"] for c in self.cases]
        self.assertEqual(len(set(ids)), 50, "case ids must be unique")
        self.assertEqual(sorted(ids), ids, "case ids must be ordered cs001..cs050")
        self.assertEqual(ids[0], "cs001")
        self.assertEqual(ids[-1], "cs050")

    def test_case_schema_valid(self):
        surfaces = {"plugin", "mcp", "skill", "mixed"}
        for c in self.cases:
            self.assertIn(c["surface"], surfaces, f"{c['id']}: bad surface")
            self.assertIsInstance(c["query"], str)
            self.assertTrue(c["query"].strip(), f"{c['id']}: empty query")
            hits = c["expected_hits"]
            self.assertIsInstance(hits, list, f"{c['id']}: expected_hits must be a list")
            self.assertTrue(1 <= len(hits) <= 3, f"{c['id']}: 1-3 expected hits")
            for h in hits:
                self.assertIsInstance(h, str)
                self.assertTrue(h.strip(), f"{c['id']}: empty expected hit")

    def test_surface_mix_is_balanced(self):
        counts = {}
        for c in self.cases:
            counts[c["surface"]] = counts.get(c["surface"], 0) + 1
        self.assertGreaterEqual(counts.get("plugin", 0), 8)
        self.assertGreaterEqual(counts.get("mcp", 0), 8)
        self.assertGreaterEqual(counts.get("skill", 0), 8)
        self.assertGreaterEqual(counts.get("mixed", 0), 8)

    def test_runner_returns_recall_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            ev = core.cross_surface_recall(
                cases_path=self.cases_path, top_k=5, report_path=report
            )
            self.assertEqual(ev["queries"], 50)
            self.assertEqual(ev["top_k"], 5)
            self.assertEqual(len(ev["per_case"]), 50)
            self.assertGreaterEqual(ev["overall_recall"], 0.0)
            self.assertLessEqual(ev["overall_recall"], 1.0)
            self.assertIn("plugin", ev["per_surface"])
            self.assertIn("mcp", ev["per_surface"])
            self.assertIn("skill", ev["per_surface"])
            self.assertIn("mixed", ev["per_surface"])
            for surface, stats in ev["per_surface"].items():
                self.assertGreaterEqual(stats["recall"], 0.0)
                self.assertLessEqual(stats["recall"], 1.0)
            self.assertTrue(report.exists(), "report file must be written")
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["overall_recall"], ev["overall_recall"])

    def test_runner_degrades_gracefully_with_missing_data(self):
        # A missing MCP catalog / skills file must score 0 for those surfaces
        # instead of crashing the run.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake = tmp / "does-not-exist.json"
            cases_file = tmp / "cases.json"
            cases_file.write_text(
                json.dumps([
                    {"id": "cs001", "query": "sqlite database", "surface": "mcp",
                     "expected_hits": ["sqlite"]},
                    {"id": "cs002", "query": "pdf document", "surface": "skill",
                     "expected_hits": ["pdf"]},
                    {"id": "cs003", "query": "compress context", "surface": "plugin",
                     "expected_hits": ["ctxcompact"]},
                ]),
                encoding="utf-8",
            )
            ev = core.cross_surface_recall(
                cases_path=cases_file, top_k=5,
                report_path=tmp / "report.json",
                mcp_path=fake, skills_path=fake,
                plugins_dir=tmp,  # empty dir: no plugin surfaces
            )
            self.assertEqual(ev["queries"], 3)
            self.assertFalse(ev["sources_loaded"]["mcp"])
            self.assertFalse(ev["sources_loaded"]["skill"])
            self.assertGreaterEqual(ev["overall_recall"], 0.0)
            self.assertLessEqual(ev["overall_recall"], 1.0)
            # mcp + skill surfaces have zero loaded entries -> recall 0
            self.assertEqual(ev["per_surface"]["mcp"]["recall"], 0.0)
            self.assertEqual(ev["per_surface"]["skill"]["recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
