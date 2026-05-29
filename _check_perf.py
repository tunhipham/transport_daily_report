import json, requests, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cfg = json.load(open('config/mcp_clickhouse.json', 'r', encoding='utf-8'))
base_url, params = cfg['base_url'], cfg['params']

# Check distinct t_status values
sql = """
SELECT t_status, count() as cnt 
FROM kdb.kf_trip_locations_items 
WHERE t_departure >= '2026-05-01' AND t_departure <= '2026-05-29 23:59:59'
GROUP BY t_status 
ORDER BY t_status
FORMAT JSONEachRow
"""
r = requests.get(base_url, params={**params, 'query': sql}, timeout=30)
print("t_status values (May 2026):")
for line in r.text.strip().split('\n'):
    if line.strip():
        obj = json.loads(line)
        print(f"  status={obj['t_status']}: {obj['cnt']} rows")

# Check: how many have arrival but status != 3?
sql2 = """
SELECT t_status, 
       countIf(tl_arrival IS NOT NULL AND tl_arrival != '0001-01-01 00:00:00') as with_arrival,
       countIf(tl_arrival IS NULL OR tl_arrival = '0001-01-01 00:00:00') as no_arrival
FROM kdb.kf_trip_locations_items 
WHERE t_departure >= '2026-05-25' AND t_departure <= '2026-05-25 23:59:59'
GROUP BY t_status
FORMAT JSONEachRow
"""
r2 = requests.get(base_url, params={**params, 'query': sql2}, timeout=30)
print("\n25/05 detail:")
for line in r2.text.strip().split('\n'):
    if line.strip():
        obj = json.loads(line)
        print(f"  status={obj['t_status']}: arrived={obj['with_arrival']}, no_arrival={obj['no_arrival']}")
