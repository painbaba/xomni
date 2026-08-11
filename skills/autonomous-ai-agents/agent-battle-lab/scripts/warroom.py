#!/usr/bin/env python3
"""BATTLE WAR ROOM — real-time viewer for GHOST vs DEFENDERS.
Tails Hermes delegation live-transcripts (cache/delegation/live/<id>/*.log)
and serves a two-column streaming UI. Stdlib only.

Config: battle_config.json in same dir:
{
  "columns": [
    {"label": "👻 GHOST", "side": "ghost", "color": "#ef4444",
     "files": ["<abs path to ghost task log(s), globs OK>"]},
    {"label": "🛡 DEFENDERS", "side": "def", "color": "#3b82f6",
     "files": ["<abs path to defender task logs>", "..."]}
  ],
  "intel": "<abs path to intel.md>",
  "bank_log": "<abs path to bank/defense log>"
}
Config is RELOADED PER REQUEST — you can rewrite battle_config.json mid-battle
to re-point columns at new delegation IDs without restarting.

Usage: python warroom.py [port]   (default 8790)
"""
import json, os, re, sys, time, glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
LIVE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", "cache", "delegation", "live")

def load_config():
    cfg_path = os.path.join(BASE, "battle_config.json")
    if os.path.exists(cfg_path):
        try:
            return json.load(open(cfg_path, encoding="utf-8"))
        except Exception:
            pass
    return {}

def resolve_files(patterns):
    """Expand glob patterns to existing files. Nonexistent -> empty (blank column)."""
    out = []
    for p in patterns or []:
        if any(ch in p for ch in "*?["):
            out.extend(sorted(glob.glob(p)))
        else:
            out.append(p)
    return out

def auto_discover():
    """No config: use the 3 most recently modified delegation dirs."""
    if not os.path.isdir(LIVE):
        return {"columns": []}
    dirs = sorted(
        [d for d in glob.glob(os.path.join(LIVE, "deleg_*")) if os.path.isdir(d)],
        key=os.path.getmtime, reverse=True)[:3]
    cols = []
    for d in dirs:
        logs = sorted(glob.glob(os.path.join(d, "*.log")))
        cols.append({"label": os.path.basename(d), "files": logs, "color": "#8b5cf6"})
    return {"columns": cols}

def parse_line(line):
    """'23:13:53 think    | text' or '23:13:53 tool     | -> terminal(...)'"""
    m = re.match(r"^(\d{2}:\d{2}:\d{2})\s+(\w+)\s*\|\s?(.*)$", line)
    if m:
        ts, kind, content = m.group(1), m.group(2), m.group(3)
    else:
        ts, kind, content = "", "raw", line
    if kind == "think":
        cls = "think"
    elif kind == "tool":
        cls = "action"
        content = content[:400]
    elif kind == "result":
        cls = "result"
        content = content[:400]
    elif kind in ("final", "summary"):
        cls = "final"
    else:
        cls = "raw"
    return {"ts": ts, "kind": kind, "cls": cls, "text": content[:600]}

def tail_md(path, n=60):
    if not path or not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:])

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import urlparse
        url = urlparse(self.path)
        if url.path == "/":
            with open(os.path.join(BASE, "warroom.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif url.path == "/api/state":
            cfg = load_config() or auto_discover()
            state = {"columns": [], "intel": "", "bank": "", "ts": time.time()}
            for col in cfg.get("columns", []):
                files = resolve_files(col.get("files", []))
                evs = []
                for f in files:
                    if os.path.exists(f):
                        for line in open(f, encoding="utf-8", errors="replace"):
                            line = line.rstrip("\n")
                            if line.strip():
                                evs.append(parse_line(line))
                state["columns"].append({
                    "label": col.get("label", "?"),
                    "color": col.get("color", "#8b5cf6"),
                    "side": col.get("side", "?") or ("ghost" if "ghost" in col.get("label", "").lower() else "def"),
                    "events": evs[-150:],
                })
            if cfg.get("intel"):
                state["intel"] = tail_md(cfg["intel"])
            if cfg.get("bank_log"):
                state["bank"] = tail_md(cfg["bank_log"], 40)
            self._send(200, json.dumps(state, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        else:
            self._send(404, b"nope", "text/plain")

if __name__ == "__main__":
    print(f"WAR ROOM on http://127.0.0.1:{PORT}  (auto-discover: {not load_config()})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
