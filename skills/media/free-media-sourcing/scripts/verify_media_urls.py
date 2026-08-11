#!/usr/bin/env python3
"""Verify direct media URLs on throttled hosts (Wikimedia upload, Pexels, Pixabay).

HEAD first; if HEAD fails (429/403/405/ERR), retry with a ranged GET (bytes=0-2047):
206 + media Content-Type = downloadable. Optional per-URL sleep to ride out
burst-rate throttles (upload.wikimedia.org 429s burst HEADs; clear in ~1-4 min).

Usage:
  python verify_media_urls.py URL [URL ...]
  python verify_media_urls.py --sleep 10 < urls.txt
  python verify_media_urls.py --no-range URL ...   # skip ranged-GET fallback

Exits 0 if all URLs verified (2xx/206), 1 otherwise. Stdlib only.
"""
import sys, time, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) media-sourcing-verify'}


def request(url, method, extra_headers=None):
    headers = dict(UA)
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.headers.get('Content-Length'), r.headers.get('Content-Type')


def check(url, use_range=True):
    try:
        st, cl, ct = request(url, 'HEAD')
        if 200 <= st < 300:
            return st, cl, ct, 'HEAD'
    except Exception:
        pass
    if use_range:
        try:
            st, cl, ct = request(url, 'GET', {'Range': 'bytes=0-2047'})
            if st in (200, 206):
                return st, cl, ct, 'RANGE'
        except Exception:
            pass
    # last resort: full GET headers only (stream to /dev/null is caller's choice)
    return ('ERR', None, None, '-')


def main():
    args = sys.argv[1:]
    sleep_s = 0
    if '--sleep' in args:
        i = args.index('--sleep')
        sleep_s = int(args[i + 1])
        del args[i:i + 2]
    use_range = '--no-range' not in args
    args = [a for a in args if not a.startswith('--')]
    urls = args if args else [l.strip() for l in sys.stdin if l.strip()]
    if not urls:
        print('no URLs given')
        return 2
    bad = 0
    for u in urls:
        st, cl, ct, via = check(u, use_range)
        ok = isinstance(st, int) and 200 <= st < 300
        if not ok:
            bad += 1
        print(f"{'OK ' if ok else 'BAD'} {str(st):<4} {via:<5} {str(cl or '-'):>11}  {ct or '-':<25} {u}")
        if sleep_s:
            time.sleep(sleep_s)
    print(f'\n{len(urls) - bad}/{len(urls)} verified')
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
