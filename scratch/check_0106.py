# -*- coding: utf-8 -*-
"""Check barcode 11486 detail on 01/06"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = r'g:\My Drive\DOCS\transport_daily_report'
sys.path.insert(0, os.path.join(BASE, 'script'))
from data_pipeline.config import load_clickhouse_config
import requests

cfg = load_clickhouse_config()
params = {'user': cfg['user'], 'password': cfg['password'], 'database': cfg['database']}

def q(sql):
    r = requests.get(cfg['base_url'], params={**params, 'query': sql}, timeout=60)
    r.raise_for_status()
    return r.text.strip()

KRC = '5fdc170ebd89c10006f15b7c'

# 1) All entries for barcode 11486 on 01/06
print("=" * 70)
print("  Barcode 11486 — all receipt_items entries on 01/06")
print("=" * 70)

r1 = q(f"""
SELECT
    ri.purchase_code AS po_code,
    ri.product_barcode,
    ri.product_name,
    ri.po_qty,
    ri.qty AS receipt_qty,
    ri.net_weight,
    po.status,
    po.sub_status,
    has(po.list_sub_status, 11) AS cancelled,
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') AS del_date
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC}'
  AND ri.product_barcode = '11486'
  AND formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') = '01/06/2026'
FORMAT JSONEachRow
""")

print(f"\n  PO_code | barcode | po_qty | rcpt_qty | nw | status | sub | cancelled | del_date | name")
for line in r1.split('\n'):
    if not line.strip(): continue
    o = json.loads(line)
    print(f"  {o['po_code']} | {o['product_barcode']} | {o['po_qty']} | {o['receipt_qty']} | {o['net_weight']} | {o['status']} | {o['sub_status']} | {o['cancelled']} | {o['del_date']} | {o.get('product_name','')[:30]}")

# 2) What does the dedup (GROUP BY purchase_code, barcode) produce?
print(f"\n\n{'='*70}")
print("  Deduped result for barcode 11486:")
print("=" * 70)

r2 = q(f"""
SELECT
    ri.purchase_code AS po_code,
    ri.product_barcode,
    any(ri.product_name) AS name,
    any(ri.po_qty) AS qty,
    any(ri.net_weight) AS nw
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC}'
    AND po.deleted = 0
    AND NOT has(po.list_sub_status, 11)
WHERE ri.branch_id = '{KRC}'
  AND ri.product_barcode = '11486'
  AND formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') = '01/06/2026'
GROUP BY po_code, ri.product_barcode
FORMAT JSONEachRow
""")

for line in r2.split('\n'):
    if not line.strip(): continue
    o = json.loads(line)
    print(f"  PO: {o['po_code']} | qty={o['qty']} | nw={o['nw']} | {o.get('name','')[:40]}")

# 3) Check this barcode on other dates to see if qty is always this large
print(f"\n\n{'='*70}")
print("  Barcode 11486 — qty on other dates (last 10):")
print("=" * 70)

r3 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') AS del_date,
    count(DISTINCT ri.purchase_code) AS po_count,
    SUM(qty_dedup) AS total_qty
FROM (
    SELECT
        ri.purchase_code,
        any(ri.po_qty) AS qty_dedup,
        any(po.delivery_date_vendor_confirm) AS dv
    FROM kf_receipt_items ri
    INNER JOIN kf_purchase_order po
        ON ri.purchase_code = po.code
        AND po.branch_id = '{KRC}'
        AND po.deleted = 0
        AND NOT has(po.list_sub_status, 11)
    WHERE ri.branch_id = '{KRC}'
      AND ri.product_barcode = '11486'
    GROUP BY ri.purchase_code, ri.product_barcode
)
GROUP BY del_date
ORDER BY del_date DESC
LIMIT 10
FORMAT JSONEachRow
""")

for line in r3.split('\n'):
    if not line.strip(): continue
    o = json.loads(line)
    print(f"  {o['del_date']}: {o['po_count']} POs, total qty={o['total_qty']}")

print("\nDone.")
