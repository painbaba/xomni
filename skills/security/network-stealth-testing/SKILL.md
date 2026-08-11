---
name: network-stealth-testing
description: Test LAN IP/MAC spoofing capability with detection angles.
---

# Network Stealth Testing (masking capability assessment)

Authorized-lab procedure: determine what a host can ACTUALLY hide on a LAN — per capability, with live evidence and an honest detection angle for each — then write a stealth report. Used for ghost-side capability assessment before battle-lab ops / red-team missions. SCOPE: authorized lab networks and test devices only.

## Step 0: capability gates (check in order — they decide everything)
0. **Do you have a root Linux box / Kali VM on the LAN?** If YES, skip the Windows gates below — every capability flips to testable. Full recipes + verified findings: `references/kali-vm-findings.md`. TL;DR: ARP MITM works bidirectionally (even against routers with no ARP protection), Tor/proxychains egress works, hostname masking works via nmcli (NOT via bare `hostname`), DNS injection works but the router never answers. Use the VM's eth0 as the MITM/egress point instead of the Windows host.
1. **Admin?** `powershell -NoProfile -Command '([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)'` → False on this host.
2. **Npcap?** `python -c "from scapy.all import conf; print(conf.L2socket)"` — `wpcap.dll missing` = no L2 socket = no ARP spoofing, no sniffing. Npcap install needs admin.
3. **Raw socket?** `socket.socket(AF_INET, SOCK_RAW, IPPROTO_RAW)` → WinError 10013 without admin.

**Windows non-admin reality (kernel-enforced, verified):**
- scapy L3 send: *"Windows native L3 Raw sockets are only usable as administrator! Please install Npcap to workaround!"*
- `SOCK_RAW` create → `[WinError 10013]`; raw **ICMP** socket *opens* (ping compat) but `sendto` → 10013.
- `pktmon`/`netsh trace` capture also need admin.
- Conclusion: non-admin Windows sends ZERO crafted packets — no IP spoofing, no DNS masquerade, no ARP. Don't burn time trying; document as blocked with the exact error strings as evidence.

## Capability matrix (test each; record evidence + detection angle)
1. **MAC masking**: `Set-NetAdapter -Name <NIC> -MacAddress ...` → error 5 without admin (registry path too). Detection: DHCP lease + AP see burned-in MAC; Wi-Fi AP sees client MAC in every 802.11 frame; lease persists after you leave. Don't confuse randomized locally-administered MACs (2/6/A/E second nibble) on other adapters with the active NIC.
2. **IP spoofing (scapy)**: gated by raw socket. Even if it worked: replies route to the VICTIM (asymmetry — you never receive them); L2 src MAC is still yours → trivial correlation. Always note the send-vs-receive asymmetry.
3. **ARP spoofing MITM**: needs L2/Npcap only. If possible, cleanup is mandatory: re-ARP victim AND gateway with real MACs, verify both caches via `arp -a`. If impossible: state "nothing poisoned → nothing to clean", verify ARP cache intact post-test.
4. **Proxy / source-port rotation**: probe router: bash `/dev/tcp` loop over 8080 3128 1080 8888; then CONNECT probe (real proxy → 200, web server → 501, dead → timeout/empty). Check `netsh winhttp show proxy` + `reg query HKCU\...\Internet Settings /v ProxyServer`. Windows ephemeral ports are SEQUENTIAL not randomized (observed 59901→59910) — rotation "works" but is itself a host fingerprint; conntrack pins port↔IP↔MAC.
5. **DNS masquerade**: needs raw socket (blocked non-admin). Replies go to victim, never you. Legit queries carry your real IP — resolver logs you.

## Leak test (what a defender sees)
- DHCP lease table (router web UI, e.g. Jio Centrum :80): IP ↔ MAC ↔ hostname — hostname ALWAYS leaks via DHCP (unless masked via nmcli dhcp-hostname; see Kali reference).
- Router access logs: every probe you sent, logged with your real IP.
- Peer `arp -a` pins your IP↔MAC.
- No IPv6 / no alternate egress (VPN TAP/TUN disconnected) = single identity.
- MAC OUI itself is a fingerprint: 08:00:27 = Oracle/VirtualBox marks the ghost as a VM in any lease/ARP inventory.

## Report format (user standard — stealth_report.md)
- Per-capability section: verdict (**NO / PARTIAL / YES**) + evidence (exact error strings, port numbers, observed values) + `*Detection:*` angle.
- Final `## Verdict`: what the ghost can hide vs what leaks, plus "best possible combo if elevated".
- `*Cleanup:*` line — state what was/wasn't altered, verify post-state (MAC/IP/ARP unchanged).
- Word-limit discipline: `wc -w` counts markdown symbols (`→`, `↔`, backticks) as words — target ~5% under the limit.

## Support files
- `scripts/capability_probe.py` — pre-flight probe: admin + raw socket + ephemeral-port rotation + proxy CONNECT. Run FIRST, before any per-capability test.
- `scripts/arp_mitm_test.py` — bidirectional ARP-spoof MITM w/ clean restore (run on Kali as root; capture in parallel with tcpdump for proof).
- `references/observed-errors.md` — exact error strings and this-host findings (Jio Centrum gateway, sequential ports, 10013 evidence) for recognition.
- `references/kali-vm-findings.md` — Kali/root-Linux branch: working recipes for ARP MITM (bidirectional + clean restore), Tor/proxychains egress (incl. user-conf override pitfall), Tor onion service for zero-exposed-port SSH, DNS injection, nmcli hostname masking, VirtualBox VM recovery, and SSH/sudo-over-paramiko quoting traps.
