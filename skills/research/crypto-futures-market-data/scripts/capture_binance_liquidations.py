#!/usr/bin/env python3
"""Live Binance liquidation capture with built-in connectivity control.

Verified Aug 2026. The REST liquidation endpoint (allForceOrders) is gone (404),
so the WS !forceOrder@arr stream is the only public liquidation feed.

Critical: a "0 events" result is ONLY meaningful if the stream is provably live.
This script therefore also counts btcusdt@aggTrade as a control — a live stream
shows hundreds of trades in seconds. If control == 0, the connection is
blocked/blackholed and the forceOrder count is garbage.

Auto-fallback: tries fstream.binance.com first, then data-stream.binance.vision
(public mirror; the latter is the one that worked from a host where fstream
silently blackholed all traffic).

Usage:  python capture_binance_liquidations.py [seconds]   (default 100)
Requires: pip install websockets
"""
import asyncio
import json
import sys
import time
import datetime

HOSTS = [
    "wss://fstream.binance.com/ws/btcusdt@aggTrade/!forceOrder@arr",
    "wss://data-stream.binance.vision/ws/btcusdt@aggTrade/!forceOrder@arr",
]

async def capture(url, duration):
    agg = {}
    n = 0
    control = 0
    try:
        import websockets
        async with websockets.connect(url, ping_interval=15, open_timeout=10) as ws:
            while time.time() - time.monotonic() < duration:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=12))
                except asyncio.TimeoutError:
                    continue
                if msg.get("e") == "aggTrade":
                    control += 1
                    continue
                o = msg.get("o", {})
                sym = o.get("s", "?")
                side = o.get("S", "?")
                qty = abs(float(o.get("q", 0)))
                price = float(o.get("ap", 0))
                notional = qty * price
                n += 1
                ev = agg.setdefault(sym, {"count": 0, "notional": 0.0, "long_liq": 0.0,
                                          "short_liq": 0.0, "biggest": 0.0, "last": 0})
                ev["count"] += 1
                ev["notional"] += notional
                if side == "SELL":
                    ev["long_liq"] += notional  # SELL = liquidated LONG
                elif side == "BUY":
                    ev["short_liq"] += notional  # BUY = liquidated SHORT
                ev["biggest"] = max(ev["biggest"], notional)
                ev["last"] = msg.get("E", 0)
    except Exception as e:
        return None, f"CONN ERR: {e}"
    return (control, n, agg), None

async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for host in HOSTS:
        print(f"trying {host} ...")
        res, err = await capture(host, duration)
        if err:
            print("  ", err)
            continue
        control, n, agg = res
        print(f"WINDOW {now} UTC, {duration}s | control aggTrades={control} | forceOrders={n}")
        if control == 0:
            print("!! CONTROL == 0 -> stream NOT delivering data (blocked). Trying next host...")
            continue
        if n == 0:
            print("Verified-live stream, ZERO liquidation events -> genuinely quiet tape.")
        for sym, v in sorted(agg.items(), key=lambda kv: -kv[1]["notional"])[:15]:
            last = datetime.datetime.fromtimestamp(v["last"] / 1000, datetime.timezone.utc).strftime("%H:%M:%S") if v["last"] else "-"
            print(f"{sym:<14} n={v['count']:<3} ${v['notional']:>10,.0f} "
                  f"long-liq=${v['long_liq']:>9,.0f} short-liq=${v['short_liq']:>9,.0f} "
                  f"biggest=${v['biggest']:>9,.0f} last={last}")
        return
    print("ALL HOSTS FAILED - no usable liquidation stream.")

asyncio.run(main())
