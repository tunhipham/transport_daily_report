# -*- coding: utf-8 -*-
"""
Dump PO KRC data from ClickHouse DB — check format & numbers
"""
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

KRC_BRANCH = '5fdc170ebd89c10006f15b7c'

# ═══════════════════════════════════════════════════════════
# 1) THE EXACT QUERY used in capacity_forecast.py
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("  QUERY 1: Exact query from capacity_forecast.py (read_po_krc_from_db)")
print("=" * 70)

sql_main = f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date)), '%d/%m/%Y') AS del_date,
    SUM(ri.qty * ri.net_weight / 1000) / 1000 AS tons
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
GROUP BY del_date
HAVING tons > 0
ORDER BY del_date
FORMAT JSONEachRow
"""

print("\n  → Running main query...")
r1 = q(sql_main)
rows = [json.loads(l) for l in r1.split('\n') if l.strip()]
print(f"  Total dates returned: {len(rows)}")

# Show last 15 dates
print(f"\n  Last 15 dates:")
print(f"  {'Date':<15} {'Tons':>10}")
print(f"  {'─'*15} {'─'*10}")
for row in rows[-15:]:
    print(f"  {row['del_date']:<15} {float(row['tons']):>10.2f}")

# ═══════════════════════════════════════════════════════════
# 2) BREAKDOWN for THIS WEEK (19-23/05/2026)
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  QUERY 2: Detailed breakdown for this week (19-23/05/2026)")
print("=" * 70)

for check_date in ['2026-05-19', '2026-05-20', '2026-05-21', '2026-05-22', '2026-05-23']:
    print(f"\n  ── {check_date} ──")
    
    # PO count
    r_po = q(f"""
    SELECT
        COUNT(*) as po_count,
        SUM(sum_qty) as total_qty
    FROM kf_purchase_order
    WHERE branch_id = '{KRC_BRANCH}'
      AND toDate(fromUnixTimestamp(toUInt32(delivery_date))) = '{check_date}'
      AND deleted = 0
    """)
    print(f"  PO header: count|qty = {r_po}")
    
    # Receipt items weight (the actual query used)
    r_ri = q(f"""
    SELECT
        round(SUM(ri.qty * ri.net_weight / 1000) / 1000, 4) as total_tons,
        round(SUM(ri.qty), 0) as total_qty,
        COUNT(*) as row_count,
        COUNT(DISTINCT ri.purchase_code) as po_count
    FROM kf_receipt_items ri
    INNER JOIN kf_purchase_order po
        ON ri.purchase_code = po.code
        AND po.branch_id = '{KRC_BRANCH}'
        AND po.deleted = 0
    WHERE ri.branch_id = '{KRC_BRANCH}'
      AND toDate(fromUnixTimestamp(toUInt32(po.delivery_date))) = '{check_date}'
    """)
    print(f"  Receipt items: tons|qty|rows|POs = {r_ri}")

# ═══════════════════════════════════════════════════════════
# 3) Check ri.net_weight units — sample data
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  QUERY 3: Sample receipt_items to check net_weight units")
print("=" * 70)

r_sample = q(f"""
SELECT
    ri.purchase_code,
    ri.barcode,
    ri.product_name,
    ri.qty,
    ri.net_weight,
    ri.qty * ri.net_weight / 1000 / 1000 as tons_calc
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND toDate(fromUnixTimestamp(toUInt32(po.delivery_date))) = '2026-05-22'
ORDER BY ri.qty * ri.net_weight DESC
LIMIT 20
FORMAT JSONEachRow
""")

print(f"\n  Top 20 receipt items by weight (22/05/2026):")
print(f"  {'PO Code':<18} {'Barcode':<15} {'Qty':>8} {'net_weight':>12} {'tons_calc':>10}  Product")
print(f"  {'─'*18} {'─'*15} {'─'*8} {'─'*12} {'─'*10}  {'─'*35}")

for line in r_sample.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    po = str(obj.get('purchase_code',''))[:18]
    bc = str(obj.get('barcode',''))[:15]
    qty = float(obj.get('qty', 0))
    nw = float(obj.get('net_weight', 0))
    tc = float(obj.get('tons_calc', 0))
    name = str(obj.get('product_name',''))[:35]
    print(f"  {po:<18} {bc:<15} {qty:>8.0f} {nw:>12.2f} {tc:>10.4f}  {name}")

# ═══════════════════════════════════════════════════════════
# 4) Check delivery_date format in kf_purchase_order
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  QUERY 4: delivery_date raw values (epoch check)")
print("=" * 70)

r_epoch = q(f"""
SELECT
    delivery_date,
    fromUnixTimestamp(toUInt32(delivery_date)) as parsed_date,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date)), '%d/%m/%Y') as formatted
FROM kf_purchase_order
WHERE branch_id = '{KRC_BRANCH}'
  AND deleted = 0
  AND toDate(fromUnixTimestamp(toUInt32(delivery_date))) >= '2026-05-19'
  AND toDate(fromUnixTimestamp(toUInt32(delivery_date))) <= '2026-05-23'
ORDER BY delivery_date
LIMIT 10
FORMAT JSONEachRow
""")

print(f"\n  Sample delivery_date values:")
for line in r_epoch.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    print(f"  epoch={obj.get('delivery_date')}  →  parsed={obj.get('parsed_date')}  →  fmt={obj.get('formatted')}")

# ═══════════════════════════════════════════════════════════
# 5) Compare with capacity_forecast.json output
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  QUERY 5: Current capacity_forecast.json KRC data")
print("=" * 70)

cf_path = os.path.join(BASE, 'docs', 'data', 'capacity_forecast.json')
if os.path.exists(cf_path):
    with open(cf_path, 'r', encoding='utf-8') as f:
        cf = json.load(f)
    krc_data = cf.get('krc', {}).get('data', [])
    print(f"  Last updated: {cf.get('_updated','?')}")
    print(f"  KRC entries: {len(krc_data)}")
    print(f"\n  {'Date':<15} {'Tons':>8} {'%Cap':>8}")
    print(f"  {'─'*15} {'─'*8} {'─'*8}")
    for entry in krc_data[-15:]:
        print(f"  {entry['date']:<15} {entry['tons']:>8.2f} {entry['pct_capacity']:>7.1f}%")
else:
    print(f"  ⚠ File not found: {cf_path}")

print("\nDone.")
