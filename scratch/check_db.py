import requests
import json
import pymysql

print("Checking ClickHouse...")
try:
    url = "http://103.140.248.114:32015/"
    auth = ("scm_lam", "xukco1-roghaB-fuqfum")
    query = """
    SELECT table, name, type 
    FROM system.columns 
    WHERE table LIKE '%claim%' OR table LIKE '%quality_tickets%'
    """
    response = requests.post(url, auth=auth, params={"database": "kdb", "query": query + " FORMAT JSON"})
    if response.status_code == 200:
        data = response.json()
        print("ClickHouse tables found:")
        tables = {}
        for row in data['data']:
            t = row['table']
            if t not in tables:
                tables[t] = []
            tables[t].append(f"{row['name']} ({row['type']})")
        for t, cols in tables.items():
            print(f"Table: {t}")
            print(f"  Columns: {', '.join(cols)}")
            print()
    else:
        print(f"ClickHouse Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"ClickHouse exception: {e}")

print("Checking StarRocks...")
try:
    conn = pymysql.connect(
        host="103.147.122.56",
        port=9030,
        user="kfm_scm_lam_nguyen",
        password="QPYZfjWWhJcHNi5ab5Au",
        database="kfm_scm"
    )
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE '%claim%'")
        tables_res = cursor.fetchall()
        cursor.execute("SHOW TABLES LIKE '%quality_tickets%'")
        tables_res += cursor.fetchall()
        print("StarRocks tables found:")
        for t_tuple in tables_res:
            t = t_tuple[0]
            print(f"Table: {t}")
            cursor.execute(f"DESCRIBE {t}")
            cols = cursor.fetchall()
            for col in cols:
                print(f"  {col[0]} ({col[1]})")
            print()
    conn.close()
except Exception as e:
    print(f"StarRocks exception: {e}")
