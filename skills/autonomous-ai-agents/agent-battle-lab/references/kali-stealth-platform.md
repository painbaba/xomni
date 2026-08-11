# Kali VM stealth platform — verified recipe (Aug 2026)

Lab: Kali 2024+ on VirtualBox (bridged), 192.168.29.35, user `painbaba`, root via `/tmp/rsudo`
(SUDO_ASKPASS wrapper: `/tmp/askpass.sh` echoes the password). SSH helper `kali_ssh.py`
(paramiko; `run(cmd, sudo=True)` base64-wraps remote commands, `put(path, content)` for
verbatim file pushes). Evidence convention: pcaps on VM under `/tmp/*.pcap`; report files in
`C:\Users\HP\ai-workforce\ghost-lab\ghost_sandbox\`.

## 1. Tor + onion service (masked path to the VM)
```bash
# append to /etc/tor/torrc — MUST be sudo; plain '>>' as user fails SILENTLY
/tmp/rsudo bash -c 'printf "HiddenServiceDir /var/lib/tor/ghost_hs/\nHiddenServicePort 22 127.0.0.1:22\n" >> /etc/tor/torrc'
/tmp/rsudo systemctl enable --now tor
# wait for the hostname file (loop up to ~40s); reading it needs sudo
/tmp/rsudo cat /var/lib/tor/ghost_hs/hostname   # -> 2vpiwe....onion
```
- Keys persist in the HiddenServiceDir → SAME onion address across tor restarts/reboots (critical for persistence phases).
- Verify egress: `curl --socks5-hostname 127.0.0.1:9050 https://api.ipify.org` → Tor exit IP (≠ direct IP).
- Direct IP vs Tor exit (observed): 49.36.18.125 vs 45.84.107.182 / 185.220.101.148 (rotates per circuit).

## 2. SSH through the onion (the masked path, host→VM)
- Kali's `nc` is netcat-traditional: `nc -X 5 -x ...` fails (`invalid option -- 'X'`). Use **socat** (installed):
```bash
ssh -i ~/.ssh/ghost_tunnel \
  -o ProxyCommand="socat - SOCKS4A:127.0.0.1:%h:%p,socksport=9050" \
  -o StrictHostKeyChecking=no painbaba@<onion> 'hostname'   # SOCKS4a → Tor resolves .onion remotely
```
- Self-tunnel key: `ssh-keygen -t ed25519 -N '' -f ~/.ssh/ghost_tunnel && cat ~/.ssh/ghost_tunnel.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`.

## 3. Persistent tunnel (autossh + systemd) — THE `-D` LEAK
`/etc/systemd/system/ghost-tunnel.service` (autossh installed via `apt-get install -y autossh`):
```ini
[Unit]
Description=Ghost persistent SSH tunnel via Tor onion (masked path)
After=network-online.target tor.service
Wants=network-online.target tor.service

[Service]
User=painbaba
ExecStart=/usr/bin/autossh -M 0 -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no \
  -i /home/painbaba/.ssh/ghost_tunnel \
  -o ProxyCommand="socat - SOCKS4A:127.0.0.1:%%h:%%p,socksport=9050" \
  -L 127.0.0.1:19050:127.0.0.1:9050 painbaba@<onion>
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
- **`%%h`/`%%p`**: systemd ExecStart specifiers — `%h` would be expanded to the user's home dir. `%%` escapes to a literal `%` that ssh then substitutes (onion host / port) inside ProxyCommand.
- **Do NOT use `-D` for a self-loop tunnel**: SSH from the VM to its own onion with `-D 127.0.0.1:19050` binds a SOCKS whose destination connections are made by the REMOTE end of the SSH channel — the VM itself — so traffic exits with the REAL IP (observed: TUNNEL_EGRESS 49.36.18.125 while 9050 egress was a Tor exit). `-L` into `127.0.0.1:9050` chains the tunnel through the VM's own Tor SOCKS → Tor-exit egress.
- **Always verify tunnel egress end-to-end**, never just `ss -tln | grep <port>`: `curl --socks5-hostname 127.0.0.1:19050 https://api.ipify.org` must show a Tor exit, not the direct IP.

## 4. Decoy hostname (router-visible)
```bash
/tmp/rsudo hostnamectl set-hostname media-pc
/tmp/rsudo nmcli connection modify "Wired connection 1" ipv4.dhcp-hostname media-pc ipv4.dhcp-send-hostname yes
/tmp/rsudo nmcli connection up "Wired connection 1"    # renew pushes DHCP option 12
echo '127.0.1.1 media-pc' >> /etc/hosts                # silences sudo "unable to resolve host" warnings
```
- Client-side verify: `nmcli -f DHCP4.OPTION device show eth0` → `host_name = media-pc`.
  **Field is `DHCP4.OPTION` (singular)** — `DHCP4.OPTIONS` errors (`invalid field`).
- Router-side verify (what the network actually sees): the Jio Centrum UI is a dead end for this —
  `platform.cgi?page=dhcp.html` and every guessed lease-table endpoint return the same 1306-byte
  login shell (no table data). Real proof = WIRE CAPTURE during a renew:
```bash
# ONE remote invocation — a separately backgrounded tcpdump DIES when the SSH channel closes
setsid /tmp/rsudo tcpdump -i eth0 -w /tmp/dhcp_media.pcap 'port 67 or port 68 or arp' >/tmp/dump.log 2>&1 &
sleep 2; /tmp/rsudo nmcli connection up 'Wired connection 1' 2>/dev/null
/tmp/rsudo dhclient -r eth0 2>/dev/null; sleep 2; /tmp/rsudo dhclient eth0 2>/dev/null; sleep 8
/tmp/rsudo pkill -f 'tcpdump -i eth0'
tshark -r /tmp/dhcp_media.pcap -Y dhcp -T fields -e ip.src -e ip.dst -e dhcp.option.hostname -e dhcp.option.dhcp
```
  Observed proof: client DHCPREQUEST `0.0.0.0 → 255.255.255.255 hostname=media-pc` and the router's
  DHCPACK `192.168.29.1 → ... hostname=media-pc` — the server accepted AND echoed the decoy.
  ARP rows show the router (192.168.29.1) sweeping/tracking the client.

## 5. Lab ops notes
- VBoxManage NOT on git-bash PATH → full path: `"/c/Program Files/Oracle/VirtualBox/VBoxManage.exe" list vms`.
  This lab's running VM is named **"kali hacker"** (several other Kali VMs exist but are off).
- `apt-get install` on the VM can outlast the SSH helper's read timeout → the remote script dies with
  the channel mid-install. Re-run the idempotent script (guards: `which autossh`, `[ -f key ]`).
- Service restarts / unit overwrites on the VM may hit an approval gate (one restart was denied
  mid-session). If a command is blocked: STOP, ask, don't retry via a different command.
- Recovery path (from earlier sessions, see stealth_v3_resume.md): if the guest network dies on both
  NICs, `VBoxManage controlvm reset` + host-only DHCP lease recovery (192.168.56.101) + bridged re-up.
  After reboot, NetworkManager auto-brings eth0 back (profile autoconnect) — DHCP may re-lease.
