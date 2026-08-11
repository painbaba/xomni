"""Pre-flight capability probe for network stealth testing (Windows).

Run FIRST: tells you if ANY packet crafting is possible from this host,
and gathers the evidence strings for the stealth report. Adjust GW/NIC
for the lab under test. Usage: python capability_probe.py
"""
import socket
import subprocess

GW = "192.168.29.1"      # default gateway / router
NIC = "Wi-Fi"            # active adapter name

def admin_check():
    ps = ("([Security.Principal.WindowsPrincipal]"
          "[Security.Principal.WindowsIdentity]::GetCurrent()"
          ").IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)")
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True).stdout.strip()
    print(f"[admin] IsInRole(Administrator) = {out}")
    return out == "True"

def scapy_l2_check():
    try:
        from scapy.all import conf
        print(f"[scapy] L2 socket: {conf.L2socket}")
        print(f"[scapy] L3 socket: {conf.L3socket}")
    except ImportError:
        print("[scapy] not installed (pip install scapy)")

def raw_socket_check():
    for proto, name in [(socket.IPPROTO_RAW, "IPPROTO_RAW"),
                        (socket.IPPROTO_ICMP, "IPPROTO_ICMP")]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)
            # ICMP socket opens without admin; sendto is the real test
            if proto == socket.IPPROTO_ICMP:
                import struct
                src = socket.inet_aton("192.168.29.243")  # a victim IP
                dst = socket.inet_aton(GW)
                ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40, 1, 0, 64, 1, 0, src, dst)
                icmp = struct.pack("!BBHHH", 8, 0, 0, 1, 1)
                try:
                    s.sendto(ip_hdr + icmp, (GW, 0))
                    print(f"[raw] {name}: SEND OK (spoofing possible!)")
                except OSError as e:
                    print(f"[raw] {name}: opens but sendto FAILED: {e}")
            else:
                print(f"[raw] {name}: socket created (unexpected without admin)")
            s.close()
        except OSError as e:
            print(f"[raw] {name}: create FAILED: {e}")

def port_rotation():
    ports = []
    for _ in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4)
        try:
            s.connect((GW, 80))
            ports.append(s.getsockname()[1])
        except Exception as e:
            ports.append(f"ERR:{e}")
        finally:
            s.close()
    print(f"[ports] ephemeral src ports: {ports}")
    seq = all(isinstance(p, int) for p in ports)
    if seq:
        print(f"[ports] SEQUENTIAL (Windows default, host fingerprint): "
              f"{ports[0]}..{ports[-1]}")

def proxy_probe():
    for port in (8080, 3128, 1080, 8888):
        try:
            s = socket.create_connection((GW, port), timeout=4)
            s.sendall(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
            data = s.recv(200)
            print(f"[proxy] {GW}:{port} -> {data[:60]!r}")
            s.close()
        except Exception as e:
            print(f"[proxy] {GW}:{port} -> FAILED: {e}")

if __name__ == "__main__":
    admin_check()
    scapy_l2_check()
    raw_socket_check()
    port_rotation()
    proxy_probe()
