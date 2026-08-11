#!/usr/bin/env python3
"""paramiko phase skeleton — remote ASAN/fuzz workflow on a Kali/VM box.

Split the whole job into PHASE scripts (upload+build / launch / poll / finalize+pull).
One SSH exec that loops over thousands of items will hit paramiko PipeTimeout.
Run with the python that has paramiko (check: python -c "import paramiko").

Known pitfalls encoded here:
- mkdir -p the remote dir BEFORE sftp.put  (else [Errno 2] No such file)
- remote shell may be zsh: unquoted globs with no matches abort the whole command
- tar bundles locally, one transfer per bundle, retry each put (flaky network)
- nohup long fuzz runs; poll with a separate lightweight script
"""
import os, sys, time
import paramiko

HOSTS = ["192.168.29.35", "192.168.56.101"]   # primary + fallback
USER = "user"
PASS = "password"
LOCAL = os.path.dirname(os.path.abspath(__file__))

def log(msg):
    print(msg, flush=True)

def ssh_exec(cli, cmd, timeout=120):
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err

def connect():
    last = None
    for h in HOSTS:
        for attempt in range(3):
            try:
                cli = paramiko.SSHClient()
                cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                cli.connect(h, username=USER, password=PASS, timeout=12,
                            banner_timeout=12, auth_timeout=12)
                log(f"[+] connected to {h}")
                return cli, h
            except Exception as e:
                last = e
                time.sleep(3)
    raise RuntimeError(f"all hosts failed: {last}")

def sftp_put(cli, local, remote, tries=5):
    sftp = cli.open_sftp()
    try:
        for i in range(tries):
            try:
                sftp.put(local, remote)
                log(f"[+] uploaded {os.path.basename(local)}")
                return
            except Exception as e:
                log(f"[-] put try {i+1}: {e}")
                time.sleep(4)
        raise RuntimeError(f"upload failed for {local}")
    finally:
        sftp.close()

def phase_upload_and_build():
    cli, host = connect()
    try:
        # remote dir MUST exist before any sftp.put
        rc, out, err = ssh_exec(cli, "mkdir -p ~/fuzzwork && echo ok")
        for b in ["src.tar.gz", "payloads.tar.gz"]:
            sftp_put(cli, os.path.join(LOCAL, b), f"/home/{USER}/fuzzwork/{b}")
        # extract + compile: C sources via clang, link via clang++ (see SKILL.md §3)
        rc, out, err = ssh_exec(cli, "cd ~/fuzzwork && tar xzf src.tar.gz && tar xzf payloads.tar.gz && "
                                      "clang -O1 -g -fno-omit-frame-pointer -fsanitize=address,fuzzer-no-link "
                                      "-I src -c src/*.c && "
                                      "clang++ -O1 -g -fno-omit-frame-pointer -fsanitize=address,fuzzer "
                                      "-I src fuzz_entry.cpp *.o -o fuzz_asan 2>&1", timeout=300)
        log(f"build rc={rc}\n{out}{err}")
    finally:
        cli.close()

def phase_launch_fuzz():
    cli, host = connect()
    try:
        # zsh-safe: no unquoted globs that could match nothing
        rc, out, err = ssh_exec(cli,
            "cd ~/fuzzwork && rm -rf corpus crash_ fuzz.log && mkdir -p corpus && "
            "cp trigger.bin corpus/ && cp gif_seeds/*.gif corpus/ 2>/dev/null; "
            "ASAN_OPTIONS=abort_on_error=1:symbolize=1:detect_leaks=0 "
            "nohup ./fuzz_asan -fork=6 -ignore_crashes=1 -ignore_timeouts=1 "
            "-artifact_prefix=crash_ -max_total_time=1800 -max_len=8192 -timeout=10 "
            "-use_value_profile=1 corpus/ > fuzz.log 2>&1 & echo PID=$!; sleep 10; "
            "pgrep -fc fuzz_asan; tail -4 fuzz.log", timeout=90)
        log(f"launch:\n{out}{err}")
    finally:
        cli.close()

def phase_poll():
    cli, host = connect()
    try:
        rc, out, err = ssh_exec(cli,
            "cd ~/fuzzwork && echo 'alive:'; pgrep -fc fuzz_asan; "
            "echo 'stats:'; grep -E '^#' fuzz.log | tail -2; "
            "echo 'artifacts:'; ls crash_* 2>/dev/null | wc -l; "
            "echo 'error types:'; grep -oE 'ERROR: AddressSanitizer: [a-z-]+' fuzz.log | sort | uniq -c; "
            "echo 'deadly:'; grep -cE 'deadly signal' fuzz.log; "
            "echo 'done:'; grep -c 'DONE' fuzz.log", timeout=90)
        log(f"{out}{err}")
    finally:
        cli.close()

def phase_finalize():
    cli, host = connect()
    try:
        # hash-dedupe artifacts, sample-run a few; don't re-run thousands (slow)
        rc, out, err = ssh_exec(cli,
            "cd ~/fuzzwork && pkill -f fuzz_asan; "
            "echo 'unique artifact hashes:'; sha256sum crash_* | awk '{print $1}' | sort -u | wc -l; "
            "for f in $(sha256sum crash_* | sort -k1,1 -u | awk '{print $2}' | head -5); do "
            "echo \"=== $f\"; ASAN_OPTIONS=abort_on_error=1:detect_leaks=0 ./fuzz_asan \"$f\" 2>&1 | "
            "grep -E 'ERROR: AddressSanitizer|SUMMARY|#1 ' | head -6; done", timeout=300)
        log(f"{out}{err}")
        # pull evidence
        sftp = cli.open_sftp()
        try:
            for f in ["fuzz.log", "seed_run.log"]:
                sftp.get(f"/home/{USER}/fuzzwork/{f}", os.path.join(LOCAL, f))
        finally:
            sftp.close()
    finally:
        cli.close()

if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "poll"
    {"upload": phase_upload_and_build, "launch": phase_launch_fuzz,
     "poll": phase_poll, "finalize": phase_finalize}[phase]()
