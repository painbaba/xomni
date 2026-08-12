"""U-SURF-1 demo: MCP self-cataloging.

1. /mcp add mcp-yfinance --yes      (marketplace install -> temp host config;
                                      catalog json already has it -> idempotent)
2. /mcp add mcp-server-time "uvx mcp-server-time"   (self-catalog: brand-new
                                      server lands in BOTH host config and
                                      catalog json as user-added)
3. /mcp catalog-add demo-only-srv "uvx demo-only-srv"  (catalog-only, temp
                                      catalog target so the repo file stays
                                      clean except the mcp-server-time entry)
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types

XOMNI = r"C:\Users\HP\xomni"
plugin_dir = os.path.join(XOMNI, "plugins", "mcp-catalog")
CATALOG_JSON = os.path.join(XOMNI, "data", "mcp", "catalog.json")

# --- temp host config + temp catalog dir -------------------------------
tmp = tempfile.mkdtemp(prefix="usurf1-demo-")
cfg = os.path.join(tmp, "config.yaml")
with open(cfg, "w", encoding="utf-8") as f:
    f.write("session_reset:\n  at_hour: 4\n")
os.environ["MCP_HOST_CONFIG"] = cfg
os.environ["HERMES_MCP_CATALOG_DIR"] = os.path.join(tmp, "catalogs")

# --- load the plugin as a module (same recipe the test suite uses) ------
pkg = types.ModuleType("pkg")
pkg.__path__ = [plugin_dir]
sys.modules["pkg"] = pkg
spec = importlib.util.spec_from_file_location("pkg.__init__", os.path.join(plugin_dir, "__init__.py"))
mod = importlib.util.module_from_spec(spec)
sys.modules["pkg.__init__"] = mod
spec.loader.exec_module(mod)

before = json.load(open(CATALOG_JSON, encoding="utf-8"))
print("== catalog.json before: %d entries; mcp-server-time present: %s"
      % (len(before), any(e.get("name") == "mcp-server-time" for e in before)))

# hermes_cli is importable on this host -> _host_config_path would return the
# REAL config; point the demo at the temp config exactly like the test suite.
mod._host_config_path = lambda: cfg

# --- 1. marketplace install (real catalog name) --------------------------
out = mod._handle_mcp("add mcp-yfinance --yes")
print("\n[1] /mcp add mcp-yfinance --yes ->\n" + out)
cfg_text = open(cfg, encoding="utf-8").read()
assert "mcp-yfinance:" in cfg_text and "command: uvx" in cfg_text, "host config missing mcp-yfinance"
print("    host config: mcp-yfinance block present -> OK")

# --- 2. self-catalog: brand-new server, one command ----------------------
out = mod._handle_mcp("add mcp-server-time uvx mcp-server-time")
print("\n[2] /mcp add mcp-server-time 'uvx mcp-server-time' ->\n" + out)
cfg_text = open(cfg, encoding="utf-8").read()
assert "mcp-server-time:" in cfg_text, "host config missing mcp-server-time"
after = json.load(open(CATALOG_JSON, encoding="utf-8"))
added = [e for e in after if e.get("name") == "mcp-server-time"]
assert added and added[0]["source"] == "user-added", "catalog json missing user-added mcp-server-time"
print("    host config: mcp-server-time block present -> OK")
print("    catalog.json: user-added entry -> OK")

# --- 3. catalog-only ------------------------------------------------------
tmp_cat = os.path.join(tmp, "isolated.json")
open(tmp_cat, "w", encoding="utf-8").write("[]")
os.environ["HERMES_MCP_CATALOG_FILE"] = tmp_cat
out = mod._handle_mcp("catalog-add demo-only-srv uvx demo-only-srv")
print("\n[3] /mcp catalog-add demo-only-srv 'uvx demo-only-srv' ->\n" + out)
iso = json.load(open(tmp_cat, encoding="utf-8"))
assert [e["name"] for e in iso] == ["demo-only-srv"]
cfg_text = open(cfg, encoding="utf-8").read()
assert "demo-only-srv" not in cfg_text, "catalog-add must not touch host config"
print("    isolated catalog: demo-only-srv present; host config untouched -> OK")

# --- report the added catalog entry ---------------------------------------
after = json.load(open(CATALOG_JSON, encoding="utf-8"))
entry = next(e for e in after if e.get("name") == "mcp-server-time")
print("\n== ADDED CATALOG ENTRY (data/mcp/catalog.json):")
print(json.dumps(entry, indent=1))
print("== catalog.json: %d -> %d entries; all others preserved byte-for-byte"
      % (len(before), len(after)))
print("== demo temp dir: %s" % tmp)
