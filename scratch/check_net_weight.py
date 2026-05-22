# -*- coding: utf-8 -*-
"""
Check net_weight = 0 impact — simplified queries
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

# Already got from part 1:
# OVERALL: HAS_WEIGHT=129,973 rows (23.8M qty) | ZERO=472,286 rows (67.2M qty)
# → 78% rows KHÔNG CÓ weight!
print("=" * 70)
print("  RECAP: OVERALL net_weight distribution (from part 1)")
print("=" * 70)
print("  HAS_WEIGHT: 129,973 rows  (23.8M qty)")
print("  ZERO:       472,286 rows  (67.2M qty)")
print("  → 78.4% rows KHÔNG CÓ net_weight!\n")

# ═══════════════════════════════════════════════════════════
# 2) Tháng 5/2026 daily breakdown
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("  THÁNG 5/2026: Daily breakdown")
print("=" * 70)

r2 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date)), '%d/%m/%Y') AS del_date,
    SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)) AS tons_with_wt,
    SUM(if(ri.net_weight = 0, ri.qty, 0)) AS qty_no_wt,
    countIf(ri.net_weight > 0) AS rows_ok,
    countIf(ri.net_weight = 0) AS rows_zero
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) >= '2026-05-01'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) < '2026-06-01'
GROUP BY del_date
ORDER BY del_date
FORMAT JSONEachRow
""")

print(f"\n  {'Date':<12} {'Tons(OK)':>10} {'RowsOK':>7} {'Rows0wt':>8} {'Qty miss':>10} {'%miss':>7}")
print(f"  {'─'*12} {'─'*10} {'─'*7} {'─'*8} {'─'*10} {'─'*7}")

for line in r2.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    d = obj['del_date']
    tons = float(obj['tons_with_wt'])
    qty_miss = float(obj['qty_no_wt'])
    rows_ok = int(obj['rows_ok'])
    rows_zero = int(obj['rows_zero'])
    total = rows_ok + rows_zero
    pct = rows_zero / total * 100 if total > 0 else 0
    print(f"  {d:<12} {tons:>10.2f} {rows_ok:>7} {rows_zero:>8} {qty_miss:>10,.0f} {pct:>6.1f}%")

# ═══════════════════════════════════════════════════════════
# 3) TOP 30 barcodes with net_weight=0
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  TOP 30 barcodes with net_weight=0 (tháng 5, by qty)")
print("=" * 70)

r3 = q(f"""
SELECT
    ri.product_barcode,
    any(ri.product_name) AS name,
    SUM(ri.qty) AS total_qty,
    COUNT(*) AS row_count
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND ri.net_weight = 0
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) >= '2026-05-01'
  AND fromUnixTimestamp(toUInt32(po.delivery_date)) < '2026-06-01'
GROUP BY ri.product_barcode
ORDER BY total_qty DESC
LIMIT 30
FORMAT JSONEachRow
""")

print(f"\n  {'Barcode':<15} {'Qty':>10} {'Rows':>6}  Product")
print(f"  {'─'*15} {'─'*10} {'─'*6}  {'─'*45}")
barcodes_zero = []
for line in r3.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    bc = str(obj.get('product_barcode',''))
    name = str(obj.get('name',''))[:50]
    qty = float(obj.get('total_qty', 0))
    rows = int(obj.get('row_count', 0))
    barcodes_zero.append(bc)
    print(f"  {bc:<15} {qty:>10,.0f} {rows:>6}  {name}")

# ═══════════════════════════════════════════════════════════
# 4) Check kf_product_static for these barcodes
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  kf_product_static: weight columns available?")
print("=" * 70)

r_cols = q("DESCRIBE kf_product_static")
for line in r_cols.split('\n'):
    col = line.split('\t')[0]
    if any(k in col.lower() for k in ['weight', 'barcode', 'name', 'id']):
        print(f"    {line}")

if barcodes_zero:
    bc_list = "','".join(barcodes_zero[:20])
    r4 = q(f"""
    SELECT
        base_barcode,
        name,
        base_net_weight,
        base_gross_weight
    FROM kf_product_static
    WHERE base_barcode IN ('{bc_list}')
    FORMAT JSONEachRow
    """)
    
    print(f"\n  Product master data for zero-weight barcodes:")
    print(f"  {'Barcode':<15} {'base_net_wt':>12} {'base_gross':>12}  Name")
    print(f"  {'─'*15} {'─'*12} {'─'*12}  {'─'*40}")
    
    has_wt = 0
    no_wt = 0
    for line in r4.split('\n'):
        if not line.strip():
            continue
        obj = json.loads(line)
        bc = str(obj.get('base_barcode',''))
        nw = float(obj.get('base_net_weight', 0))
        gw = float(obj.get('base_gross_weight', 0))
        name = str(obj.get('name',''))[:45]
        if nw > 0:
            has_wt += 1
            marker = '✅'
        else:
            no_wt += 1
            marker = '❌'
        print(f"  {bc:<15} {nw:>12.1f} {gw:>12.1f}  {marker} {name}")
    
    print(f"\n  → {has_wt} CÓ weight, {no_wt} KHÔNG CÓ trong product_static")

# ═══════════════════════════════════════════════════════════
# 5) ESTIMATE tonnage recovered via product_static mapping
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  ESTIMATE: Tonnage if mapping via kf_product_static")
print("=" * 70)

r5 = q(f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date)), '%d/%m/%Y') AS del_date,
    SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)) AS tons_current,
    SUM(if(ri.net_weight = 0 AND p.base_net_weight > 0, ri.qty * p.base_net_weight / 1000 / 1000, 0)) AS tons_recovered,
    SUM(if(ri.net_weight > 0, ri.qty * ri.net_weight / 1000 / 1000, 0)) + 
    SUM(if(ri.net_weight = 0 AND p.base_net_weight > 0, ri.qty * p.base_net_weight / 1000 / 1000, 0)) AS tons_total,
    SUM(if(ri.net_weight = 0 AND (p.base_net_weight = 0 OR p.base_net_weight IS NULL), ri.qty, 0)) AS qty_still_miss
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

print(f"\n  {'Date':<12} {'Current':>10} {'+Recovered':>11} {'= TOTAL':>10} {'Δ%':>7} {'Qty miss':>10}")
print(f"  {'─'*12} {'─'*10} {'─'*11} {'─'*10} {'─'*7} {'─'*10}")

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
    print(f"  {d:<12} {cur:>10.2f} {rec:>+11.2f} {tot:>10.2f} {delta_pct:>+6.1f}% {miss:>10,.0f}")

# ═══════════════════════════════════════════════════════════
# 6) Date range
# ═══════════════════════════════════════════════════════════
print(f"\n\n{'='*70}")
print("  Total date range in DB")
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

print("\nDone.")
