import json, sys, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('config/mcp_clickhouse.json', encoding='utf-8') as f:
    cfg = json.load(f)

base_url = cfg['base_url']
params = cfg['params']

# Check what container/basket columns exist
sql = """
SELECT 
    barrel_basket_name,
    tli_transfer_qty,
    tli_received_qty,
    t_code,
    b.branch_name_abbreviate AS dest
FROM kdb.kf_trip_locations_items t
LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
WHERE toDate(t.t_departure) = '2026-05-27'
  AND barrel_basket_name != ''
LIMIT 30
FORMAT JSON
"""

r = requests.get(base_url, params={**params, "query": sql}, timeout=30)
data = r.json()
for row in data.get("data", [])[:15]:
    print(f"  {row['t_code']} | {row['dest']} | {row['barrel_basket_name']} | giao={row['tli_transfer_qty']} | nhận={row['tli_received_qty']}")

print(f"\nTotal rows: {data.get('rows', 0)}")

# Check distinct barrel_basket_name values
sql2 = """
SELECT DISTINCT barrel_basket_name, count() as cnt
FROM kdb.kf_trip_locations_items
WHERE toDate(t_departure) >= '2026-05-01'
  AND barrel_basket_name != ''
GROUP BY barrel_basket_name
ORDER BY cnt DESC
FORMAT JSON
"""
r2 = requests.get(base_url, params={**params, "query": sql2}, timeout=30)
data2 = r2.json()
print("\nDistinct barrel_basket_name:")
for row in data2.get("data", []):
    print(f"  {row['barrel_basket_name']}: {row['cnt']}")
