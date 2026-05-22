# -*- coding: utf-8 -*-
import sys, os
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

KRC = '5fdc170ebd89c10006f15b7c'

# All statuses across entire system
print("=" * 60)
print("  ALL PO statuses in kf_purchase_order (toàn hệ thống)")
print("=" * 60)
r1 = q("SELECT status, COUNT(*) as cnt FROM kf_purchase_order WHERE deleted=0 GROUP BY status ORDER BY status")
print(f"\n  status | count")
print(f"  -------+--------")
for line in r1.split('\n'):
    parts = line.split('\t')
    if len(parts) >= 2:
        print(f"  {parts[0]:>6} | {parts[1]}")

# KRC branch only
print(f"\n{'='*60}")
print(f"  KRC branch — status + sub_status")
print("=" * 60)
r2 = q(f"""
SELECT status, sub_status, COUNT(*) as cnt
FROM kf_purchase_order
WHERE branch_id = '{KRC}' AND deleted = 0
GROUP BY status, sub_status
ORDER BY status, sub_status
""")
print(f"\n  status | sub_status | count")
print(f"  -------+------------+--------")
for line in r2.split('\n'):
    parts = line.split('\t')
    if len(parts) >= 3:
        print(f"  {parts[0]:>6} | {parts[1]:>10} | {parts[2]}")

# Check if there are any status descriptions in the system
print(f"\n{'='*60}")
print(f"  Dự đoán ý nghĩa status PO:")
print("=" * 60)
print("""
  Status | Ý nghĩa (dự đoán từ data)
  -------+---------------------------
       1 | Draft / Nháp
       2 | Pending / Chờ duyệt  
       3 | Approved / Đã duyệt (chờ NCC xác nhận)
       4 | Rejected / Từ chối
       5 | Confirmed / NCC đã xác nhận
       6 | Cancelled / Đã hủy
       7 | Received / Đã nhận hàng
       8 | Closed / Đã đóng
       9 | Partial received / Nhận 1 phần
""")

print("Done.")
