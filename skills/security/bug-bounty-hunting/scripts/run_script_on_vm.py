#!/usr/bin/env python3
"""Run a local bash script on the Kali VM via paramiko (stdin to `bash -s`).

Usage: python run_script_on_vm.py <local_script.sh> [timeout_sec]

- Executes the ENTIRE script remotely with one SSH session (no quoting hell:
  write the script to a file locally, this runner streams it to the remote
  shell's stdin).
- Tries the primary Kali host, falls back to the secondary host.
- Prints merged stdout/stderr + EXITCODE.
- Scripts run in the remote user's home dir (~); the remote script does its own
  `cd`/`mkdir` for workspace hygiene.

Credentials match ssh_kali.py on disk (painbaba@192.168.29.35 /
192.168.56.101). Override password with env var KALI_PASS if it rotates.
"""
import os
import sys
import paramiko

HOSTS = ["192.168.29.35", "192.168.56.101"]
USER = "painbaba"
PASS = os.environ.get("KALI_PASS", "3775364553")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    script_path = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    with open(script_path, "r", encoding="utf-8") as f:
        script = f.read()

    last = None
    for h in HOSTS:
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(h, username=USER, password=PASS, timeout=20,
                      banner_timeout=20, auth_timeout=20)
            stdin, stdout, stderr = c.exec_command("bash -s", timeout=timeout)
            stdin.write(script)
            stdin.channel.shutdown_write()
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            rc = stdout.channel.recv_exit_status()
            c.close()
            print(f"[host={h}]")
            if out:
                print(out)
            if err:
                print("[stderr]", err)
            print(f"EXITCODE={rc}")
            last = rc
            break
        except Exception as e:
            print(f"[host={h}] FAILED: {e}", file=sys.stderr)
    sys.exit(last if last is not None else 1)


if __name__ == "__main__":
    main()
