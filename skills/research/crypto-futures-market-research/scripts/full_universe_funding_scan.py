#!/usr/bin/env python
"""Full-universe Binance USDT-perp scan: funding extremes, OI/volume anomalies, distribution.

Usage:  python full_universe_funding_scan.py
Prints: pair count + total volume, ALL funding extremes (|f| >= 0.05% per 8h),
highest OI/VOL ratios (parked positions), distribution candidates (volume spike
without price confirmation), funding trend for top extremes, and long/short
crowding for top extremes + majors.

Verified live Aug 2026 (675 USDT pairs; premiumIndex returns 857 symbols).
Key facts baked in:
- /fapi/v1/premiumIndex with NO args = whole universe; lastFundingRate = current/next-interval
- /fapi/v1/openInterest REQUIRES ?symbol= (thread it, ~20 workers)
- futures 24hr ticker field is `lastPrice`, NOT `price`
- non-ASCII symbols (e.g. 龙虾USDT) crash prints -> skipped
- funding % is per 8h: x3 for daily cost
"""
import json
import urllib.request
import ssl
import sys
import io
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
CTX = ssl.create_default_context()

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        return json.loads(r.read().decode())

BASE = "https://fapi.binance.com"

tickers = get(BASE + "/fapi/v1/ticker/24hr")
prem = get(BASE + "/fapi/v1/premiumIndex")  # NO arg: whole universe, one call

pm_map = {}
for p in prem:
    try:
        pm_map[p["symbol"]] = float(p["lastFundingRate"])
    except Exception:
        pass

usdt = []
for t in tickers:
    sym = t.get("symbol", "")
    if sym.endswith("USDT") and sym.count("USDT") == 1:
        try:
            sym.encode("ascii")
        except UnicodeEncodeError:
            continue
        usdt.append({"sym": sym, "price": float(t["lastPrice"]),
                     "chg": float(t["priceChangePercent"]), "vol": float(t["quoteVolume"]),
                     "high": float(t["highPrice"]), "low": float(t["lowPrice"]),
                     "fund": pm_map.get(sym, float("nan"))})

print(f"TOTAL USDT PERP PAIRS: {len(usdt)}")
tot = sum(x["vol"] for x in usdt)
print(f"TOTAL 24H QUOTE VOL: {tot/1e9:.2f}B USDT")

def fetch_oi(sym):
    try:
        o = get(BASE + f"/fapi/v1/openInterest?symbol={sym}")
        return sym, float(o["openInterest"])
    except Exception:
        return sym, None

oi_raw = {}
with ThreadPoolExecutor(max_workers=20) as ex:
    for sym, oi in ex.map(fetch_oi, [x["sym"] for x in usdt]):
        oi_raw[sym] = oi

for x in usdt:
    oi = oi_raw.get(x["sym"])
    x["oi_usd"] = (oi or 0) * x["price"]
    x["oi_vol_ratio"] = x["oi_usd"] / x["vol"] if x["vol"] > 0 else float("inf")

print("\n=== FUNDING EXTREMES |fund| >= 0.05% per 8h ===")
ext = sorted([x for x in usdt if abs(x["fund"]) >= 0.0005], key=lambda x: -abs(x["fund"]))
print(f"count: {len(ext)}")
print(f"{'SYMBOL':<16}{'FUND%':>10}{'PRICE':>12}{'24H%':>8}{'VOL(M)':>10}{'OI(USD M)':>12}{'OI/VOL':>8}")
for x in ext:
    print(f"{x['sym']:<16}{x['fund']*100:>9.4f}%{x['price']:>12.6g}{x['chg']:>8.2f}{x['vol']/1e6:>10.1f}{x['oi_usd']/1e6:>12.1f}{x['oi_vol_ratio']:>8.2f}")

print("\n=== HIGHEST OI/VOL RATIO (vol>=10M; parked positions vs flow) ===")
big = sorted([x for x in usdt if x["vol"] >= 10e6], key=lambda x: -x["oi_vol_ratio"])[:25]
print(f"{'SYMBOL':<16}{'OI/VOL':>8}{'OI(USD M)':>12}{'VOL(M)':>10}{'24H%':>8}{'FUND%':>10}")
for x in big:
    print(f"{x['sym']:<16}{x['oi_vol_ratio']:>8.2f}{x['oi_usd']/1e6:>12.1f}{x['vol']/1e6:>10.1f}{x['chg']:>8.2f}{x['fund']*100:>9.4f}%")

print("\n=== DISTRIBUTION CANDIDATES (top-120 vol, range>=3%, |chg|<=35% of range) ===")
cands = []
for x in sorted(usdt, key=lambda x: -x["vol"])[:120]:
    if x["high"] > 0 and x["low"] > 0:
        rng = (x["high"] - x["low"]) / x["low"] * 100
        if rng >= 3 and abs(x["chg"]) <= 0.35 * rng:
            cands.append(x)
cands.sort(key=lambda x: -x["vol"])
print(f"{'SYMBOL':<16}{'VOL(M)':>10}{'24H%':>8}{'RANGE%':>9}{'CHG/RANGE':>10}{'OI(USD M)':>12}{'FUND%':>10}")
for x in cands[:20]:
    rng = (x["high"] - x["low"]) / x["low"] * 100
    print(f"{x['sym']:<16}{x['vol']/1e6:>10.1f}{x['chg']:>8.2f}{rng:>9.2f}{x['chg']/rng:>10.2f}{x['oi_usd']/1e6:>12.1f}{x['fund']*100:>9.4f}%")

print("\n=== FUNDING TREND (last 8 x 8h) for top extremes ===")
for x in ext[:12]:
    try:
        h = get(BASE + f"/fapi/v1/fundingRate?symbol={x['sym']}&limit=8")
        vals = [float(v["fundingRate"]) * 100 for v in h]
        trend = "".join("+" if v > 0 else "-" for v in vals)
        print(f"{x['sym']:<16} current={x['fund']*100:+.4f}% last_applied={vals[-1]:+.4f}% sign-trend: {trend}")
    except Exception:
        pass

print("\n=== LONG/SHORT ACCOUNT RATIO (top traders, 1h) ===")
watch = list(dict.fromkeys([x["sym"] for x in ext[:10]] + ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]))
for s in watch:
    try:
        d = get(BASE + f"/futures/data/topLongShortAccountRatio?symbol={s}&period=1h&limit=1")
        if d:
            r = d[-1]
            print(f"{s:<16} L/S={r['longShortRatio']:<6} long={float(r['longAccount'])*100:.1f}% short={float(r['shortAccount'])*100:.1f}%")
    except Exception:
        pass
