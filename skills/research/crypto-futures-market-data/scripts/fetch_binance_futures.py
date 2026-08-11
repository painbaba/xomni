#!/usr/bin/env python3
"""Binance Futures REST snapshot: extreme funding ranking + per-symbol funding/OI/L-S table.

Verified Aug 2026. Pure stdlib (urllib). No API key needed.
Usage:  python fetch_binance_futures.py [SYMBOL ...]   (defaults to BTC ETH SOL BNB XRP DOGE USDT perps)
Output: compact per-symbol lines ready to paste into a report table.
"""
import json
import sys
import time
import datetime
import urllib.request

BASE = "https://fapi.binance.com"
ALT = "https://data-api.binance.vision"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]

def get(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
                "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(1.5)
    return {"_error": str(last)}

def get_any(path, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE}{path}" + (("?" + qs) if qs else "")
    r = get(url)
    if "_error" not in r:
        return r
    r2 = get(f"{ALT}{path}" + (("?" + qs) if qs else ""))
    return r2 if "_error" not in r2 else {"_error": r["_error"], "_alt": r2["_error"]}

def ts(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%m-%d %H:%M")

def main():
    syms = [s.upper() for s in sys.argv[1:]] or SYMS
    print("NOW_UTC:", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    allpi = get_any("/fapi/v1/premiumIndex")
    if isinstance(allpi, list):
        ext = [p for p in allpi if p.get("symbol", "").endswith("USDT") and p.get("lastFundingRate")]
        ext.sort(key=lambda p: abs(float(p["lastFundingRate"])), reverse=True)
        print("\n=== TOP 15 extreme |funding| (all USDT perps) ===")
        for p in ext[:15]:
            print(f"{p['symbol']:<12} rate={p['lastFundingRate']:<12} next={ts(p['nextFundingTime'])}")
    else:
        print("premiumIndex(all) error:", allpi)

    for s in syms:
        if not s.endswith("USDT"):
            s += "USDT"
        print(f"\n===== {s} =====")
        pi = get_any("/fapi/v1/premiumIndex", symbol=s)
        fr = get_any("/fapi/v1/fundingRate", symbol=s, limit=4)
        oi = get_any("/fapi/v1/openInterest", symbol=s)
        oih = get_any("/futures/data/openInterestHist", symbol=s, period="4h", limit=30)
        gl = get_any("/futures/data/globalLongShortAccountRatio", symbol=s, period="1h", limit=12)
        tp = get_any("/futures/data/topLongShortPositionRatio", symbol=s, period="1h", limit=12)
        ta = get_any("/futures/data/topLongShortAccountRatio", symbol=s, period="1h", limit=12)
        t24 = get_any("/fapi/v1/ticker/24hr", symbol=s)
        if isinstance(pi, dict):
            print("mark:", pi.get("markPrice"), "| current funding:", pi.get("lastFundingRate"),
                  "| next funding:", ts(pi.get("nextFundingTime", 0)))
        if isinstance(fr, list) and fr:
            print("  paid (last 3):", " | ".join(f"{ts(f['fundingTime'])} {f['fundingRate']}" for f in fr[-3:]))
        if isinstance(oih, list) and oih:
            vals = [float(x["sumOpenInterest"]) for x in oih]
            c24 = (vals[-1] / vals[-7] - 1) * 100 if len(vals) >= 7 else None
            c5d = (vals[-1] / vals[0] - 1) * 100
            print(f"OI now {vals[-1]:,.0f} ct | 24h {c24:+.2f}% | 5d {c5d:+.2f}% | 5d-ago {vals[0]:,.0f} ({ts(oih[0]['timestamp'])})")
        if isinstance(gl, list) and gl:
            print("global L/S acct ratio (1h, last6):", " ".join(x["longShortRatio"] for x in gl[-6:]))
        if isinstance(tp, list) and tp:
            t = tp[-1]
            print(f"top-trader L/S POSITION (1h): {t['longShortRatio']} (long {t['longAccount']} / short {t['shortAccount']})")
        if isinstance(ta, list) and ta:
            a = ta[-1]
            print(f"top-trader L/S ACCOUNT (1h): {a['longShortRatio']} (long {a['longAccount']} / short {a['shortAccount']})")
        if isinstance(t24, dict):
            print("24h: price", t24.get("lastPrice"), "| chg", t24.get("priceChangePercent") + "%",
                  "| quoteVol", t24.get("quoteVolume"))

if __name__ == "__main__":
    main()
