import os, sys, json, requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CH_CONFIG_PATH = os.path.join(BASE, "config", "mcp_clickhouse.json")

with open(CH_CONFIG_PATH, encoding="utf-8") as f:
    cfg = json.load(f)
base_url, params = cfg["base_url"], cfg["params"]

sql = """
SELECT t_code, t_status, dest, noi_chuyen 
FROM kdb.kf_trip_locations_items 
WHERE t_code = 'TRIP0000053831'
FORMAT JSONEachRow
"""

r = requests.get(base_url, params={**params, "query": sql})
for line in r.text.strip().split('\n'):
    print(line)
