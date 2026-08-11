#!/usr/bin/env python3
"""
EXPLORER-FREEWILL Kali recon probe (generalized for sandbox-city-expedition).

Authorized access: user-owned VM. Password loaded in-process from the Hermes
.env (SUDO_PASSWORD key), NEVER printed. READ-ONLY commands only.

Usage: copy this file into the expedition's explorer/ dir as cycleN_kali_recon.py,
adjust HOSTS / USER / CMDS for the environment, then run with a Windows-style
path:  python "C:/Users/.../cycleN_kali_recon.py"
"""
import sys
import socket
import re

try:
    import paramiko
except ImportError:
    print("NO_PARAMIKO (pip install paramiko)")
    sys.exit(2)

# Authorized access: user-owned VM. Password loaded in-process, NEVER printed.
ENV_PATH = r"C:\Users\HP\AppData\Local\hermes\.env"


def load_password():
    with open(ENV_PATH, "r", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    m = re.search(r"^\s*SUDO_PASSWORD\s*=\s*(.+?)\s*$", txt, re.M)
    if not m:
        print("FATAL: SUDO_PASSWORD not found in Hermes .env")
        sys.exit(2)
    return m.group(1)


# (host, label) — first reachable+authable host wins
HOSTS = [
    ("192.168.29.35", "bridged"),
    ("192.168.56.101", "host-only"),
]
USER = "painbaba"
PORT = 22
# Baseline last-write for "0 new artifacts" proof (update per cycle)
BASELINE_LAST_WRITE = "2026-08-09 06:41"

CMDS = [
    ("whoami+uptime", "whoami; uptime; uname -a | cut -c1-60"),
    ("fuzz-procs", "ps aux | grep -iE 'libfuzzer|fuzz|hevc|avc|afl|qemu' | grep -v grep | wc -l"),
    ("fuzz-proc-detail", "ps aux | grep -iE 'libfuzzer|fuzz|hevc|avc|afl|qemu' | grep -v grep | head -5"),
    ("artifact-count", "find ~/fuzz -maxdepth 2 -name '*crash*' 2>/dev/null | wc -l; find ~/fuzz -maxdepth 2 -name '*slow*' 2>/dev/null | wc -l; find ~/fuzz -maxdepth 2 -name '*timeout*' 2>/dev/null | wc -l"),
    ("last-log-writes", "ls -lt ~/fuzz/*.log 2>/dev/null | head -6"),
    ("newest-artifacts", f"find ~/fuzz -maxdepth 2 -newermt '{BASELINE_LAST_WRITE}' \\( -name '*crash*' -o -name '*slow*' -o -name '*timeout*' \\) 2>/dev/null | head -10"),
    ("corpus", "ls -d ~/fuzz/*corpus* 2>/dev/null; du -sh ~/fuzz/*corpus* 2>/dev/null | head -5"),
    ("disk", "df -h / | tail -1"),
]


def try_host(ip, label):
    print(f"### HOST {ip} ({label})")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(8)
    try:
        s.connect((ip, PORT))
        print(f"TCP:{ip}:22 OPEN")
    except Exception as e:
        print(f"TCP:{ip}:22 UNREACHABLE ({e.__class__.__name__})")
        s.close()
        return False
    s.close()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # password kwarg is REQUIRED — without it you get
        # "No authentication methods available" even when TCP:22 is open.
        client.connect(ip, port=PORT, username=USER, password=load_password(),
                       timeout=8, banner_timeout=8, auth_timeout=8,
                       allow_agent=False, look_for_keys=False)
    except Exception as e:
        print(f"SSH AUTH FAILED ({e.__class__.__name__}: {str(e)[:80]})")
        return False
    print("SSH OK")
    for name, cmd in CMDS:
        try:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=12)
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()
            print(f"[{name}] rc={stdout.channel.recv_exit_status()}")
            if out:
                print(out[:600])
            if err:
                print(f"  stderr: {err[:200]}")
        except Exception as e:
            print(f"[{name}] TIMEOUT/ERR ({e.__class__.__name__})")
    client.close()
    return True


if __name__ == "__main__":
    ok = False
    for ip, label in HOSTS:
        if try_host(ip, label):
            ok = True
            break
        print("---")
    print("RESULT:", "REACHED" if ok else "UNREACHABLE_ALL")
