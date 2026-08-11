# Observed errors & findings (host: Windows 10/11, git-bash, non-admin, no Npcap)

Exact strings to recognize / reuse as report evidence.

## Windows non-admin packet-crafting blocks (kernel-enforced)
- scapy L3 send (sr1/send with spoofed src), no Npcap:
  `OSError: Windows native L3 Raw sockets are only usable as administrator ! Please install Npcap to workaround !`
  (comes from scapy's L3WinSocket; `wpcap.dll missing` warning printed first)
- Python `socket.socket(AF_INET, SOCK_RAW, IPPROTO_RAW)`:
  `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`
- Raw `IPPROTO_ICMP` socket: **opens** without admin (ping compat), but `sendto()`
  of a crafted ICMP echo (with or without IP_HDRINCL) → same WinError 10013.
- `pktmon start --capture` / `netsh trace`: "Failed to obtain Packet Monitor
  status" / requires elevation. No capture channel without admin either.
- MAC change: `Set-NetAdapter -Name "Wi-Fi" -MacAddress ...` →
  `Access is denied ... Windows System Error 5, Set-NetAdapter` (CimException,
  PermissionDenied). Registry NetworkAddress path also needs admin.

## Windows ephemeral ports are SEQUENTIAL
10 TCP connects to router:80 → src ports 59901,59902,...,59910 (consecutive).
Windows allocates ephemeral ports from the dynamic range deterministically —
"port rotation" is real but is itself a host fingerprint (unlike Linux
randomized ports). Router conntrack ties srcPort↔IP↔MAC anyway.

## Jio Centrum Home Gateway recon (JCOW404)
- Web UI: http://192.168.29.1/ → title "Jio Centrum Home Gateway", Server: Web Server.
- Port 8080: `HTTP/1.1 503 Service Unavailable`, `Server: JCOW404/JUICEJFV-1.3.32`
  — NOT a usable proxy (CONNECT → empty/503).
- Port 80 CONNECT probe → `HTTP/1.1 501 Not Implemented` (web server, not proxy).
- Port 3128/1080/8888: filtered/timeout.
- DNS on .1: resolver name `reliance.reliance` (Jio ISP DNS) — open on LAN, answers
  for anyone; queries carry the requester's real IP (logs you).
- DHCP lease table (defender view): IP ↔ MAC ↔ hostname (hostname always leaks).
  On this host: 192.168.29.55 ↔ 2C-3B-70-E3-71-F7 ↔ LAPTOP-SE92NP1U, 24h lease.

## Recognition notes
- scapy `get_if_list()` returns many `\Device\NPF_{GUID}` names (TAP/VirtualBox/
  Wi-Fi Direct adapters) even when Npcap is NOT usable — NPF names ≠ working L2.
  Trust `conf.L2socket` ("wpcap.dll missing") instead.
- `ipconfig /all` Physical Address may show a DIFFERENT MAC than `getmac /v` /
  `Get-NetAdapter` for other adapters (Wi-Fi Direct virtual, randomized MACs).
  The active NIC's MAC = `Get-NetAdapter -Name <NIC> | select MacAddress`.
