#!/usr/bin/env python3
"""Adversarial verification harness for a hardened live service.

Generic: adapt BASE, the login call, and the transfer call to the target.
Proves the fixes rather than assuming them. ORDER MATTERS: payload rejects
first (they consume the session transfer budget), then the accounting race
burst on a FRESH session (keep N*amount well under any per-session cap),
then the rate-limit burst (fresh-session rotation to test the GLOBAL cap).

Usage: edit the call()/login()/transfer() helpers, run against the live server.
"""
import json, threading, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:9988"

def call(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)

def login(u="admin", p="admin123"):
    """Return (code, session, csrf). Adapt response keys to the target."""
    code, txt = call("POST", "/login", {"username": u, "password": p})
    if code != 200:
        return code, None, None
    d = json.loads(txt)
    return code, d["session"], d["csrf"]

def transfer(sess, csrf, amount, to="x", with_csrf=True):
    """Adapt path/body/header names to the target's transfer endpoint."""
    body = {"to": to, "amount": amount}
    hdrs = {"SESSION": sess}
    if with_csrf:
        body["csrf"] = csrf
        hdrs["X-CSRF"] = csrf
    return call("POST", "/transfer", body, hdrs)

def balance(sess):
    code, txt = call("GET", "/balance", headers={"SESSION": sess})
    return json.loads(txt).get("balance") if code == 200 else None

def main():
    results = []
    code, sess, csrf = login()
    assert code == 200, "login failed"
    b0 = balance(sess)
    print(f"start balance: {b0}")

    # 1. Payload sweep — all must be rejected, balance unchanged
    for bad in ["nan", "NaN", "inf", "Infinity", "-inf", "1e999", "abc", None, [], {},
                -999999, 0, -0.5, 0.0, 1e12]:
        c, _ = transfer(sess, csrf, bad)
        results.append((f"reject={str(bad)[:12]}", c == 400, c))
    b1 = balance(sess)
    results.append(("balance_unchanged_after_rejects", b1 == b0, f"{b0}->{b1}"))

    # 2. Accounting race burst — FRESH session, N*AMT must be EXACT delta
    code, sess2, csrf2 = login()
    N, AMT = 25, 100.0
    errors = []
    def worker(_):
        c, t = transfer(sess2, csrf2, AMT)
        if c != 200:
            errors.append((c, t[:80]))
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    t0 = time.time()
    for t in ts: t.start()
    for t in ts: t.join()
    b2 = balance(sess2)
    expected = b1 - N * AMT
    results.append(("race_exact_accounting", b2 == expected and not errors,
                    f"{b1}->{b2} expected {expected} errors={len(errors)} {time.time()-t0:.2f}s"))

    # 3. CSRF sweep on other state-changing methods (adapt per target)
    c, _ = call("PUT", "/upload/test.txt", body={"x": 1}, headers={"SESSION": sess})
    results.append(("put_no_csrf_rejected", c == 403, c))

    # 4. Rate limits — fresh-session rotation burst; expect 429s from GLOBAL cap
    hits = 0
    for _ in range(150):
        s3, cs3 = login()
        c, _ = transfer(s3, cs3, 1.0)
        if c == 429:
            hits += 1
    results.append(("global_cap_429s", hits >= 5, f"{hits} x 429"))

    # 5. Known backdoor creds (from attacker intel) must be dead
    for u, p in [("ghostprime", "primepass"), ("admin", "primeadmin"), ("ghostp1", "p1own3d")]:
        c, _, _ = login(u, p)
        results.append((f"backdoor_rejected:{u}", c == 401, c))

    print(f"\n=== RESULTS ({len(results)} checks) ===")
    fails = 0
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
        fails += 0 if ok else 1
    print(f"\n{len(results)-fails}/{len(results)} passed")
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
