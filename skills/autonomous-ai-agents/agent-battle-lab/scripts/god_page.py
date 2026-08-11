#!/usr/bin/env python3
"""GOD PAGE — live territory dashboard server for agent-battle-lab civilizations.
Serves /api/state (JSON), / (2D panel), /3d (Three.js view). Port 8792.
Adapt ROOT/CACHE paths to your lab. Run: python god_page.py  (background).

State per tick: bank status (urllib GET target port), civilization dirs + file
counts, machine_city district populations/opinions, census/registry/ledger
tails, last N live delegation log tails, open ports (netstat).
"""
import json, os, glob, time, subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = r"C:\Users\HP\ai-workforce\ghost-lab"          # territory root
CITY = os.path.join(ROOT, "machine_city")              # districts live here
CACHE = r"C:\Users\HP\AppData\Local\hermes\cache\delegation\live"
BANK_URL = "http://127.0.0.1:9988/"                    # bank to watch
PORT = 8792
HERE = os.path.dirname(os.path.abspath(__file__))

def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=6).stdout.strip()
    except Exception:
        return ""

def bank_status():
    try:
        import urllib.request
        with urllib.request.urlopen(BANK_URL, timeout=3) as r:
            return f"UP ({r.status})"
    except Exception as e:
        return f"DOWN ({type(e).__name__})"

def read_tail(path, n=4000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()[-n:]
    except Exception:
        return ""

def collect_state():
    state = {"ts": time.strftime("%H:%M:%S"), "bank": bank_status()}
    # civilizations: any dir with a founding doc
    civs = []
    for name, d in [("GHOST CIVILIZATION", os.path.join(ROOT, "ghost_sandbox")),
                    ("GOD'S PEOPLE", os.path.join(ROOT, "god_people"))]:
        founding = None
        if os.path.isdir(d):
            for f in os.listdir(d):
                if "founding" in f.lower() or "constitution" in f.lower():
                    founding = read_tail(os.path.join(d, f), 800); break
        civs.append({"name": name, "dir": d,
                     "files": len(os.listdir(d)) if os.path.isdir(d) else 0,
                     "founding": (founding or "(no founding doc yet)")[:800]})
    state["civilizations"] = civs
    # districts: subdirs of CITY, pop = files in population/, opinions in opinions/
    districts = []
    if os.path.isdir(CITY):
        for d in sorted(os.listdir(CITY)):
            dp = os.path.join(CITY, d)
            if os.path.isdir(dp):
                pop = len(os.listdir(os.path.join(dp, "population"))) if os.path.isdir(os.path.join(dp, "population")) else 0
                op = len(os.listdir(os.path.join(dp, "opinions"))) if os.path.isdir(os.path.join(dp, "opinions")) else 0
                districts.append({"name": d, "pop": pop, "opinions": op, "files": len(os.listdir(dp))})
    state["districts"] = districts
    for k in ("census", "registry", "ledger"):
        p = os.path.join(CITY, {"census": "census.md", "registry": "registry.md", "ledger": "city_ledger.md"}[k])
        state[k] = read_tail(p, 1500) if os.path.exists(p) else "(pending)"
    # live delegation streams (newest 6)
    streams = []
    for d in sorted(glob.glob(os.path.join(CACHE, "deleg_*")), key=os.path.getmtime, reverse=True)[:6]:
        for tf in sorted(glob.glob(os.path.join(d, "task-*.log"))):
            t = read_tail(tf, 500)
            if t:
                streams.append({"deleg": os.path.basename(d), "task": os.path.basename(tf), "tail": t})
    state["streams"] = streams
    state["ports"] = sh("netstat -ano | grep LISTENING | grep -E ':(9988|8787|8790|8791|8792|8080|80) ' | awk '{print $2}' | sort -u")
    return state

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/state":
            body = json.dumps(collect_state()).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body); return
        page = {"": "god_page.html", "/": "god_page.html", "/3d": "god_view3d.html", "/god3d": "god_view3d.html"}.get(self.path)
        if page:
            with open(os.path.join(HERE, page), "rb") as f:
                body = f.read()
            self.send_response(200); self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body); return
        self.send_response(404); self.end_headers()
    def log_message(self, *a): pass

if __name__ == "__main__":
    print(f"GOD PAGE listening on 127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
