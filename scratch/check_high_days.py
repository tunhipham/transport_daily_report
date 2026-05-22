# -*- coding: utf-8 -*-
"""Analyze days with 80T+ in May 2026 — breakdown by vendor"""
import sys, os, json, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'g:\My Drive\DOCS\transport_daily_report\script')
from data_pipeline.config import load_clickhouse_config
import requests

cfg = load_clickhouse_config()
p = {'user': cfg['user'], 'password': cfg['password'], 'database': cfg['database']}
def q(sql):
    r = requests.get(cfg['base_url'], params={**p, 'query': sql}, timeout=120)
    r.raise_for_status()
    return r.text.strip()

KRC = '5fdc170ebd89c10006f15b7c'

# Load master data
from lib.sources import MASTER_SHEET_URL
from io import BytesIO
from openpyxl import load_workbook as lw
r_m = requests.get(MASTER_SHEET_URL, allow_redirects=True, timeout=120)
r_m.raise_for_status()
wb = lw(BytesIO(r_m.content), read_only=True, data_only=True)
ws = wb.worksheets[0]
master = {}
for row in ws.iter_rows(min_row=2, values_only=False):
    bc = str(row[0].value or "").strip()
    if not bc: continue
    tl = row[25].value
    if tl is not None:
        try:
            w = float(tl)
            if w > 0: master[bc] = w
        except: pass
wb.close()
print(f"Master: {len(master)} barcodes\n")

# Step 1: Get daily totals for May 2026
print("=" * 70)
print("  T5/2026: Daily tonnage (delivery_date_vendor_confirm + po_qty)")
print("=" * 70)

r1 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') AS del_date,
    ri.product_barcode AS barcode,
    ri.product_name AS pname,
    ri.po_qty AS qty,
    ri.net_weight AS net_weight,
    po.code AS po_code,
    ri.vendor_id AS vendor_id
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC}'
  AND fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)) >= '2026-05-01'
  AND fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)) < '2026-06-01'
FORMAT JSONEachRow
""")

def resolve_weight(nw, bc, pname):
    if nw > 0: return nw, 'db'
    if bc and bc in master: return master[bc], 'master'
    text = (pname or '').upper()
    for pat, mult in [(r'(\d+(?:[.,]\d+)?)\s*KG\b',1000),(r'(\d+(?:[.,]\d+)?)\s*G\b',1)]:
        m = re.findall(pat, text)
        if m:
            try: return float(m[-1].replace(",","."))*mult, 'name'
            except: pass
    return 0, 'none'

# Parse all rows
rows_by_date = defaultdict(list)
daily_tons = defaultdict(float)

for line in r1.split('\n'):
    if not line.strip(): continue
    obj = json.loads(line)
    d = obj.get('del_date','')
    qty = float(obj.get('qty',0))
    nw = float(obj.get('net_weight',0))
    bc = str(obj.get('barcode','')).strip()
    pname = str(obj.get('pname','')).strip()
    vendor = str(obj.get('vendor_id','')).strip()
    po = str(obj.get('po_code','')).strip()
    
    if not d or qty <= 0: continue
    wg, src = resolve_weight(nw, bc, pname)
    if wg <= 0: continue
    
    tons = qty * wg / 1_000_000
    daily_tons[d] += tons
    rows_by_date[d].append({'bc': bc, 'pname': pname, 'qty': qty, 'wg': wg, 'tons': tons, 'vendor': vendor, 'po': po, 'src': src})

# Print daily totals
sorted_dates = sorted(daily_tons.keys(), key=lambda d: d.split('/')[::-1])
high_days = []
print(f"\n  {'Date':<12} {'Tons':>8} {'Flag':>6}")
print(f"  {'─'*12} {'─'*8} {'─'*6}")
for d in sorted_dates:
    t = daily_tons[d]
    flag = '⚠ HIGH' if t >= 80 else ''
    print(f"  {d:<12} {t:>8.2f} {flag}")
    if t >= 80:
        high_days.append(d)

# Step 2: Breakdown of high days
for d in high_days:
    items = rows_by_date[d]
    print(f"\n{'='*70}")
    print(f"  ⚠ {d}: {daily_tons[d]:.2f} tấn — BREAKDOWN")
    print(f"{'='*70}")
    
    # By vendor
    vendor_tons = defaultdict(float)
    vendor_rows = defaultdict(int)
    vendor_pos = defaultdict(set)
    for item in items:
        vendor_tons[item['vendor']] += item['tons']
        vendor_rows[item['vendor']] += 1
        vendor_pos[item['vendor']].add(item['po'])
    
    print(f"\n  By Vendor (top 10):")
    print(f"  {'Vendor':<30} {'Tons':>8} {'POs':>5} {'Rows':>5}")
    print(f"  {'─'*30} {'─'*8} {'─'*5} {'─'*5}")
    for v in sorted(vendor_tons, key=vendor_tons.get, reverse=True)[:10]:
        print(f"  {v:<30} {vendor_tons[v]:>8.2f} {len(vendor_pos[v]):>5} {vendor_rows[v]:>5}")
    
    # Top items by tonnage
    items_sorted = sorted(items, key=lambda x: x['tons'], reverse=True)
    print(f"\n  Top 15 items by tonnage:")
    print(f"  {'Barcode':<15} {'Qty':>8} {'Wt(g)':>8} {'Tons':>8} {'Src':>6}  Product")
    print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*8} {'─'*6}  {'─'*30}")
    for item in items_sorted[:15]:
        print(f"  {item['bc']:<15} {item['qty']:>8.0f} {item['wg']:>8.1f} {item['tons']:>8.3f} {item['src']:>6}  {item['pname'][:40]}")
    
    # Weight source distribution
    src_tons = defaultdict(float)
    src_count = defaultdict(int)
    for item in items:
        src_tons[item['src']] += item['tons']
        src_count[item['src']] += 1
    print(f"\n  Weight source distribution:")
    for src in sorted(src_tons, key=src_tons.get, reverse=True):
        print(f"    {src:>8}: {src_tons[src]:>8.2f}T ({src_count[src]} rows)")

    # Check for duplicate PO items
    seen = defaultdict(float)
    for item in items:
        key = f"{item['po']}|{item['bc']}"
        seen[key] += item['tons']
    dupes = {k: v for k, v in seen.items() if '|' in k}
    po_bc_count = defaultdict(int)
    for item in items:
        key = f"{item['po']}|{item['bc']}"
        po_bc_count[key] += 1
    real_dupes = {k: v for k, v in po_bc_count.items() if v > 1}
    if real_dupes:
        print(f"\n  ⚠ Duplicate PO+Barcode combos: {len(real_dupes)}")
        for k in list(real_dupes.keys())[:5]:
            po, bc = k.split('|')
            print(f"    {po} + {bc}: {real_dupes[k]} times = {seen[k]:.3f}T")

print("\nDone.")
