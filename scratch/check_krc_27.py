import sys, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "script"))

from data_pipeline.config import load_clickhouse_config
import requests
import json
from collections import defaultdict

KRC_BRANCH_ID = '5fdc170ebd89c10006f15b7c'
cfg = load_clickhouse_config()

sql = f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') AS del_date,
    ri.product_barcode AS barcode,
    any(ri.product_name) AS product_name,
    any(ri.po_qty) AS qty,
    any(ri.net_weight) AS net_weight
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH_ID}'
    AND po.deleted = 0
    AND NOT has(po.list_sub_status, 11)
WHERE ri.branch_id = '{KRC_BRANCH_ID}'
  AND formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') = '27/05/2026'
GROUP BY del_date, ri.purchase_code, ri.product_barcode
FORMAT JSONEachRow
"""

print("Querying 27/05/2026 KRC data...")
r = requests.get(
    cfg['base_url'],
    params={
        'user': cfg['user'],
        'password': cfg['password'],
        'database': cfg['database'],
        'query': sql
    }
)

if r.status_code != 200:
    print("Error:", r.text)
    sys.exit(1)

items = []
for line in r.text.strip().split('\n'):
    if not line.strip():
        continue
    items.append(json.loads(line))

print(f"Total rows for 27/05/2026: {len(items)}")

# Load master weights
try:
    from domains.daily.capacity_forecast import load_master_weights, extract_weight_from_name
    master = load_master_weights()
except Exception as e:
    print(f"Error loading master weights: {e}")
    master = {}

missing_weight = []
tons_total = 0

for item in items:
    qty = float(item.get('qty', 0))
    if qty <= 0: continue
    
    net_weight = float(item.get('net_weight', 0))
    barcode = str(item.get('barcode', '')).strip()
    name = str(item.get('product_name', '')).strip()
    
    weight_grams = 0
    source = ""
    if net_weight > 0:
        weight_grams = net_weight
        source = "db"
    elif barcode in master:
        weight_grams = master[barcode]
        source = "master"
    else:
        kg = extract_weight_from_name(name)
        if kg > 0:
            weight_grams = kg * 1000
            source = "name"
        else:
            missing_weight.append((barcode, name, qty))
            
    tons = (qty * weight_grams) / 1_000_000
    tons_total += tons

print(f"\nTotal tons calculated: {tons_total:.2f} T")
print(f"Items missing weight: {len(missing_weight)}")
if missing_weight:
    print("\nTop 10 missing weights:")
    for b, n, q in missing_weight[:10]:
        print(f"  {b}: {n} (qty: {q})")
