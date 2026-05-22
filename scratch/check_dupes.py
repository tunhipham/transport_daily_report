# -*- coding: utf-8 -*-
"""Check receipt_status of duplicate PO+Barcode rows"""
import sys, os, json
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'g:\My Drive\DOCS\transport_daily_report\script')
from data_pipeline.config import load_clickhouse_config
import requests

cfg = load_clickhouse_config()
p = {'user': cfg['user'], 'password': cfg['password'], 'database': cfg['database']}
KRC = '5fdc170ebd89c10006f15b7c'

sql = f"""
SELECT
    ri.purchase_code, ri.product_barcode, ri.receipt_code,
    ri.receipt_status, ri.purchase_status,
    ri.po_qty, ri.qty, ri.qty_receipt,
    ri.product_name
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC}' AND po.deleted = 0
WHERE ri.branch_id = '{KRC}'
  AND toDate(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm))) = '2026-05-18'
ORDER BY ri.purchase_code, ri.product_barcode, ri.receipt_code
FORMAT JSONEachRow
"""

r = requests.get(cfg['base_url'], params={**p, 'query': sql}, timeout=120)
r.raise_for_status()

combos = defaultdict(list)
for line in r.text.strip().split('\n'):
    if not line.strip(): continue
    obj = json.loads(line)
    key = f"{obj['purchase_code']}|{obj['product_barcode']}"
    combos[key].append(obj)

dupes = {k: v for k, v in combos.items() if len(v) > 1}
print(f"Total combos: {len(combos)}, Duplicates: {len(dupes)}\n")

# Receipt status distribution
print("Receipt status (all rows):")
all_rs = defaultdict(int)
for rows in combos.values():
    for r2 in rows:
        all_rs[r2['receipt_status']] += 1
for s, c in sorted(all_rs.items()):
    print(f"  receipt_status={s}: {c} rows")

print("\nPurchase status (all rows):")
all_ps = defaultdict(int)
for rows in combos.values():
    for r2 in rows:
        all_ps[r2['purchase_status']] += 1
for s, c in sorted(all_ps.items()):
    print(f"  purchase_status={s}: {c} rows")

# Duplicate detail
print(f"\n--- Duplicate samples (first 8) ---")
for k in list(dupes.keys())[:8]:
    rows = dupes[k]
    po, bc = k.split('|')
    print(f"\n  PO={po} | BC={bc} | {rows[0]['product_name'][:40]}")
    for r2 in rows:
        print(f"    receipt={r2['receipt_code']} r_status={r2['receipt_status']} "
              f"p_status={r2['purchase_status']} po_qty={r2['po_qty']} "
              f"qty={r2['qty']} qty_rcpt={r2['qty_receipt']}")

# How many dupes have different receipt_codes vs same receipt_code?
diff_receipt = 0
same_receipt = 0
for k, rows in dupes.items():
    codes = set(r2['receipt_code'] for r2 in rows)
    if len(codes) > 1:
        diff_receipt += 1
    else:
        same_receipt += 1
print(f"\nDuplicate analysis:")
print(f"  Different receipt_code: {diff_receipt}")
print(f"  Same receipt_code: {same_receipt}")

print("\nDone.")
