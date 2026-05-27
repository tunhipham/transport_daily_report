import requests
import json
import pymysql

print("================ Checking ClickHouse ================")
try:
    url = "http://103.140.248.114:32015/"
    auth = ("scm_lam", "xukco1-roghaB-fuqfum")
    
    # Check tables that might be related to trip/transport
    query = """
    SELECT table
    FROM system.tables
    WHERE database = 'kdb' 
      AND (table LIKE '%trip%' OR table LIKE '%transport%' OR table LIKE '%delivery%' OR table LIKE '%xe%' OR table LIKE '%route%')
    """
    response = requests.post(url, auth=auth, params={"database": "kdb", "query": query + " FORMAT JSON"})
    if response.status_code == 200:
        data = response.json()
        print("ClickHouse tables found:")
        for row in data['data']:
            print(f"- {row['table']}")
            
            # describe the table
            desc_query = f"DESCRIBE kdb.{row['table']}"
            desc_resp = requests.post(url, auth=auth, params={"database": "kdb", "query": desc_query + " FORMAT JSON"})
            if desc_resp.status_code == 200:
                cols = desc_resp.json()['data']
                print(f"  Columns: {', '.join([c['name'] for c in cols])}")
    else:
        print(f"ClickHouse Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"ClickHouse exception: {e}")


print("\n================ Checking StarRocks ================")
try:
    conn = pymysql.connect(
        host="103.147.122.56",
        port=9030,
        user="kfm_scm_lam_nguyen",
        password="QPYZfjWWhJcHNi5ab5Au",
        database="kfm_scm"
    )
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables_res = cursor.fetchall()
        
        target_keywords = ['trip', 'transport', 'delivery', 'route', 'xe']
        
        print("StarRocks tables found:")
        for t_tuple in tables_res:
            t = t_tuple[0].lower()
            if any(k in t for k in target_keywords):
                print(f"Table: {t_tuple[0]}")
                cursor.execute(f"DESCRIBE {t_tuple[0]}")
                cols = cursor.fetchall()
                print(f"  Columns: {', '.join([c[0] for c in cols])}")
    conn.close()
except Exception as e:
    print(f"StarRocks exception: {e}")
