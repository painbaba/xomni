# ASAN+libFuzzer on a Linux VM (Kali) — closing the Windows ASAN gap

Why: Windows/zig `cc` cannot link ASAN (`undefined __asan_*` symbols) — heap OOB
WRITES (the RCE-class bug) were undetectable with UBSAN-only fuzzing. A Linux VM
with clang gives real ASAN + libFuzzer + qemu-user in one box. Proven 2026-08-09.

## VM access chain (VirtualBox + Kali, all quirks hit)
- Find VMs: `VBoxManage list vms` / `runningvms`. The research VM is `kali hacker`
  (bridged Wi-Fi NIC → LAN IP 192.168.29.35; host-only NIC → 192.168.56.10x).
- Guest IPs: `VBoxManage guestproperty enumerate "<vm>" | grep V4/IP` (only after
  GuestAdditions/VBoxService is up — i.e. after a user session starts).
- Headless boot leaves Kali at the LOGIN SCREEN (no services, sshd down, guest
  control "not ready"). Fix: type login via scancode injection —
  `VBoxManage controlvm "<vm>" keyboardputscancode <hex sc> ...` (ASCII→PS/2
  scancodes: a=1e p=19 i=17 n=31 b=30, 0=0b 1=02 2=03 3=04 4=05 5=0e 6=07 7=08,
  enter=1c 9c). Screenshot to verify: `controlvm ... screenshotpng C:\path.png`.
- Host-only NIC cannot be hot-plugged onto a disabled NIC while running; attach
  while powered off (`modifyvm --nic2 hostonly --hostonlyadapter2 "<name>"`),
  then power on. Flaky: VM network renegotiates (IP flips .35 ↔ .56.10x) — scan
  both subnets' port 22 and retry connects with short timeouts.
- SSH: no sshpass/expect on Windows → `pip install paramiko`; connect in a
  python heredoc (password auth), keep a `kali_ssh.py` helper (connect + run).

## Transfer discipline (flaky VM network)
NEVER SFTP hundreds of files — the connection drops mid-stream (observed ~200
files lost, socket closed). Tar locally (`tar -czf x.tgz -C dir subdirs...`),
SFTP ONE tarball with retry loop (3 attempts, fresh sftp handle per retry),
extract remotely. Decoder source only — exclude encoder/arm/s files.

## clang ASAN+libFuzzer build recipe (libhevc, libavc)
```bash
clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer -fno-omit-frame-pointer \
  -DDISABLE_AVX2 -I <root> -I <root>/decoder -I <root>/common -I <root>/common/x86 \
  -I <root>/decoder/x86 -I <root>/fuzzer \
  <root>/fuzzer/hevc_dec_fuzzer.cpp \        # has LLVMFuzzerTestOneInput
  -x c <root>/decoder/*.c <root>/decoder/x86/*.c <root>/common/*.c <root>/common/x86/*.c \
  -o fuzz_hevc_asan
```
- `.c` files MUST be compiled as C (`-x c`) — clang++ treats them as C++ and
  errors on implicit void* casts in ittiam code.
- `-msse4.1` required or always_inline SSE4 intrinsics fail.
- Windows harness edits break Linux builds: `sed -i 's/_aligned_free/free/g'`
  and struct member is `pf_aligned_free` (NOT `pffree`) in this AOSP snapshot.
- Do NOT add your own main/cov callback — libFuzzer provides both; the harness's
  LLVMFuzzerTestOneInput is the entry. Duplicate `__sanitizer_cov_trace_pc` =
  multiple-definition link error.
- Missing avx2 selector file → `-DDISABLE_AVX2`.

## Running + artifact capture
```bash
nohup timeout 3600 ./fuzz_hevc_asan corpus/ -max_len=200000 -timeout=10 \
  -rss_limit_mb=3000 -artifact_prefix=hevc_ > fuzz_hevc_asan.log 2>&1 &
```
- Crashes land as `hevc_<hash>`; timeout units as `timeout-<hash>`.
- grep `ERROR: AddressSanitizer` in the log for the report; `-B2 -A35` for the
  stack; class = heap-buffer-overflow WRITE vs READ / use-after-free /
  double-free / SEGV. SFTP artifacts to Windows with descriptive names.
- exec/s drops with corpus growth (5→1/s); ASAN overhead ~2x over UBSAN.
- libFuzzer timeout units are NOT automatically bugs: verify natively — the
  "slowest unit" decoded in 0.37s natively (fuzzer-config artifact, not a DoS).

## Severity verification chain (run before claiming)
1. ASAN single-shot: `timeout 20 ./fuzz_<lib>_asan -runs=1 <file>` (or tiny main
   calling LLVMFuzzerTestOneInput) — exit 139 = SEGV, 0 = clean.
2. Patched-vs-unpatched cross-check: same input on a triage-patched build
   proves whether the bug (e.g. NULL+offset) executes or is arithmetic-only.
3. aarch64 cross-build + qemu-user: `gcc-aarch64-linux-gnu -static` (install
   gcc-aarch64-linux-gnu + qemu-user via sudo; SUDO_PASSWORD in .env, feed via
   `echo '<pw>' | sudo -S apt-get install ...` on the VM) then
   `qemu-aarch64 ./prog`. ARM64 silently allows unaligned loads — verify before
   claiming an ARM fault class.
4. NVD novelty gate: `https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=<lib>&resultsPerPage=20`.

## Parallel-agent swarm pattern (user directive: "deploy parallel agents")
Wave batches of 4 delegate_task agents, each self-contained with the VM creds +
exact build/run commands in context. Assign one surface per agent (libavc ASAN,
giflib verify, dav1d build, artifact sweep...). Agents die on API errors
mid-task — resume by re-dispatching the same goal in the next wave (check
`ls ~/fuzz/` state first to avoid redoing transfers). Watch progress via
`cache/delegation/live/<deleg_id>/task-<n>.log` tails. Consolidated results
re-enter as one message when a wave completes.

## Evidence pulled to Windows (2026-08-09)
gif_asan_seed_run.log, gif_fuzz30.log, gif_evidence.tar.gz (giflib double-free,
2763 ASAN crashes); libavc timeout units (artifact, not DoS); KALI_FUZZ_STATUS.md
(per-fuzzer table) — all under C:\Users\HP\ai-workforce\aosp-audit\.
