#!/usr/bin/env python3
"""Compute technical metrics from Yahoo Finance chart API JSON (validated in production, Aug 2026).

Usage: python yahoo_tech_analysis.py <daily.json> [weekly.json]
  daily.json  = output of https://query1.finance.yahoo.com/v8/finance/chart/SYM?interval=1d&range=2y
  weekly.json = optional, interval=1wk (adds weekly RSI/SMA/swings)

Prints: meta snapshot, returns 1D..1Y (with base dates), SMA/EMA 20/50/100/200 + price
position, MA cross dates, Wilder RSI(14), MACD(12,26,9), ATR(14), volume averages,
52w/ATH extremes, daily + weekly swing highs/lows (fractal k=2), gap scan (>0.5%),
month-end closes. Dates are converted to IST (UTC+5:30).
"""
import json, sys, datetime

def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def series(j):
    r = j['chart']['result'][0]
    ts = r['timestamp']
    q = r['indicators']['quote'][0]
    rows = []
    for i, t in enumerate(ts):
        o, h, l, c, v = q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]
        if c is None:
            continue
        d = datetime.datetime.utcfromtimestamp(t) + datetime.timedelta(hours=5, minutes=30)
        rows.append({'date': d.strftime('%Y-%m-%d'), 'o': o, 'h': h, 'l': l, 'c': c, 'v': v or 0})
    return rows, r['meta']

def sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None

def sma_series(vals, n):
    out, s = [], 0.0
    for i, v in enumerate(vals):
        s += v
        if i >= n:
            s -= vals[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out

def ema_series(vals, n):
    k = 2 / (n + 1); e = vals[0]; out = [e]
    for v in vals[1:]:
        e = v * k + e * (1 - k); out.append(e)
    return out

def rsi_series(closes, n=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0)); losses.append(max(-d, 0.0))
    if len(gains) < n:
        return [None] * len(closes)
    ag = sum(gains[:n]) / n; al = sum(losses[:n]) / n
    out = [None] * n
    for i in range(n, len(closes)):
        ag = (ag * (n - 1) + gains[i - 1]) / n
        al = (al * (n - 1) + losses[i - 1]) / n
        out.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    return out

def macd_series(closes, f=12, s=26, sig=9):
    ef, es = ema_series(closes, f), ema_series(closes, s)
    macd = [a - b for a, b in zip(ef, es)]
    sigl = ema_series(macd, sig)
    return macd, sigl, [m - x for m, x in zip(macd, sigl)]

def atr(rows, n=14):
    trs = []
    for i in range(1, len(rows)):
        r, p = rows[i], rows[i - 1]
        trs.append(max(r['h'] - r['l'], abs(r['h'] - p['c']), abs(r['l'] - p['c'])))
    return sum(trs[-n:]) / n if len(trs) >= n else None

def swings(rows, k=2):
    sh, sl = [], []
    for i in range(k, len(rows) - k):
        if rows[i]['h'] > max(rows[j]['h'] for j in range(i - k, i)) and \
           rows[i]['h'] > max(rows[j]['h'] for j in range(i + 1, i + k + 1)):
            sh.append((rows[i]['date'], round(rows[i]['h'], 2)))
        if rows[i]['l'] < min(rows[j]['l'] for j in range(i - k, i)) and \
           rows[i]['l'] < min(rows[j]['l'] for j in range(i + 1, i + k + 1)):
            sl.append((rows[i]['date'], round(rows[i]['l'], 2)))
    return sh, sl

def pct(a, b):
    return (a / b - 1) * 100

def analyze_daily(daily, meta):
    last, prev = daily[-1], daily[-2]
    print(f"meta: price {meta.get('regularMarketPrice')} | 52wH {meta.get('fiftyTwoWeekHigh')} "
          f"52wL {meta.get('fiftyTwoWeekLow')} | day H {meta.get('regularMarketDayHigh')} "
          f"L {meta.get('regularMarketDayLow')} V {meta.get('regularMarketVolume')}")
    print(f"last bar: {last['date']} O{last['o']:.2f} H{last['h']:.2f} L{last['l']:.2f} "
          f"C{last['c']:.2f} V{last['v']:,}  (prev {prev['date']} C{prev['c']:.2f})")
    closes = [r['c'] for r in daily]
    print("\nreturns:")
    for label, n in [('1D', 1), ('1W', 5), ('1M', 21), ('3M', 63), ('6M', 126), ('1Y', 252)]:
        if len(daily) > n:
            print(f"  {label}: {pct(last['c'], daily[-1 - n]['c']):+.2f}%  "
                  f"(vs {daily[-1 - n]['c']:.2f} on {daily[-1 - n]['date']})")
    print("\nSMAs / EMAs:")
    for n in [20, 50, 100, 200]:
        m = sma(closes, n)
        if m:
            print(f"  SMA{n}: {m:.2f}  (price {'ABOVE' if last['c'] > m else 'BELOW'} {(last['c'] / m - 1) * 100:+.1f}%)")
    e20, e50 = ema_series(closes, 20), ema_series(closes, 50)
    print(f"  EMA20 {e20[-1]:.2f} | EMA50 {e50[-1]:.2f}")
    ma20s, ma50s = sma_series(closes, 20), sma_series(closes, 50)
    for a, b, name in [(ma20s, ma50s, '20/50'), (ma50s, sma_series(closes, 200), '50/200')]:
        for i in range(len(a) - 1, 0, -1):
            if a[i] is not None and b[i] is not None and a[i - 1] is not None and b[i - 1] is not None \
               and (a[i] > b[i]) != (a[i - 1] > b[i - 1]):
                print(f"  {name} last cross: {daily[i]['date']} "
                      f"({'above' if a[i] > b[i] else 'below'})")
                break
    rsi = rsi_series(closes)
    print(f"RSI(14): {rsi[-1]:.1f}" if rsi[-1] else "RSI: N/A")
    macd, sigl, hist = macd_series(closes)
    print(f"MACD {macd[-1]:.3f} | signal {sigl[-1]:.3f} | hist {hist[-1]:.3f}")
    print(f"ATR(14): {atr(daily):.2f} ({(atr(daily) / last['c']) * 100:.1f}% of price)")
    vols = [r['v'] for r in daily]
    print(f"avg vol: 20d {sum(vols[-20:]) / 20:,.0f} | 50d {sum(vols[-50:]) / 50:,.0f} | "
          f"3M {sum(vols[-63:]) / 63:,.0f} | 6M {sum(vols[-126:]) / 126:,.0f}")
    ony = daily[-252:] if len(daily) >= 252 else daily
    hi, lo = max(ony, key=lambda r: r['h']), min(ony, key=lambda r: r['l'])
    print(f"52w window ({ony[0]['date']}): high {hi['h']:.2f} ({hi['date']}) low {lo['l']:.2f} ({lo['date']})")
    sh, sl = swings(daily[-120:])
    print(f"swing highs (120 bars): {sh[-10:]}")
    print(f"swing lows  (120 bars): {sl[-10:]}")
    print("\ngaps (>0.5%):")
    for i in range(1, len(daily)):
        r, p = daily[i], daily[i - 1]
        g = (r['l'] - p['h']) / p['h'] * 100
        if g > 0.5:
            print(f"  UP  {r['date']}: {p['h']:.2f}->{r['l']:.2f} +{g:.1f}%")
        gd = (r['h'] - p['l']) / p['l'] * 100
        if gd < -0.5:
            print(f"  DOWN {r['date']}: {p['l']:.2f}->{r['h']:.2f} {gd:.1f}%")
    months = {}
    for r in daily:
        months.setdefault(r['date'][:7], []).append(r['c'])
    print("\nmonth-end closes:")
    prevc = None
    for m in sorted(months):
        c = months[m][-1]
        print(f"  {m}: {c:.2f} ({pct(c, prevc):+.1f}%)" if prevc else f"  {m}: {c:.2f}")
        prevc = c

if __name__ == '__main__':
    daily, meta = series(load(sys.argv[1]))
    analyze_daily(daily, meta)
    if len(sys.argv) > 2:
        wk, _ = series(load(sys.argv[2]))
        wc = [r['c'] for r in wk]
        print(f"\nWEEKLY: {len(wk)} bars {wk[0]['date']}->{wk[-1]['date']}")
        print(f"  SMA10 {sma(wc, 10):.2f} | SMA20 {sma(wc, 20):.2f} | SMA50 {sma(wc, 50):.2f} | RSI(14) {rsi_series(wc)[-1]:.1f}")
        print(f"  swing highs: {swings(wk)[0][-6:]}")
        print(f"  swing lows : {swings(wk)[1][-6:]}")
