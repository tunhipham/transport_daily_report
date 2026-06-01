# -*- coding: utf-8 -*-
"""Check timezone issue for PO1002529950"""
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

# 1) Raw timestamp for PO1002529950
print("=" * 70)
print("  PO1002529950 — raw timestamp check")
print("=" * 70)

r1 = q(f"""
SELECT
    code,
    delivery_date_vendor_confirm AS raw_ts,
    fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)) AS utc_datetime,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)), '%d/%m/%Y %H:%M') AS utc_formatted,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)), '%d/%m/%Y %H:%M', 'Asia/Ho_Chi_Minh') AS vn_formatted,
    delivery_date AS raw_del_date,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date)), '%d/%m/%Y %H:%M') AS del_date_utc,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date)), '%d/%m/%Y %H:%M', 'Asia/Ho_Chi_Minh') AS del_date_vn
FROM kf_purchase_order
WHERE code = 'PO1002529950'
FORMAT JSONEachRow
""")

for line in r1.split('\n'):
    if not line.strip(): continue
    o = json.loads(line)
    print(f"\n  PO: {o['code']}")
    print(f"  delivery_date_vendor_confirm:")
    print(f"    raw timestamp:  {o['raw_ts']}")
    print(f"    UTC formatted:  {o['utc_formatted']}")
    print(f"    VN formatted:   {o['vn_formatted']}")
    print(f"  delivery_date:")
    print(f"    raw timestamp:  {o['raw_del_date']}")
    print(f"    UTC formatted:  {o['del_date_utc']}")
    print(f"    VN formatted:   {o['del_date_vn']}")

# 2) Check a few more POs to confirm pattern
print(f"\n\n{'='*70}")
print("  Last 10 POs — UTC vs VN timezone comparison")
print("=" * 70)

r2 = q(f"""
SELECT
    code,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)), '%d/%m/%Y %H:%M') AS utc,
    formatDateTime(fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)), '%d/%m/%Y %H:%M', 'Asia/Ho_Chi_Minh') AS vn
FROM kf_purchase_order
WHERE branch_id = '{KRC}'
  AND deleted = 0
  AND delivery_date_vendor_confirm > 0
ORDER BY delivery_date_vendor_confirm DESC
LIMIT 10
FORMAT JSONEachRow
""")

print(f"\n  {'PO':<18} {'UTC':>16} {'VN (UTC+7)':>16}")
for line in r2.split('\n'):
    if not line.strip(): continue
    o = json.loads(line)
    diff = " ← DATE SHIFT!" if o['utc'].split(' ')[0] != o['vn'].split(' ')[0] else ""
    print(f"  {o['code']:<18} {o['utc']:>16} {o['vn']:>16}{diff}")

# 3) Count how many POs have date shift between UTC and VN
print(f"\n\n{'='*70}")
print("  How many POs have date shift (UTC vs VN)?")
print("=" * 70)

r3 = q(f"""
SELECT
    countIf(
        formatDateTime(fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)), '%d/%m/%Y') !=
        formatDateTime(fromUnixTimestamp(toUInt32(delivery_date_vendor_confirm)), '%d/%m/%Y', 'Asia/Ho_Chi_Minh')
    ) AS shifted,
    count(*) AS total
FROM kf_purchase_order
WHERE branch_id = '{KRC}'
  AND deleted = 0
  AND delivery_date_vendor_confirm > 0
FORMAT JSONEachRow
""")

for line in r3.split('\n'):
    if not line.strip(): continue
    o = json.loads(line)
    pct = float(o['shifted']) / float(o['total']) * 100 if float(o['total']) > 0 else 0
    print(f"  Shifted: {o['shifted']} / {o['total']} ({pct:.1f}%)")

# 4) Check ClickHouse server timezone
print(f"\n\n{'='*70}")
print("  ClickHouse server timezone")
print("=" * 70)
r4 = q("SELECT timezone()")
print(f"  Server timezone: {r4}")

print("\nDone.")
