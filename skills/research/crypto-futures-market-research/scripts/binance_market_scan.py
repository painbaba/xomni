#!/usr/bin/env python
"""Scan EVERY USDT perpetual pair on Binance Futures (live, public API, no key).

Usage:  python binance_market_scan.py
Prints: pair count, majors, top-30 by 24h volume, top gainers/losers across ALL
pairs, funding + OI for leaders/movers, and long/short crowding on majors.

Verified live Aug 2026 (678 USDT pairs). Pitfalls baked in:
- futures 24hr ticker field is `lastPrice`, NOT `price`
- /fapi/v1/openInterest REQUIRES ?symbol= (batch call 400s)
- non-ASCII symbols (e.g. 龙虾USDT) crash prints -> skipped here
"""
import json
import urllib.request
import ssl

CTX = ssl.create_default_context()

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        return json.loads(r.read().decode())

BASE = "https://fapi.binance.com"

tickers = get(BASE + "/fapi/v1/ticker/24hr")
usdt = []
for t in tickers:
    sym = t.get("symbol", "")
    if sym.endswith("USDT") and sym.count("USDT") == 1:
        try:
            sym.encode("ascii")
        except UnicodeEncodeError:
            continue
        usdt.append({
            "sym": sym,
            "price": float(t["lastPrice"]),
            "chg": float(t["priceChangePercent"]),
            "vol": float(t["quoteVolume"]),
            "high": float(t["highPrice"]),
            "low": float(t["lowPrice"]),
        })

print(f"TOTAL USDT PERP PAIRS: {len(usdt)}")
tot = sum(x["vol"] for x in usdt)
btc = next((x for x in usdt if x["sym"] == "BTCUSDT"), None)
eth = next((x for x in usdt if x["sym"] == "ETHUSDT"), None)
if btc:
    print(f"BTCUSDT {btc['price']:.2f}  24h {btc['chg']:+.2f}%  vol_share {btc['vol']/tot*100:.1f}%")
if eth:
    print(f"ETHUSDT {eth['price']:.2f}  24h {eth['chg']:+.2f}%  vol_share {eth['vol']/tot*100:.1f}%")
print(f"TOTAL 24H QUOTE VOL (all USDT perps): {tot/1e9:.1f}B USDT")

byvol = sorted(usdt, key=lambda x: -x["vol"])[:30]
print("\n=== TOP 30 BY 24H VOLUME ===")
print(f"{'SYMBOL':<14}{'PRICE':>14}{'24H%':>9}{'VOL(B)':>9}")
for x in byvol:
    print(f"{x['sym']:<14}{x['price']:>14.4f}{x['chg']:>8.2f}%{x['vol']/1e9:>9.2f}")

gainers = sorted(usdt, key=lambda x: -x["chg"])[:15]
losers = sorted(usdt, key=lambda x: x["chg"])[:15]
print("\n=== TOP 15 GAINERS (24h, ALL PAIRS) ===")
for x in gainers:
    print(f"{x['sym']:<16}{x['chg']:>8.2f}%  p={x['price']:.6g}  vol={x['vol']/1e6:.1f}M")
print("\n=== TOP 15 LOSERS (24h, ALL PAIRS) ===")
for x in losers:
    print(f"{x['sym']:<16}{x['chg']:>8.2f}%  p={x['price']:.6g}  vol={x['vol']/1e6:.1f}M")

# funding + OI for the movers/leaders
watch = list(dict.fromkeys([x["sym"] for x in byvol[:15] + gainers[:8] + losers[:8]]))
print("\n=== FUNDING + OI (live) ===")
print(f"{'SYMBOL':<14}{'FUNDING%':>10}{'MARK':>14}{'OI(USD M)':>12}")
oi_map = {}
for s in watch:
    try:
        o = get(BASE + f"/fapi/v1/openInterest?symbol={s}")
        pm = float(next((t["lastPrice"] for t in tickers if t["symbol"] == s), 0))
        oi_map[s] = float(o["openInterest"]) * pm
    except Exception:
        pass
for s in watch:
    try:
        p = get(BASE + f"/fapi/v1/premiumIndex?symbol={s}")
        fund = float(p["lastFundingRate"]) * 100
        mark = float(p["markPrice"])
        oiv = oi_map.get(s, 0) / 1e6
        print(f"{s:<14}{fund:>9.4f}%{mark:>14.4f}{oiv:>12.1f}")
    except Exception as e:
        print(s, "ERR", e)

# long/short crowding on majors
print("\n=== LONG/SHORT ACCOUNT RATIO (top traders, 1h) ===")
for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]:
    try:
        d = get(BASE + f"/futures/data/topLongShortAccountRatio?symbol={s}&period=1h&limit=1")
        if d:
            r = d[-1]
            print(f"{s:<10} L/S={r['longShortRatio']}  long={float(r['longAccount'])*100:.1f}% short={float(r['shortAccount'])*100:.1f}%")
    except Exception as e:
        print(s, "ERR", e)
