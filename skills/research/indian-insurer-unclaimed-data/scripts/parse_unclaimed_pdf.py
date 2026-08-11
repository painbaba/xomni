#!/usr/bin/env python3
"""Robustly extract records from unclaimed-amounts table PDFs.

Why not a naive line split: in IndiaFirst-style unclaimed PDFs the table layout is
    Sl No / Policy id / Name / Amount / Due date
and small amounts (3, 6, 100...) are pure integers, indistinguishable from Sl No
values. The reliable row-start signal is:
    a small integer line IMMEDIATELY followed by a 6-9 digit policy-id line.

Usage:
    python parse_unclaimed_pdf.py <file.pdf> [out.csv]

Writes CSV with columns slno, policy_id, name, amount, due_date and prints the
record count, max Sl No, and first few rows. Requires pymupdf (`pip install pymupdf`).
"""
import re
import sys
import csv

try:
    import pymupdf  # preferred; fall back to deprecated fitz name
except ImportError:
    import fitz as pymupdf

ROW_START = re.compile(r'^\d{1,4}$')          # Sl No
POLICY_ID = re.compile(r'^\d{6,9}$')          # 6-9 digit policy / member id


def parse(pdf_path):
    doc = pymupdf.open(pdf_path)
    recs = []
    for page in doc:
        lines = [l.strip() for l in page.get_text("text").splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            if (ROW_START.match(lines[i]) and i + 1 < len(lines)
                    and POLICY_ID.match(lines[i + 1])):
                slno, pid = lines[i], lines[i + 1]
                j = i + 2
                fields = []
                while j < len(lines) and not (ROW_START.match(lines[j])
                                              and j + 1 < len(lines)
                                              and POLICY_ID.match(lines[j + 1])):
                    fields.append(lines[j])
                    j += 1
                recs.append([slno, pid] + fields)
                i = j
            else:
                i += 1
    return recs, doc.page_count


if __name__ == "__main__":
    pdf_path = sys.argv[1]
    out_csv = sys.argv[2] if len(sys.argv) > 2 else "unclaimed_records.csv"
    recs, pages = parse(pdf_path)
    print(f"pages: {pages}, records: {len(recs)}")
    sl = [int(r[0]) for r in recs if r[0].isdigit()]
    if sl:
        print(f"max Sl No: {max(sl)}")
    for r in recs[:5]:
        print(r)
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slno", "policy_id", "name", "amount", "due_date"])
        for r in recs:
            if len(r) >= 5:
                w.writerow([r[0], r[1], " ".join(r[2:-2]), r[-2], r[-1]])
            else:
                w.writerow(r + [""] * (5 - len(r)))
    print("CSV ->", out_csv)
