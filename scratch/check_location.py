import requests
import pymysql
import json

print("==== Checking ClickHouse `kf_trip_locations_items` ====")
url = "http://103.140.248.114:32015/"
auth = ("scm_lam", "xukco1-roghaB-fuqfum")

query = """
SELECT tl_branch_id, t_from_location_name_abbreviates 
FROM kdb.kf_trip_locations_items 
LIMIT 5
"""
try:
    response = requests.post(url, auth=auth, params={"database": "kdb", "query": query + " FORMAT JSON"})
    if response.status_code == 200:
        data = response.json()
        for row in data['data']:
            print(row)
    else:
        print("ClickHouse Error:", response.text)
except Exception as e:
    print(e)


print("\n==== Checking StarRocks `kf_trips` ====")
try:
    conn = pymysql.connect(
        host="103.147.122.56",
        port=9030,
        user="kfm_scm_lam_nguyen",
        password="QPYZfjWWhJcHNi5ab5Au",
        database="kfm_scm"
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT t_locations, t_trip_location_ids FROM __cdc_kfm_kf_inventories_kf_trips LIMIT 2")
        rows = cursor.fetchall()
        for row in rows:
            print("t_locations:", row[0][:200] if row[0] else None)
            print("t_trip_location_ids:", row[1][:200] if row[1] else None)
            print("---")
            
        print("\n==== Checking for Location tables in StarRocks ====")
        cursor.execute("SHOW TABLES LIKE '%location%'")
        loc_tables = cursor.fetchall()
        for t in loc_tables:
            print(t[0])
            
    conn.close()
except Exception as e:
    print(e)
