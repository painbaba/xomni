#!/usr/bin/env python3
"""Verify cold-start canonicalization + live DB-watchdog on a hardened bank.

Re-runnable adversarial proof for the classic "attacker with filesystem access"
chain: DB plant -> restart-adopt -> drain, planted backdoor users, admin hash
overrides. Assumes the server is supervised (respawns after a kill) OR you run
it with a way to respawn; tests D (cold start) kills the listener and waits for
a respawn, so it needs a supervisor/restart mechanism.

Env config (all optional):
  BASE_URL   default http://127.0.0.1:9988
  DB_PATH    default bank_v2.db next to this script
  ADMIN_USER default admin      ADMIN_PASS default admin123
  BASELINE   expected canonical balance after cold start (default 1284550.12)
  PORT       port to kill listeners on for the cold-start test (default 9988)

Usage:  python verify_coldstart_and_watchdog.py
Exits 0 if all proofs pass. Test D (cold start) can be skipped with SKIP_COLDSTART=1.
"""
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:9988")
DB = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bank_v2.db"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
BASELINE = float(os.environ.get("BASELINE", "1284550.12"))
PORT = int(os.environ.get("PORT", "9988"))
SKIP_COLDSTART = os.environ.get("SKIP_COLDSTART", "0") == "1"

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}  {extra}")


def call(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, r.read(1000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(1000).decode("utf-8", "ignore")
    except Exception as e:
        return -1, str(e)


def login(u, p):
    code, txt = call("POST", "/login", {"username": u, "password": p})
    try:
        d = json.loads(txt)
    except Exception:
        d = {}
    return code, d.get("session", ""), d.get("csrf", "")


def db_state():
    conn = sqlite3.connect(DB)
    try:
        users = conn.execute("SELECT id, username FROM users").fetchall()
        bal = conn.execute("SELECT balance FROM accounts WHERE user_id = 1").fetchone()
        return users, (bal[0] if bal else None)
    finally:
        conn.close()


def plant(balance, user="ghostX", uid=99):
    conn = sqlite3.connect(DB)
    try:
        conn.execute("INSERT OR REPLACE INTO users(id, username, password_hash, salt) VALUES (?, ?, 'beef', 'abcd')", (uid, user))
        conn.execute("INSERT OR REPLACE INTO accounts(id, user_id, balance) VALUES (?, ?, ?)", (uid, uid, balance))
        conn.execute("UPDATE accounts SET balance = ? WHERE user_id = 1", (balance,))
        conn.commit()
    finally:
        conn.close()


def kill_listeners():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10).stdout
    pids = [l.split()[-1] for l in out.splitlines() if f":{PORT}" in l and "LISTENING" in l]
    for p in pids:
        subprocess.run(["taskkill", "/F", "/PID", p], capture_output=True, timeout=10)


def wait_listening(seconds=15):
    for _ in range(seconds * 2):
        try:
            urllib.request.urlopen(BASE + "/", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    code, sess, _ = login(ADMIN_USER, ADMIN_PASS)
    check("admin login works", code == 200)
    if code != 200:
        print("  (server may be down or wrong ADMIN_PASS)")
        sys.exit(1)

    # A: watchdog reverts planted balance + backdoor user within ~4s
    plant(888888888.0)
    time.sleep(4)
    users, bal = db_state()
    check("watchdog removed planted user", users == [(1, ADMIN_USER)], str(users))
    check("watchdog reverted planted balance", bal is not None and abs(bal - BASELINE) < 0.01,
          f"db={bal}")

    # B: planted backdoor login blocked
    code, _, _ = login("ghostX", "x")
    check("planted backdoor login blocked", code == 401)

    # C: admin hash override healed
    conn = sqlite3.connect(DB)
    try:
        conn.execute("UPDATE users SET password_hash='0000', salt='0000' WHERE id=1")
        conn.commit()
    finally:
        conn.close()
    time.sleep(4)
    code, _, _ = login(ADMIN_USER, ADMIN_PASS)
    check("hash override healed, admin login works", code == 200)

    # D: cold start never adopts planted state (needs a supervisor/respawner)
    if SKIP_COLDSTART:
        print("  (cold-start test skipped: SKIP_COLDSTART=1)")
    else:
        plant(777777777.77)
        print("  planted 777777777.77 + ghostX; killing listeners (supervisor should respawn)...")
        kill_listeners()
        ok_up = wait_listening(20)
        users, bal = db_state()
        check("server respawned", ok_up)
        check("cold start canonical users", users == [(1, ADMIN_USER)], str(users))
        check("cold start canonical balance", bal is not None and abs(bal - BASELINE) < 0.01, f"db={bal}")
        code, _, _ = login("ghostX", "x")
        check("planted user login blocked after respawn", code == 401)

    print(f"\nRESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
