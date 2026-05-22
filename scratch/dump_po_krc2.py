# -*- coding: utf-8 -*-
"""
Dump PO KRC — Part 2: sample data + check net_weight format
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

# 1) Check columns in kf_receipt_items
print("=" * 70)
print("  kf_receipt_items — column names")
print("=" * 70)
r_cols = q("DESCRIBE kf_receipt_items")
print(r_cols[:2000])

# 2) Sample rows from receipt_items for today
print(f"\n\n{'='*70}")
print("  Sample receipt_items for 22/05/2026")
print("=" * 70)

r_sample = q(f"""
SELECT *
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND toDate(fromUnixTimestamp(toUInt32(po.delivery_date))) = '2026-05-22'
LIMIT 3
FORMAT JSONEachRow
""")

for i, line in enumerate(r_sample.split('\n')):
    if not line.strip():
        continue
    obj = json.loads(line)
    print(f"\n  Row {i+1}:")
    for k, v in obj.items():
        print(f"    {k}: {v}")

# 3) Specific weight check
print(f"\n\n{'='*70}")
print("  Weight calculation check: ri.qty * ri.net_weight / 1000 / 1000")
print("=" * 70)

r_w = q(f"""
SELECT
    ri.purchase_code,
    ri.product_id,
    ri.qty,
    ri.net_weight,
    ri.qty * ri.net_weight as raw_product,
    ri.qty * ri.net_weight / 1000 as in_kg_maybe,
    ri.qty * ri.net_weight / 1000 / 1000 as in_tons_maybe
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH}'
    AND po.deleted = 0
WHERE ri.branch_id = '{KRC_BRANCH}'
  AND toDate(fromUnixTimestamp(toUInt32(po.delivery_date))) = '2026-05-22'
ORDER BY ri.qty * ri.net_weight DESC
LIMIT 15
FORMAT JSONEachRow
""")

print(f"\n  {'purchase_code':<20} {'qty':>8} {'net_wt':>10} {'raw':>14} {'÷1000':>12} {'÷1M(tons)':>12}")
print(f"  {'─'*20} {'─'*8} {'─'*10} {'─'*14} {'─'*12} {'─'*12}")
for line in r_w.split('\n'):
    if not line.strip():
        continue
    obj = json.loads(line)
    print(f"  {str(obj.get('purchase_code',''))[:20]:<20} "
          f"{float(obj.get('qty',0)):>8.0f} "
          f"{float(obj.get('net_weight',0)):>10.2f} "
          f"{float(obj.get('raw_product',0)):>14.2f} "
          f"{float(obj.get('in_kg_maybe',0)):>12.2f} "
          f"{float(obj.get('in_tons_maybe',0)):>12.4f}")

# 4) Current capacity_forecast.json
print(f"\n\n{'='*70}")
print("  capacity_forecast.json — KRC last 10 entries")
print("=" * 70)

cf_path = os.path.join(BASE, 'docs', 'data', 'capacity_forecast.json')
if os.path.exists(cf_path):
    with open(cf_path, 'r', encoding='utf-8') as f:
        cf = json.load(f)
    krc_data = cf.get('krc', {}).get('data', [])
    print(f"  Last updated: {cf.get('_updated','?')}")
    print(f"  Total KRC entries: {len(krc_data)}")
    print(f"\n  {'Date':<15} {'Tons':>8} {'%Cap':>8} {'Alert':>6}")
    print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*6}")
    for entry in krc_data[-10:]:
        print(f"  {entry['date']:<15} {entry['tons']:>8.2f} {entry['pct_capacity']:>7.1f}% {'⚠' if entry['exceeds_alert'] else ''}")
else:
    print(f"  ⚠ Not found: {cf_path}")

print("\nDone.")
