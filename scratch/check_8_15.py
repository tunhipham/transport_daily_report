# -*- coding: utf-8 -*-
"""Check EXACT data for 08/05 and 15/05 using same query as capacity_forecast"""
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

# Load master
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

def resolve_wt(nw, bc):
    if nw > 0: return nw
    if bc and bc in master: return master[bc]
    return 0

# Use EXACT same query as capacity_forecast.py but filter for target dates
for target in ['08/05/2026', '15/05/2026']:
    r1 = q(f"""
    SELECT
        formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') AS del_date,
        ri.purchase_code AS po_code,
        ri.product_barcode AS barcode,
        any(ri.product_name) AS pname,
        any(ri.po_qty) AS po_qty,
        any(ri.qty) AS qty,
        any(ri.qty_receipt) AS qty_rcpt,
        any(ri.net_weight) AS net_weight
    FROM kf_receipt_items ri
    INNER JOIN kf_purchase_order po
        ON ri.purchase_code = po.code
        AND po.branch_id = '{KRC}' AND po.deleted = 0
    WHERE ri.branch_id = '{KRC}'
    GROUP BY del_date, ri.purchase_code, ri.product_barcode
    HAVING del_date = '{target}'
    FORMAT JSONEachRow
    """)
    
    total_tons = 0
    items = []
    po_set = set()
    
    for line in r1.split('\n'):
        if not line.strip(): continue
        obj = json.loads(line)
        po_qty = float(obj.get('po_qty', 0))
        qty = float(obj.get('qty', 0))
        qr = float(obj.get('qty_rcpt', 0))
        nw = float(obj.get('net_weight', 0))
        bc = str(obj.get('barcode', '')).strip()
        pname = str(obj.get('pname', '')).strip()
        po = obj.get('po_code', '')
        po_set.add(po)
        
        wg = resolve_wt(nw, bc)
        if po_qty <= 0 or wg <= 0: continue
        tons = po_qty * wg / 1_000_000
        total_tons += tons
        items.append({'po': po, 'bc': bc, 'pname': pname, 'po_qty': po_qty, 'qty': qty, 'qr': qr, 'wg': wg, 'tons': tons})
    
    print(f"{'='*70}")
    print(f"  {target}: {total_tons:.2f}T | {len(items)} items | {len(po_set)} POs")
    print(f"{'='*70}")
    
    # Check for same barcode appearing in multiple POs
    bc_po = defaultdict(list)
    for i in items:
        bc_po[i['bc']].append(i)
    multi_po_bc = {bc: rows for bc, rows in bc_po.items() if len(rows) > 1}
    multi_tons = sum(sum(r['tons'] for r in rows[1:]) for rows in multi_po_bc.values())
    
    print(f"\n  Barcodes in multiple POs: {len(multi_po_bc)} ({multi_tons:.2f}T from extra POs)")
    
    # Top barcodes appearing in multiple POs
    multi_sorted = sorted(multi_po_bc.items(), key=lambda x: sum(r['tons'] for r in x[1]), reverse=True)
    print(f"\n  Top 10 multi-PO barcodes:")
    for bc, rows in multi_sorted[:10]:
        total = sum(r['tons'] for r in rows)
        pos = set(r['po'] for r in rows)
        print(f"    {bc:<15} {len(pos)} POs  {total:.3f}T  {rows[0]['pname'][:35]}")
        for r2 in rows:
            print(f"      {r2['po']} po_qty={r2['po_qty']:.0f} qty={r2['qty']:.0f} rcpt={r2['qr']:.0f}")
    print()

print("Done.")
