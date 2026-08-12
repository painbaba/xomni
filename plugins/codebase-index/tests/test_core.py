"""Tests for the hybrid codebase index engine (core.py) + zero-hook surface."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

import core


def _tree(files: dict[str, str]) -> str:
    d = tempfile.mkdtemp()
    for rel, content in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    return d


class CodebaseIndexTests(unittest.TestCase):
    def _repo(self, files: dict[str, str]) -> tuple[str, str]:
        """Return (root, db_path) with a freshly built index."""
        root = _tree(files)
        db = os.path.join(tempfile.mkdtemp(), "index.db")
        core.update_index(root, db_path=db)
        return root, db

    # ---- build / schema ------------------------------------------------- #

    def test_build_creates_full_schema(self):
        root, db = self._repo({"a.py": "def f():\n    pass\n"})
        conn = core._connect(db)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','virtual')")}
            for t in ("files", "meta", "symbols", "chunks", "fts", "fts_meta",
                      "vectors"):
                self.assertIn(t, tables)
            self.assertEqual(core._meta(conn, "schema_version"), core.SCHEMA_VERSION)
            self.assertEqual(core._meta(conn, "embedding_model"), "none")
        finally:
            conn.close()

    def test_build_indexes_files_symbols_chunks(self):
        root, db = self._repo({
            "app.py": "class Server:\n    pass\n\ndef main():\n    pass\n",
            "notes.md": "# notes\nsome text here\n",
        })
        st = core.index_status(root, db_path=db)
        self.assertEqual(st["file_count"], 2)
        self.assertEqual(st["symbol_count"], 2)
        self.assertGreaterEqual(st["chunk_count"], 2)
        conn = core._connect(db)
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM fts_meta").fetchone()[0],
                st["chunk_count"])
        finally:
            conn.close()

    def test_symbols_have_lines_and_kinds(self):
        root, db = self._repo({
            "app.py": "import os\n\ndef main():\n    pass\n\nclass Server:\n    pass\n",
        })
        conn = core._connect(db)
        try:
            rows = {r["name"]: (r["line"], r["kind"])
                    for r in conn.execute("SELECT name,line,kind FROM symbols")}
        finally:
            conn.close()
        self.assertEqual(rows["main"], (3, "function"))
        self.assertEqual(rows["Server"], (6, "type"))

    def test_chunks_respect_symbol_boundaries(self):
        root, db = self._repo({
            "a.py": "class A:\n    x = 1\n\ndef f():\n    pass\n",
        })
        conn = core._connect(db)
        try:
            chunks = [tuple(r) for r in conn.execute(
                "SELECT start_line,end_line FROM chunks ORDER BY idx")]
        finally:
            conn.close()
        self.assertEqual(chunks, [(1, 3), (4, 5)])  # preamble ends before def f

    # ---- incrementality ------------------------------------------------- #

    def test_incremental_noop_on_unchanged(self):
        root, db = self._repo({"a.py": "def f():\n    pass\n"})
        before = core.index_status(root, db_path=db)["rebuilt_at"]
        st = core.update_index(root, db_path=db)
        self.assertEqual((st["added"], st["updated"], st["removed"]), (0, 0, 0))
        self.assertEqual(core.index_status(root, db_path=db)["rebuilt_at"], before)

    def test_mtime_touch_content_same_is_noop(self):
        root, db = self._repo({"a.py": "def f():\n    pass\n"})
        p = os.path.join(root, "a.py")
        st_old = os.stat(p)
        os.utime(p, (st_old.st_atime + 500, st_old.st_mtime + 500))
        st = core.update_index(root, db_path=db)
        self.assertEqual(st["updated"], 0)
        self.assertEqual(st["unchanged"], 1)  # sha256 dedup: no re-parse
        self.assertEqual(st["removed"], 0)

    def test_edit_reindexes_content(self):
        root, db = self._repo({"a.py": "def old_name():\n    pass\n"})
        with open(os.path.join(root, "a.py"), "w", encoding="utf-8") as f:
            f.write("def brand_new_symbol():\n    pass\n")
        st = core.update_index(root, db_path=db)
        self.assertEqual(st["updated"], 1)
        self.assertIn("brand_new_symbol", core.search_symbols(root, "brand_new", db_path=db))
        self.assertNotIn("old_name", core.search_symbols(root, "old_name", db_path=db))

    def test_deleted_file_removed(self):
        root, db = self._repo({"keep.py": "def keep():\n    pass\n",
                               "gone.py": "def goner():\n    pass\n"})
        os.remove(os.path.join(root, "gone.py"))
        st = core.update_index(root, db_path=db)
        self.assertEqual(st["removed"], 1)
        self.assertEqual(core.index_status(root, db_path=db)["file_count"], 1)
        self.assertNotIn("goner", core.search_symbols(root, "goner", db_path=db))

    def test_skips_noise_dirs(self):
        root, db = self._repo({
            "src/real.py": "def real():\n    pass\n",
            ".git/hooks/x.py": "def fake():\n    pass\n",
            "node_modules/lib/y.py": "def fake2():\n    pass\n",
            "dist/bundle.py": "def fake3():\n    pass\n",
        })
        st = core.index_status(root, db_path=db)
        self.assertEqual(st["file_count"], 1)
        hits = core.search_symbols(root, "fake", db_path=db)
        self.assertNotIn("fake", hits)
        self.assertIn("real", core.search_symbols(root, "real", db_path=db))

    # ---- ranking --------------------------------------------------------- #

    def test_bm25_ranks_relevant_file_first(self):
        root, db = self._repo({
            "dense.py": "def alpha():\n    # alpha alpha alpha alpha\n    return 'alpha'\n",
            "sparse.py": "def beta():\n    # alpha mentioned once\n    pass\n",
        })
        out = core.rank_files(root, "alpha", db_path=db)
        self.assertIn("dense.py", out)
        self.assertIn("sparse.py", out)
        self.assertLess(out.index("dense.py"), out.index("sparse.py"))

    def test_symbol_boost_outranks_incidental_match(self):
        root, db = self._repo({
            "authsvc.py": "def auth_token():\n    return 'x'\n",
            "util.py": "def helper():\n    # auth auth auth auth\n    pass\n",
        })
        out = core.rank_files(root, "auth", db_path=db)
        self.assertLess(out.index("authsvc.py"), out.index("util.py"))

    def test_path_weight_outranks_content_match(self):
        root, db = self._repo({
            "zebra_query.py": "def nothing():\n    pass\n",   # path match only
            "other.py": "def h():\n    # zebra_query\n    pass\n",  # content match
        })
        out = core.rank_files(root, "zebra_query", db_path=db)
        self.assertLess(out.index("zebra_query.py"), out.index("other.py"))

    # ---- symbol search --------------------------------------------------- #

    def test_search_symbols_prefix_then_substring(self):
        root, db = self._repo({
            "tok.py": "def tokenizer():\n    pass\n\ndef tokens():\n    pass\n",
            "util.py": "def get_token_ref():\n    pass\n",
        })
        out = core.search_symbols(root, "token", db_path=db)
        self.assertIn("tokenizer", out)
        self.assertIn("tokens", out)
        self.assertIn("get_token_ref", out)   # substring hit included
        self.assertIn("tok.py:1", out)        # "path:line" format
        # short terms (<3 chars) can't hit the trigram FTS but resolve via symbols
        root2, db2 = self._repo({"sql.py": "def f5_handler():\n    pass\n"})
        out2 = core.search_symbols(root2, "f5", db_path=db2)
        self.assertIn("f5_handler", out2)
        self.assertIn("sql.py", core.rank_files(root2, "f5", db_path=db2))

    # ---- unified query / status / freshness ----------------------------- #

    def test_query_renders_files_and_symbols(self):
        root, db = self._repo({
            "app.py": "class Server:\n    pass\n\ndef handle():\n    pass\n",
        })
        out = core.query(root, "server", db_path=db)
        self.assertIn("index:", out)
        self.assertIn("ranked files", out)
        self.assertIn("app.py", out)
        self.assertIn("symbol hits", out)
        self.assertIn("Server", out)

    def test_query_json_parses_and_roundtrips(self):
        root, db = self._repo({
            "app.py": "class Server:\n    pass\n\ndef handle():\n    pass\n",
            "util.py": "def server_util():\n    pass\n",
        })
        hits = core.query_json(root, "server", db_path=db)
        self.assertIsInstance(hits, list)
        data = json.loads(json.dumps(hits))  # machine-readable round-trip
        self.assertTrue(data)
        kinds = {h["type"] for h in data}
        self.assertIn("file", kinds)
        self.assertIn("symbol", kinds)
        for h in data:
            self.assertIn("path", h)
            if h["type"] == "symbol":
                self.assertIn("name", h)
                self.assertIn("line", h)
                self.assertIn("kind", h)

    def test_query_json_top_respected(self):
        root, db = self._repo({
            f"f{i}.py": f"def fn{i}():\n    # alpha\n    pass\n" for i in range(15)
        })
        hits = core.query_json(root, "alpha", top_n=3, db_path=db)
        file_hits = [h for h in hits if h["type"] == "file"]
        self.assertLessEqual(len(file_hits), 3)
        self.assertLessEqual(len(hits) - len(file_hits), 3)  # symbols capped too

    def test_query_json_symbols_only_filters(self):
        root, db = self._repo({
            "app.py": "class Server:\n    pass\n\ndef handle():\n    pass\n",
            "notes.md": "# server notes\nserver server server\n",
        })
        hits = core.query_json(root, "server", symbols_only=True, db_path=db)
        self.assertTrue(hits)
        for h in hits:
            self.assertEqual(h["type"], "symbol")  # no file rows
            self.assertIn("name", h)
        # text-only file (no symbols) is excluded by the filter
        self.assertNotIn("notes.md", [h["path"] for h in hits])
        # plain query still surfaces the text file
        plain = core.query_json(root, "server", db_path=db)
        self.assertIn("notes.md", [h["path"] for h in plain if h["type"] == "file"])

    def test_index_status_shape_and_dirty(self):
        root, db = self._repo({"a.py": "def f():\n    pass\n"})
        st = core.index_status(root, db_path=db)
        for k in ("db_path", "exists", "file_count", "symbol_count", "chunk_count",
                  "dirty_count", "indexed_at", "embedding_model", "git_head"):
            self.assertIn(k, st)
        self.assertTrue(st["exists"])
        self.assertEqual(st["dirty_count"], 0)
        os.utime(os.path.join(root, "a.py"), (1e9, 1e9))  # mtime moved
        self.assertEqual(core.index_status(root, db_path=db)["dirty_count"], 1)

    def test_deferred_banner_when_dirty_large(self):
        root, db = self._repo({f"f{i}.py": f"def fn{i}():\n    pass\n" for i in range(5)})
        for i in range(3):  # touch 3 files with new content
            with open(os.path.join(root, f"f{i}.py"), "w", encoding="utf-8") as f:
                f.write(f"def fn{i}_changed():\n    pass\n")
        old = core.MAX_DIRTY_DEFER
        core.MAX_DIRTY_DEFER = 2   # make the query path defer on 3 dirty files
        try:
            st = core.update_index(root, db_path=db)
            self.assertTrue(st["deferred"])
            self.assertIn("pending", st["banner"])
            out = core.query(root, "fn2", db_path=db)   # serves stale + banner
            self.assertIn("pending re-index", out)
        finally:
            core.MAX_DIRTY_DEFER = old
        st2 = core.update_index(root, db_path=db, max_dirty=100)  # now refresh
        self.assertEqual(st2["updated"], 3)
        self.assertIn("fn2_changed", core.search_symbols(root, "fn2_changed", db_path=db))

    def test_build_map_from_index(self):
        root, db = self._repo({
            "pkg/__init__.py": "",
            "pkg/app.py": "class Server:\n    pass\n\ndef main():\n    pass\n",
        })
        m = core.build_map(root, db_path=db)
        self.assertIn("pkg/app.py", m)
        self.assertIn("Server", m)
        self.assertIn("main", m)
        self.assertIn("pkg/__init__.py", m)

    # ---- surface: tool + command, zero hooks ----------------------------- #

    def test_register_exposes_tool_and_command_no_hooks(self):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(plugin_dir, "__init__.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("register_hook", src)  # zero-hooks rule

        pkg = type(sys)("codebase_index")
        pkg.__path__ = [plugin_dir]
        sys.modules["codebase_index"] = pkg
        spec = importlib.util.spec_from_file_location(
            "codebase_index", os.path.join(plugin_dir, "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        mod.__path__ = [plugin_dir]
        sys.modules["codebase_index"] = mod
        spec.loader.exec_module(mod)

        class FakeCtx:
            def __init__(self):
                self.tools, self.commands = {}, {}
            def register_tool(self, name, toolset=None, schema=None, handler=None,
                              description=None, emoji=None):
                self.tools[name] = (toolset, schema, handler)
            def register_command(self, name, handler=None, description=None,
                                 args_hint=None):
                self.commands[name] = (handler, description, args_hint)

        ctx = FakeCtx()
        mod.register(ctx)
        self.assertIn("codebase_query", ctx.tools)
        self.assertIn("cindex", ctx.commands)
        toolset, schema, handler = ctx.tools["codebase_query"]
        self.assertEqual(toolset, "file")
        self.assertIn("query", schema["properties"])

        # exercise the command handler end-to-end on a temp repo (hermetic cache)
        root = _tree({"x.py": "def ping():\n    pass\n"})
        cache_tmp = tempfile.mkdtemp()
        old_env = os.environ.get("XOMNI_CACHE")
        os.environ["XOMNI_CACHE"] = cache_tmp
        try:
            core.update_index(root)  # default db path under the temp cache
            out = handler({"path": root, "query": "ping", "limit": 5})
            self.assertIn("x.py", out)
            self.assertIn("ping", out)
            cmd = ctx.commands["cindex"][0]
            self.assertIn("file_count: 1", cmd(f"status {root}"))
            self.assertIn("x.py", cmd(f"query ping {root}"))
        finally:
            if old_env is None:
                os.environ.pop("XOMNI_CACHE", None)
            else:
                os.environ["XOMNI_CACHE"] = old_env
            sys.modules.pop("codebase_index", None)


class HybridEmbeddingsTests(unittest.TestCase):
    """Opt-in embeddings/RRF layer: fusion math, vectors storage, graceful skip.

    No network: every provider call is mocked at the core._post_json /
    core.embed_texts boundary.
    """

    def _repo(self, files: dict[str, str]) -> tuple[str, str]:
        root = _tree(files)
        db = os.path.join(tempfile.mkdtemp(), "index.db")
        core.update_index(root, db_path=db)
        return root, db

    # ---- fusion math ---------------------------------------------------- #

    def test_rrf_fusion_math(self):
        fused = dict(core.rrf_fuse([["a", "b", "c"], ["b", "c", "a"]]))
        # a: 1/61 + 1/63 | b: 1/62 + 1/61 | c: 1/63 + 1/62  =>  b > a > c
        self.assertEqual([d for d, _ in core.rrf_fuse(
            [["a", "b", "c"], ["b", "c", "a"]])], ["b", "a", "c"])
        self.assertAlmostEqual(fused["b"], 1 / 61 + 1 / 62)
        self.assertAlmostEqual(fused["a"], 1 / 61 + 1 / 63)
        self.assertAlmostEqual(fused["c"], 1 / 63 + 1 / 62)
        # doc ranked 1st in both lists with k=1 scores exactly 1.0
        self.assertEqual(core.rrf_fuse([["x"], ["x"]], k=1.0), [("x", 1.0)])
        # a doc present in both rankings beats one present in only one
        self.assertGreater(fused["b"], fused["c"])

    def test_cosine_similarity(self):
        self.assertAlmostEqual(core._cosine([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(core._cosine([1.0, 0.0], [0.0, 1.0]), 0.0)
        self.assertAlmostEqual(core._cosine([1.0, 0.0], [-1.0, 0.0]), -1.0)
        self.assertEqual(core._cosine([1.0, 2.0], [1.0]), 0.0)  # dim mismatch

    # ---- graceful skip (provider mocked: no network) -------------------- #

    def test_embed_texts_returns_none_when_provider_down(self):
        with mock.patch("core._post_json", return_value=None):
            self.assertIsNone(core.embed_texts(["hello"]))
        with mock.patch("core._post_json",
                        return_value={"embedding": [0.1, 0.2]}):
            self.assertEqual(core.embed_texts(["hi"]), [[0.1, 0.2]])
        with mock.patch("core._post_json", return_value={"nope": 1}):
            self.assertIsNone(core.embed_texts(["hi"]))

    def test_build_embeddings_graceful_skip_when_provider_down(self):
        root, db = self._repo({"a.py": "def f():\n    pass\n"})
        with mock.patch("core.embed_texts", return_value=None):
            r = core.build_embeddings(root, db_path=db, model="mock-embed")
        self.assertFalse(r["ok"])
        self.assertIn("graceful", r["reason"])
        st = core.index_status(root, db_path=db)
        self.assertEqual(st["embedding_model"], "none")
        self.assertEqual(st["vector_count"], 0)

    # ---- vectors storage + hybrid query --------------------------------- #

    def test_build_embeddings_stores_vectors_and_model_tag(self):
        root, db = self._repo({"a.py": "def alpha():\n    pass\n",
                               "b.py": "def beta():\n    pass\n"})

        def fake_embed(texts, **kw):
            return [[float(len(t)), 1.0] for t in texts]

        with mock.patch("core.embed_texts", side_effect=fake_embed):
            r = core.build_embeddings(root, db_path=db, model="test-embed")
        self.assertTrue(r["ok"])
        self.assertEqual(r["embedded"], 2)
        st = core.index_status(root, db_path=db)
        self.assertEqual(st["embedding_model"], "test-embed")
        self.assertEqual(st["vector_count"], 2)
        conn = core._connect(db)
        try:
            rows = [dict(r) for r in conn.execute(
                "SELECT file_id, model, dim, embedding FROM vectors "
                "ORDER BY file_id")]
        finally:
            conn.close()
        self.assertEqual([r["file_id"] for r in rows], [1, 2])
        self.assertTrue(all(r["model"] == "test-embed" for r in rows))
        self.assertTrue(all(r["dim"] == 2 for r in rows))
        self.assertEqual(core._unpack_vec(rows[0]["embedding"])[1], 1.0)

    def test_query_hybrid_uses_vectors_and_gracefully_falls_back(self):
        root, db = self._repo({
            "dense.py": "def alpha():\n    # alpha alpha alpha\n    pass\n",
            "sparse.py": "def beta():\n    # alpha once\n    pass\n",
        })
        # vector = [1,0,0] iff the file defines "alpha" (dense.py only);
        # the query "alpha" embeds to [0,1,0] -> sparse.py is the vector hit.
        def fake_embed(texts, **kw):
            return [[1.0, 0.0, 0.0] if "def alpha" in t else [0.0, 1.0, 0.0]
                    for t in texts]

        with mock.patch("core.embed_texts", side_effect=fake_embed):
            core.build_embeddings(root, db_path=db, model="mock-vec")
            out = core.query_hybrid(root, "alpha", db_path=db)
        self.assertIn("hybrid rrf", out)
        self.assertIn("mock-vec", out)
        self.assertIn("dense.py", out)
        self.assertIn("sparse.py", out)

        # provider down at query time -> graceful bm25 fallback, no raise
        with mock.patch("core.embed_texts", return_value=None):
            out2 = core.query_hybrid(root, "alpha", db_path=db)
        self.assertIn("graceful fallback", out2)
        self.assertIn("dense.py", out2)

    def test_query_hybrid_without_embeddings_is_pure_bm25(self):
        root, db = self._repo({
            "dense.py": "def alpha():\n    # alpha alpha alpha\n    pass\n",
            "sparse.py": "def beta():\n    # alpha once\n    pass\n",
        })
        out = core.query_hybrid(root, "alpha", db_path=db)
        self.assertIn("no vectors", out)
        self.assertIn("dense.py", out)
        self.assertLess(out.index("dense.py"), out.index("sparse.py"))


if __name__ == "__main__":
    unittest.main()
