# -*- coding: utf-8 -*-
"""
Part 3: Check product_static weight + estimate tonnage recovery
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
    r = requests.get(cfg['base_url'], params={**params, 'query': sql}, timeout=120)
    r.raise_for_status()
    return r.text.strip()

KRC_BRANCH = '5fdc170ebd89c10006f15b7c'

# ═══════════════════════════════════════════════════════════
# 1) Check product_static for zero-weight barcodes
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("  product_static: weight lookup for zero-wt barcodes")
print("=" * 70)

barcodes = ['10791','1101302','10792','10356','11026','10911','1101062','10466',
            '10790','8936049691058','10354','1100816','10900','10463',
            '8936114400110','10273','10908','10902','10826','10511']

bc_list = "','".join(barcodes)
r4 = q(f"""
SELECT
    base_barcode,
    name,
    base_net_weight
FROM kf_product_static
WHERE base_barcode IN ('{bc_list}')
FORMAT JSONEachRow
""")

print(f"\n  {'Barcode':<15} {'base_net_wt':>12}  Name")
print(f"  {'─'*15} {'─'*12}  {'─'*45}")

has_wt = 0
no_wt = 0
for line in r4.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    bc = str(obj.get('base_barcode',''))
    nw = float(obj.get('base_net_weight', 0))
    name = str(obj.get('name',''))[:50]
    marker = '✅' if nw > 0 else '❌'
    if nw > 0:
        has_wt += 1
    else:
        no_wt += 1
    print(f"  {bc:<15} {nw:>12.1f}  {marker} {name}")

print(f"\n  → {has_wt} CÓ weight, {no_wt} KHÔNG CÓ weight trong product_static")

# ═══════════════════════════════════════════════════════════
# 2) ESTIMATE tonnage recovered via product_static
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  ESTIMATE: Tonnage recovered via product_static mapping")
print("=" * 70)

r5 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date)), '%d/%m/%Y') AS del_date,
    SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)) AS tons_current,
    SUM(if(ri.net_weight = 0 AND p.base_net_weight > 0, ri.qty * p.base_net_weight / 1000 / 1000, 0)) AS tons_recovered,
    SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)) + 
    SUM(if(ri.net_weight = 0 AND p.base_net_weight > 0, ri.qty * p.base_net_weight / 1000 / 1000, 0)) AS tons_total,
    SUM(if(ri.net_weight = 0 AND (p.base_net_weight IS NULL OR p.base_net_weight = 0), ri.qty, 0)) AS qty_still_miss
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
LEFT JOIN kf_product_static p
    ON ri.product_id = p.id
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) >= '2026-05-01'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) < '2026-06-01'
GROUP BY del_date
ORDER BY del_date
FORMAT JSONEachRow
""")

print(f"\n  {'Date':<12} {'Current':>10} {'+Master':>10} {'= TOTAL':>10} {'Δ%':>7} {'Miss qty':>10}")
print(f"  {'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*7} {'─'*10}")

for line in r5.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    d = obj['del_date']
    cur = float(obj['tons_current'])
    rec = float(obj['tons_recovered'])
    tot = float(obj['tons_total'])
    miss = float(obj['qty_still_miss'])
    delta_pct = (rec / cur * 100) if cur > 0 else 0
    print(f"  {d:<12} {cur:>10.2f} {rec:>+10.2f} {tot:>10.2f} {delta_pct:>+6.1f}% {miss:>10,.0f}")

# ═══════════════════════════════════════════════════════════
# 3) Date range & total stats
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  TOTAL date range & coverage")
print("=" * 70)

r6 = q(f"""
SELECT
    count(DISTINCT toDate(fromUnixTimestamp(toUInt32(po.delivery_date)))) AS total_dates,
    min(toDate(fromUnixTimestamp(toUInt32(po.delivery_date)))) AS min_date,
    max(toDate(fromUnixTimestamp(toUInt32(po.delivery_date)))) AS max_date
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
""")
print(f"\n  total_dates | min_date | max_date = {r6}")

# Per-month summary
print(f"\n  Monthly summary (last 6 months):")
r7 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date)), '%Y-%m') AS month,
    SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)) AS tons_wt,
    countIf(ri.net_weight > 0) AS rows_wt,
    countIf(ri.net_weight = 0) AS rows_no_wt,
    count(DISTINCT toDate(fromUnixTimestamp(toUInt32(po.delivery_date)))) AS days
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) >= '2025-12-01'
GROUP BY month
ORDER BY month
FORMAT JSONEachRow
""")

print(f"  {'Month':<10} {'Tons(wt>0)':>12} {'RowsOK':>8} {'Rows0wt':>9} {'%miss':>7} {'Days':>6}")
print(f"  {'─'*10} {'─'*12} {'─'*8} {'─'*9} {'─'*7} {'─'*6}")

for line in r7.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    m = obj['month']
    tons = float(obj['tons_wt'])
    rw = int(obj['rows_wt'])
    rn = int(obj['rows_no_wt'])
    days = int(obj['days'])
    pct = rn/(rw+rn)*100 if (rw+rn)>0 else 0
    print(f"  {m:<10} {tons:>12.2f} {rw:>8,} {rn:>9,} {pct:>6.1f}% {days:>6}")

print("\nDone.")
