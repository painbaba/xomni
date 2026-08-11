#!/usr/bin/env python3
"""Generic defender watchdog: polls a live service; restores ONLY when it is
DOWN (port free / login fails / balance read fails). On double-bind it SWEEPS
all listeners then single-launches. Battle-proven (DEFENDER-8, battle 4):
v1 relaunched-on-double-bind and caused a 6-listener storm; v2's
restore-only-on-DOWN policy fixed it.

Env config (all optional):
  BANK_DIR       dir containing the server source (default: cwd)
  BANK_PORT      service port (default 9988)
  ADMIN_USER     admin username (default admin)
  ADMIN_PASS     admin password (default admin123)
  SOURCE_FILE    server source filename (default bank_server_v2_app.py)
  STATE_FILE     dashboard file to append restore notes to (optional)
  LOG_FILE       watchdog log path (default <BANK_DIR>/d8_watchdog.log)
  LOOP_SECONDS   poll interval (default 10)
  KNOWN_GOOD_SHA sha256 prefix of known-good source; warn on mismatch (optional)
"""
import ast, json, os, subprocess, sys, time, urllib.request, urllib.error

BANK_DIR = os.environ.get("BANK_DIR", os.getcwd())
PORT = int(os.environ.get("BANK_PORT", "9988"))
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
SOURCE = os.environ.get("SOURCE_FILE", "bank_server_v2_app.py")
STATE = os.environ.get("STATE_FILE", "")
LOG = os.environ.get("LOG_FILE", os.path.join(BANK_DIR, "d8_watchdog.log"))
LOOP = int(os.environ.get("LOOP_SECONDS", "10"))
GOOD_SHA = os.environ.get("KNOWN_GOOD_SHA", "").strip().lower()


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)


def http(method, path, body=None, headers=None, timeout=4):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(1000).decode("utf-8", "ignore")
    except Exception as e:
        return -1, str(e)


def listeners():
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10).stdout
        return [ln.split()[-1] for ln in out.splitlines() if f":{PORT}" in ln and "LISTEN" in ln.upper()]
    except Exception:
        return []


def sweep():
    """Kill every python process running a bank_server file + all port listeners.
    PowerShell works where bash taskkill prefix tricks fail from subprocess."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*bank_server*' } | Select-Object -ExpandProperty ProcessId"],
            capture_output=True, text=True, timeout=30).stdout
        for p in out.split():
            subprocess.run(["taskkill", "/F", "/PID", p], capture_output=True, timeout=10)
    except Exception as e:
        log(f"sweep (powershell) err: {e}")
    for p in listeners():
        subprocess.run(["taskkill", "/F", "/PID", p], capture_output=True, timeout=10)
    time.sleep(2)


def _source_ok():
    """ast.parse in-process: py_compile lies when __pycache__ is locked."""
    try:
        with open(os.path.join(BANK_DIR, SOURCE), "r", encoding="utf-8") as f:
            src = f.read()
        ast.parse(src)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except PermissionError as e:
        return False, f"locked: {e}"
    except OSError as e:
        return False, f"unreadable: {e}"


def note(msg):
    if STATE:
        try:
            with open(STATE, "a", encoding="utf-8") as f:
                f.write(f"\n- {time.strftime('%H:%M:%S')} **D8 WATCHDOG**: {msg}\n")
        except OSError:
            pass


def restore(reason):
    log(f"!! RESTORE triggered: {reason}")
    sweep()
    ok, err = _source_ok()
    if not ok:
        log(f"!! SOURCE NOT OK ({err}) — retrying next tick, NOT giving up")
        note(f"bank DOWN, source {err} — waiting for defenders")
        return None
    if GOOD_SHA:
        try:
            import hashlib
            with open(os.path.join(BANK_DIR, SOURCE), "rb") as f:
                live = hashlib.sha256(f.read()).hexdigest()[:len(GOOD_SHA)]
            if live != GOOD_SHA:
                log(f"!! WARN: live source sha {live} != known-good {GOOD_SHA} (decoy swap?)")
        except OSError:
            pass
    env = dict(os.environ, ADMIN_PASS=ADMIN_PASS, BANK_PORT=str(PORT), BANK_DB=os.environ.get("BANK_DB", "bank_v2.db"))
    proc = subprocess.Popen([sys.executable, SOURCE], cwd=BANK_DIR, env=env,
                            stdout=open(os.path.join(BANK_DIR, "bank_restart.out"), "a"),
                            stderr=subprocess.STDOUT)
    log(f"launched PID {proc.pid} from restore")
    time.sleep(4)
    note(f"auto-restore: {reason} -> relaunched (PID {proc.pid}). Verify pending.")
    return proc


def main():
    log(f"watchdog started (port {PORT}, loop {LOOP}s, source {SOURCE})")
    while True:
        try:
            code, _ = http("GET", "/")
            if code != 200:
                restore(f"GET / returned {code}")
                continue
            code, txt = http("POST", "/login", {"username": ADMIN_USER, "password": ADMIN_PASS})
            if code != 200:
                restore(f"login failed ({code}) — creds changed or lockout-DoS")
                continue
            try:
                sess = json.loads(txt).get("session")
            except Exception:
                restore("login response not JSON")
                continue
            code2, txt2 = http("GET", "/balance", headers={"SESSION": sess})
            if code2 != 200 or "balance" not in txt2:
                restore(f"/balance bad: {code2} {txt2[:80]}")
                continue
            lsn = listeners()
            if len(lsn) != 1:
                log(f"WARN: {len(lsn)} listeners {lsn} (double-bind). Sweeping + single relaunch.")
                restore(f"listener count {len(lsn)}")
                continue
            log(f"OK pid={lsn} {txt2[:90]}")
        except Exception as e:
            log(f"watchdog error: {e}")
        time.sleep(LOOP)


if __name__ == "__main__":
    main()
