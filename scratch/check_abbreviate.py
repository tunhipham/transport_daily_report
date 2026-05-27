import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

url = "http://103.140.248.114:32015/"
auth = ("scm_lam", "xukco1-roghaB-fuqfum")

# Check branch_name_abbreviate - this should match the "Nơi nhận (Tên viết tắt)" in xlsx 
q = "SELECT id, branch_code, branch_name_abbreviate, branch_name FROM kdb.kf_branch_location WHERE branch_code IN ('A101','A103','A106','60','70','90') FORMAT JSON"
r = requests.post(url, auth=auth, params={"database": "kdb", "query": q})
if r.status_code == 200:
    print("branch_name_abbreviate vs branch_code:")
    for row in r.json()['data']:
        print(f"  code={row['branch_code']}, abbreviate={row['branch_name_abbreviate']}, full={row['branch_name']}")

# Now test: join trip data with branch_name_abbreviate to get the exact dest name
q2 = """
SELECT DISTINCT b.branch_name_abbreviate as dest, count(*) as cnt
FROM kdb.kf_trip_locations_items t
LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
WHERE t.t_departure >= '2026-05-20' AND t.t_departure <= '2026-05-20 23:59:59'
GROUP BY dest
ORDER BY cnt DESC
LIMIT 15
FORMAT JSON
"""
r2 = requests.post(url, auth=auth, params={"database": "kdb", "query": q2})
if r2.status_code == 200:
    print("\nDest abbreviated names (from trip join):")
    for row in r2.json()['data']:
        print(f"  {row['dest']}: {row['cnt']} rows")
