#!/usr/bin/env python3
"""Live Binance liquidation tap.

Connects to Binance's PUBLIC force-order WebSocket stream and prints
liquidation events. Works even where the REST endpoints
(/futures/data/allForceOrders, /futures/data/forceOrders) are geo-blocked
(HTTP 404 via CloudFront).

Usage:
    pip install websockets
    python binance_forceorder_ws.py            # all symbols, 40s window
    python binance_forceorder_ws.py BTCUSDT ETHUSDT SOLUSDT   # filtered, 50s

Interpreting output:
  - Events print as JSON: sym, side (SELL=liquidated long, BUY=liquidated
    short), px, usd notional, time (epoch ms).
  - Zero prints in ~40s across ALL symbols = no cascade running right now.
    Report that explicitly ("no liquidation activity observed live").
  - Note: this stream carries Binance-only liquidations; Coinglass
    aggregates all exchanges (totals differ ~2-5x).
"""
import asyncio
import json
import sys
import time

import websockets

URI = "wss://fstream.binance.com/ws/!forceOrder@arr"
WINDOW_SECONDS = 50
MAX_PRINTS = 30


async def main() -> None:
    wanted = set(sys.argv[1:]) or None  # None = all symbols
    try:
        async with websockets.connect(URI, ping_interval=20, open_timeout=15) as ws:
            print("CONNECTED", flush=True)
            end = time.time() + WINDOW_SECONDS
            n = 0
            while time.time() < end:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    continue
                d = json.loads(msg)
                o = d.get("o", {})
                sym = o.get("s")
                if wanted and sym not in wanted:
                    continue
                usd = round(float(o.get("q", 0)) * float(o.get("p", 0)))
                print(json.dumps({
                    "sym": sym,
                    "side": o.get("S"),          # SELL => long liquidated, BUY => short liquidated
                    "px": o.get("p"),
                    "usd": usd,
                    "t": d.get("E"),
                }), flush=True)
                n += 1
                if n >= MAX_PRINTS:
                    break
            print(f"DONE total={n} window={WINDOW_SECONDS}s symbols={'all' if wanted is None else ','.join(sys.argv[1:])}", flush=True)
    except Exception as e:  # noqa: BLE001 - report any failure loudly
        print("ERR:", type(e).__name__, str(e)[:200], flush=True)


if __name__ == "__main__":
    asyncio.run(main())
