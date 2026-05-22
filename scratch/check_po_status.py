# -*- coding: utf-8 -*-
"""Check PO status distribution — find cancelled POs"""
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

# 1) PO status distribution (all time)
print("=" * 70)
print("  PO STATUS distribution — KRC branch (all time)")
print("=" * 70)
r1 = q(f"""
SELECT
    status,
    sub_status,
    COUNT(*) AS cnt,
    SUM(sum_qty) AS total_qty
FROM kf_purchase_order
WHERE branch_id = '{KRC}'
  AND deleted = 0
GROUP BY status, sub_status
ORDER BY status, sub_status
""")
print(f"\n  status | sub_status | count | total_qty")
print(f"  {r1}")

# 2) Tháng 5/2026: tonnage by PO status
print(f"\n\n{'='*70}")
print("  T5/2026: Tonnage breakdown by PO status")
print("=" * 70)

r2 = q(f"""
SELECT
    po.status,
    count(DISTINCT po.code) AS po_count,
    SUM(ri.qty) AS total_qty,
    round(SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)), 2) AS tons_with_wt
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC}'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) >= '2026-05-01'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) < '2026-06-01'
GROUP BY po.status
ORDER BY po.status
""")
print(f"\n  status | POs | qty | tons")
print(f"  {r2}")

# 3) Check transfer status filter for comparison
print(f"\n\n{'='*70}")
print("  Transfer (PT) status filter: t.status != 6")
print("  → status 6 = HỦY (cancelled)")
print("=" * 70)

# 4) Show per-day impact of filtering status
print(f"\n\n{'='*70}")
print("  T5/2026: Daily tonnage — ALL vs filtered (exclude status 6)")
print("=" * 70)

r4 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date)), '%d/%m/%Y') AS del_date,
    round(SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)), 2) AS tons_all,
    round(SUM(if(ri.net_weight > 0 AND po.status != 6, ri.qty * ri.net_weight / 1000 / 1000, 0)), 2) AS tons_no_cancel,
    round(SUM(if(ri.net_weight > 0 AND po.status NOT IN (6, 7, 8), ri.qty * ri.net_weight / 1000 / 1000, 0)), 2) AS tons_strict,
    countIf(po.status = 6) AS rows_cancelled
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC}'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) >= '2026-05-01'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) < '2026-06-01'
GROUP BY del_date
ORDER BY del_date
FORMAT JSONEachRow
""")

print(f"\n  {'Date':<12} {'All':>8} {'No s=6':>8} {'Strict':>8} {'Cancelled':>10}")
print(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*10}")
for line in r4.split('\n'):
    if not line.strip(): continue
    obj = json.loads(line)
    print(f"  {obj['del_date']:<12} {float(obj['tons_all']):>8.2f} {float(obj['tons_no_cancel']):>8.2f} "
          f"{float(obj['tons_strict']):>8.2f} {int(obj['rows_cancelled']):>10}")

print("\nDone.")
