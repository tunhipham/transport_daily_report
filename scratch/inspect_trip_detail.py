import requests, json, codecs, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

url = "http://103.140.248.114:32015/"
auth = ("scm_lam", "xukco1-roghaB-fuqfum")

# Check how many unique (t_code, tl_branch_id) vs total rows 
q1 = """
SELECT 
    count(*) as total_rows,
    uniq(t_code, tl_branch_id) as unique_trip_dest,
    uniq(t_code) as unique_trips
FROM kdb.kf_trip_locations_items
WHERE t_departure >= '2026-05-18' AND t_departure <= '2026-05-24 23:59:59'
FORMAT JSON
"""
res1 = requests.post(url, auth=auth, params={"database": "kdb", "query": q1})
if res1.status_code == 200:
    d = res1.json()['data'][0]
    print(f"Total rows: {d['total_rows']}")
    print(f"Unique (trip, dest): {d['unique_trip_dest']}")
    print(f"Unique trips: {d['unique_trips']}")

# Check all t_from_location_name_abbreviates values (noi_chuyen equivalent)
q2 = """
SELECT DISTINCT arrayJoin(t_from_location_name_abbreviates) as noi_chuyen, count(*) as cnt
FROM kdb.kf_trip_locations_items
WHERE t_departure >= '2026-05-18' AND t_departure <= '2026-05-24 23:59:59'
GROUP BY noi_chuyen
ORDER BY cnt DESC
FORMAT JSON
"""
res2 = requests.post(url, auth=auth, params={"database": "kdb", "query": q2})
if res2.status_code == 200:
    print("\nNơi chuyển (t_from_location_name_abbreviates):")
    for row in res2.json()['data']:
        print(f"  {row['noi_chuyen']}: {row['cnt']} rows")

# Check: is there dest_status equivalent? 
# tl_arrival != empty -> can derive "Hoàn thành" for dest
# t_status: 3=completed, 2=delivering, 4=cancelled, 1=pending
q3 = """
SELECT 
    t_status, 
    countIf(tl_arrival != '' AND tl_arrival != '0001-01-01T00:00:00Z') as has_arrival,
    countIf(tl_arrival = '' OR tl_arrival = '0001-01-01T00:00:00Z') as no_arrival,
    count(*) as total
FROM kdb.kf_trip_locations_items
WHERE t_departure >= '2026-05-18' AND t_departure <= '2026-05-24 23:59:59'
GROUP BY t_status
ORDER BY t_status
FORMAT JSON
"""
res3 = requests.post(url, auth=auth, params={"database": "kdb", "query": q3})
if res3.status_code == 200:
    print("\nt_status vs tl_arrival:")
    print(f"  {'status':<10} {'has_arrival':>12} {'no_arrival':>12} {'total':>10}")
    for row in res3.json()['data']:
        print(f"  {row['t_status']:<10} {row['has_arrival']:>12} {row['no_arrival']:>12} {row['total']:>10}")

# Check barrel_basket_name values for ĐÔNG MÁT classification (tote = ĐÔNG)
q4 = """
SELECT DISTINCT barrel_basket_name, count(*) as cnt
FROM kdb.kf_trip_locations_items
WHERE t_departure >= '2026-05-18' AND t_departure <= '2026-05-24 23:59:59'
  AND arrayJoin(t_from_location_name_abbreviates) = 'QCABA'
GROUP BY barrel_basket_name
ORDER BY cnt DESC
LIMIT 20
FORMAT JSON
"""
res4 = requests.post(url, auth=auth, params={"database": "kdb", "query": q4})
if res4.status_code == 200:
    print("\nQCABA barrel_basket_name (for ĐÔNG/MÁT classification):")
    for row in res4.json()['data']:
        print(f"  {row['barrel_basket_name']}: {row['cnt']}")

# Check dest name format - do we get abbreviated names from branch lookup?
q5 = """
SELECT DISTINCT b.branch_name, count(*) as cnt
FROM kdb.kf_trip_locations_items t
LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
WHERE t.t_departure >= '2026-05-20' AND t.t_departure <= '2026-05-20 23:59:59'
GROUP BY b.branch_name
ORDER BY cnt DESC
LIMIT 10
FORMAT JSON
"""
res5 = requests.post(url, auth=auth, params={"database": "kdb", "query": q5})
if res5.status_code == 200:
    print("\nDest branch names (sample):")
    for row in res5.json()['data']:
        print(f"  {row['branch_name']}: {row['cnt']}")
