"""Redacted probe: read secret-bearing files, print ONLY REDACTED-xxxx-xxxx.

Safe to run into a transcript — nothing it prints is a full secret value.

Usage:
    python read_redacted.py [HOME_DIR]

Reads (all optional; absent files are reported as such):
  .env          -> KEY=REDACTED-<first4>-<last4> per non-comment line
  auth.json     -> nested walk of dicts/lists, every leaf redacted
  config.yaml   -> full dump, but values of secret-like keys redacted
  state.db      -> table names + row counts ONLY (never content), read-only

Windows note: invoke with a Windows-style script path, e.g.
    python "C:/Users/.../read_redacted.py" "C:/Users/HP/AppData/Local/hermes"
MSYS /c/... paths get mangled to C:\\c\\... when passed to Windows python.
"""
import json
import os
import re
import sqlite3
import sys

SECRET_KEY = re.compile(r"(key|token|secret|password|auth|api[_-]?key|sk-|Bearer)", re.I)


def redact(v):
    v = str(v).strip()
    if len(v) <= 8:
        return "REDACTED-****-****"
    return f"REDACTED-{v[:4]}-{v[-4:]}"


def probe_env(path):
    print(f"=== {os.path.basename(path)} ===")
    if not os.path.exists(path):
        print("(absent)")
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            print(f"ENV {k.strip()}={redact(v)}")


def probe_auth(path):
    print(f"=== {os.path.basename(path)} (redacted) ===")
    if not os.path.exists(path):
        print("(absent)")
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{prefix}[{i}]")
        else:
            print(f"AUTH {prefix}={redact(o)}")

    walk(data)


def probe_config(path):
    print(f"=== {os.path.basename(path)} (secret-like values redacted) ===")
    if not os.path.exists(path):
        print("(absent)")
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if ":" in s:
                k, _, v = s.partition(":")
                if SECRET_KEY.search(k) and v.strip():
                    print(f"CFG {k.strip()}: {redact(v)}")
                    continue
            print(line.rstrip())


def probe_db(path):
    print(f"=== {os.path.basename(path)} (schema + counts only) ===")
    if not os.path.exists(path):
        print("(absent)")
        return
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"tables ({len(tables)}): {tables}")
    for t in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            print(f"  {t}: {cur.fetchone()[0]} rows")
        except Exception as e:
            print(f"  {t}: (count failed: {e})")
    con.close()


if __name__ == "__main__":
    home = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.hermes")
    probe_env(os.path.join(home, ".env"))
    probe_auth(os.path.join(home, "auth.json"))
    probe_config(os.path.join(home, "config.yaml"))
    probe_db(os.path.join(home, "state.db"))
