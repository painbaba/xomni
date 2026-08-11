#!/usr/bin/env python3
"""Batch-probe insurer unclaimed-amount pages for downloadable list links.

Usage:
    python probe_insurers.py urls.txt [out.json]

urls.txt: one "label|https://..." per line. Output JSON (default probe_results.json)
contains per-insurer: final URL, content-type, size, and deduped links matching
pdf/xls/csv/zip/download/unclaimed/disclos. Prints one status line per insurer.

The full 2026-08 URL set is embedded in INSURER_URLS below — a fresh sweep can
either edit that dict or pass a file.
"""
import urllib.request, urllib.error, re, json, sys, ssl

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

INSURER_URLS = {
    # Life
    "absli_life": "https://lifeinsuranceservicing.adityabirlacapital.com/pre-unclaim",
    "ageas_federal": "https://www.ageasfederal.com/unclaimed-payouts",
    "aviva": "https://online.avivaindia.com/econnect/Pages/IRDA_Claims.aspx",
    "axis_max_life": "https://www.maxlifeinsurance.com/cs/unclaimed-amount",
    "canara_hsbc": "https://www.canarahsbclife.com/customer-service/claims/unclaimed-amount",
    "edelweiss": "https://www.edelweisslife.in/unclaimedamount",
    "indiafirst": "https://www.indiafirstlife.com/unclaimed-amount",
    "indusind_nippon": "https://www.indusindnipponlife.com/unclaimed-amount-of-policy-holders",
    "kotak_life": "https://customer.kotaklifeinsurance.com/CP/customerunclaimamount.aspx",
    "pnb_metlife": "https://customerportal.pnbmetlife.com/unclaimed/amount/",
    "pramerica": "https://pramericalife.in/unclaimed-amount",
    "tata_aia": "https://myinsurance.tataaia.com/portfolio/policy/unclaimed-funds/authenticate",
    # General
    "chola_ms": "https://www.cholainsurance.com/unclaimed-amount",
    "godigit": "https://www.godigit.com/claim/check-unclaimed-amount",
    "icici_lombard": "https://ilhc.icicilombard.com/Home/UnclaimedAmount",
    "iffco_tokio": "https://www.iffcotokio.co.in/claims/unclaimed-amount-policy-holders",
    "kshema": "https://kshema.co/unclaimed-amount/",
    "magma": "https://www.magmainsurance.com/unclaimed-amount",
    "navi": "https://navi.com/insurance/unclaimed-claims",
    "indusind_gi": "https://www.indusindinsurance.com/Insurance/About-Us/Unclaimed-Amount.aspx",
    "universal_sompo": "https://www.universalsompo.com/public-disclosure",
    "zuno": "https://www.hizuno.com/unclaimed-amount",
    # Health
    "manipal_cigna": "https://www.manipalcigna.com/disclosures/unclaimed-amount",
    "niva_bupa": "https://transactions.nivabupa.com/unclaimed/unclaimedamount.aspx",
}

LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
FILE_RE = re.compile(r'(pdf|xlsx?|csv|zip|download|unclaimed|disclos)', re.I)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read(), r.geturl(), r.headers.get("Content-Type", "")
    except Exception as e:
        return None, str(e), ""


def probe(urls):
    results = {}
    for name, url in urls.items():
        data, final, ctype = fetch(url)
        if data is None:
            results[name] = {"url": url, "error": final[:200]}
            print(f"[ERR] {name}: {final[:120]}", flush=True)
            continue
        text = data.decode("utf-8", errors="ignore")
        links, seen = [], set()
        for m in LINK_RE.finditer(text):
            href = m.group(1)
            if FILE_RE.search(href) and href not in seen:
                seen.add(href)
                links.append(href)
        results[name] = {"url": url, "final": final, "ctype": ctype,
                         "size": len(data), "links": links[:25], "n_links": len(links)}
        print(f"[OK] {name}: {len(data)} bytes, {len(links)} file-ish links, ctype={ctype}", flush=True)
    return results


if __name__ == "__main__":
    urls = dict(INSURER_URLS)
    if len(sys.argv) > 1:
        urls = {}
        for line in open(sys.argv[1], encoding="utf-8"):
            line = line.strip()
            if "|" in line:
                label, u = line.split("|", 1)
                urls[label.strip()] = u.strip()
    out = sys.argv[2] if len(sys.argv) > 2 else "probe_results.json"
    with open(out, "w") as f:
        json.dump(probe(urls), f, indent=1)
    print("DONE ->", out)
