#!/usr/bin/env python3
"""Verify direct-download URLs for media sourcing: HEAD check (status, size, type),
optionally probe duration by downloading + ffprobe.

Usage:
  python verify_direct_urls.py URL [URL ...]          # check listed URLs
  python verify_direct_urls.py < urls.txt             # read URLs from stdin
  python verify_direct_urls.py --duration URL ...     # also download + ffprobe duration
  python verify_direct_urls.py --duration-max 5000000 # skip duration probe for files > N bytes

Exits 0 if all URLs returned 2xx, 1 otherwise. Stdlib only.
"""
import sys, os, re, subprocess, tempfile, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) media-sourcing-verify'}

def head(url, timeout=30):
    req = urllib.request.Request(url, method='HEAD', headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Length'), r.headers.get('Content-Type')
    except Exception as e:
        return getattr(e, 'code', 'ERR'), str(e)[:60], None

def duration(url, timeout=120, max_bytes=15_000_000):
    """Download to temp file and probe with ffprobe; returns 'Ns' or '?'."""
    if not shutil_which('ffprobe'):
        return '?'
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(max_bytes + 1)
        if len(data) > max_bytes:
            return '?'
        fd, fn = tempfile.mkstemp(suffix='.mp3')
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', fn],
            capture_output=True, text=True).stdout.strip()
        os.unlink(fn)
        return f"{float(out):.0f}s" if out else '?'
    except Exception:
        return '?'

def shutil_which(name):
    from shutil import which
    return which(name)

def main():
    args = sys.argv[1:]
    want_dur = '--duration' in args
    max_bytes = 15_000_000
    if '--duration-max' in args:
        i = args.index('--duration-max')
        max_bytes = int(args[i + 1]); del args[i:i + 2]
    args = [a for a in args if not a.startswith('--')]
    urls = args if args else [l.strip() for l in sys.stdin if l.strip()]
    if not urls:
        print("no URLs given"); return 2
    bad = 0
    for u in urls:
        st, cl, ct = head(u)
        dur = ''
        if want_dur and st == 200 and cl and int(cl) <= max_bytes:
            dur = ' ' + duration(u, max_bytes=max_bytes)
        ok = isinstance(st, int) and 200 <= st < 300
        if not ok:
            bad += 1
        print(f"{'OK ' if ok else 'BAD'} {st}  {str(cl or '-'):>11}  {ct or '-':18s}{dur} {u}")
    print(f"\n{len(urls) - bad}/{len(urls)} verified")
    return 0 if bad == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
