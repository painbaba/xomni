#!/usr/bin/env python3
"""Line-based parser for DENSE unclaimed-register PDFs (LIC dividend registers,
multi-hundred-page, records span many text lines). Use when pymupdf
find_tables() is too slow or breaks on the layout.

Record shape (LIC dividend register 2025 format):
  SNo line (short int alone) opens a record
  then ~12 lines: folio (14-17 digits) | pincode (6 digits) | warrant (8 digits)
  | amount (\\d+[.,]\\d{2}) | due date | name (first non-classified line) | address...

Usage: python lic_parse.py <input.pdf> <output.csv>
"""
import fitz, re, csv, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", s).strip()

def parse_register(path, out_csv):
    doc = fitz.open(path)
    recs = []
    for page in doc:
        lines = [norm(l) for l in page.get_text().splitlines() if l.strip()]
        i, n = 0, len(lines)
        while i < n:
            l = lines[i]
            if re.match(r"^\d{1,7}$", l):          # SNo record opener
                sno = l
                k = i + 1
                folio = name = pincode = warrant = shares = amount = due = ""
                addr = []
                while k < n and k < i + 13:
                    seg = lines[k]
                    if re.match(r"^\d{1,7}$", seg) and k > i + 1:
                        break                        # next record
                    if not folio and re.match(r"^\d{14,17}$", seg):
                        folio = seg; k += 1; continue
                    if not pincode and re.match(r"^\d{6}$", seg):
                        pincode = seg; k += 1; continue
                    if not amount and re.match(r"^[\d,]+\.\d{2}$", seg):
                        amount = seg.replace(",", ""); k += 1; continue
                    if not warrant and re.match(r"^\d{8}$", seg):
                        warrant = seg; k += 1; continue
                    if not shares and re.match(r"^\d{1,5}$", seg) and not re.match(r"^\d{6}$", seg):
                        shares = seg; k += 1; continue
                    if not due and re.match(r"^\d{2}[./-]\d{2}[./-]\d{4}$", seg):
                        due = seg; k += 1; continue
                    if not name:
                        name = seg
                    else:
                        addr.append(seg)
                    k += 1
                recs.append({"sno": sno, "folio": folio, "name": name,
                             "address": " | ".join(addr), "pincode": pincode,
                             "warrant": warrant, "shares": shares,
                             "amount": amount, "due": due})
                i = k
            else:
                i += 1
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sno", "folio", "name", "address",
                                          "pincode", "warrant", "shares", "amount", "due"])
        w.writeheader(); w.writerows(recs)
    amt = sum(float(r["amount"]) for r in recs if r["amount"])
    print(f"{len(recs)} records | with amount: {sum(1 for r in recs if r['amount'])} | total: {amt:,.2f}")

if __name__ == "__main__":
    parse_register(sys.argv[1], sys.argv[2])
