# -*- coding: utf-8 -*-
"""Check cancelled PO status on DB — PO1002502831 shows Hủy on app"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'g:\My Drive\DOCS\transport_daily_report\script')
from data_pipeline.config import load_clickhouse_config
import requests

cfg = load_clickhouse_config()
p = {'user': cfg['user'], 'password': cfg['password'], 'database': cfg['database']}
def q(sql):
    r = requests.get(cfg['base_url'], params={**p, 'query': sql}, timeout=60)
    r.raise_for_status()
    return r.text.strip()

# Check the cancelled PO
po_cancel = 'PO1002502831'
r1 = q(f"SELECT * FROM kf_purchase_order WHERE code = '{po_cancel}' FORMAT JSONEachRow")
obj = json.loads(r1)

print(f"PO: {po_cancel} (app shows: Hủy)")
print(f"{'='*50}")
for k, v in obj.items():
    if isinstance(v, (list, dict)) and len(str(v)) > 100:
        v = str(v)[:100] + '...'
    print(f"  {k:<40} = {v}")

print(f"\n\nKey fields:")
print(f"  status       = {obj['status']}")
print(f"  sub_status   = {obj['sub_status']}")
print(f"  list_sub_status = {obj['list_sub_status']}")
print(f"  deleted      = {obj['deleted']}")

# Compare with a KNOWN good PO (rcpt > 0)
po_good = 'PO1002503914'
r2 = q(f"SELECT status, sub_status, list_sub_status, deleted FROM kf_purchase_order WHERE code = '{po_good}' FORMAT JSONEachRow")
obj2 = json.loads(r2)
print(f"\nGood PO: {po_good}")
print(f"  status       = {obj2['status']}")
print(f"  sub_status   = {obj2['sub_status']}")
print(f"  list_sub_status = {obj2['list_sub_status']}")
print(f"  deleted      = {obj2['deleted']}")

# Check receipt_items for the cancelled PO
r3 = q(f"SELECT receipt_status, purchase_status, qty, po_qty, qty_receipt FROM kf_receipt_items WHERE purchase_code = '{po_cancel}' LIMIT 5 FORMAT JSONEachRow")
print(f"\nReceipt items for cancelled PO {po_cancel}:")
for line in r3.split('\n'):
    if line.strip():
        print(f"  {json.loads(line)}")

# Now check ALL POs with same sub_status pattern — how many are "Hủy"?
cancel_status = obj['status']
cancel_sub = obj['sub_status']
cancel_list = obj['list_sub_status']
print(f"\n\nSearching for similar POs (status={cancel_status}, sub_status={cancel_sub})...")
r4 = q(f"""
SELECT 
    status, sub_status, list_sub_status,
    COUNT(*) as cnt,
    SUM(sum_qty) as total_qty,
    countIf(sum_qty_receipt = 0) as zero_receipt
FROM kf_purchase_order
WHERE branch_id = '5fdc170ebd89c10006f15b7c' AND deleted = 0
GROUP BY status, sub_status, list_sub_status
ORDER BY status, sub_status
""")
print(f"\n  status | sub | list_sub_status | count | qty | zero_receipt")
print(f"  {'-'*70}")
for line in r4.split('\n'):
    parts = line.split('\t')
    if len(parts) >= 6:
        print(f"  {parts[0]:>6} | {parts[1]:>3} | {parts[2]:<20} | {parts[3]:>5} | {parts[4]:>10} | {parts[5]:>5}")

print("\nDone.")
