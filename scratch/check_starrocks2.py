import pymysql

conn = pymysql.connect(
    host='103.147.122.56',
    port=9030,
    user='kfm_scm_lam_nguyen',
    password='QPYZfjWWhJcHNi5ab5Au',
    database='kfm_scm',
    connect_timeout=10
)
cur = conn.cursor()

# 1. Count total tables
print("=" * 70)
print("TOTAL TABLES IN kfm_scm")
print("=" * 70)
cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE TABLE_SCHEMA='kfm_scm'")
print(f"  Total tables: {cur.fetchone()[0]}")

# 2. Show ALL tables with sizes
print()
print("=" * 70)
print("ALL TABLES - sorted by DATA_LENGTH (size)")
print("=" * 70)
cur.execute("""
    SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, TABLE_TYPE, UPDATE_TIME 
    FROM information_schema.tables 
    WHERE TABLE_SCHEMA='kfm_scm' 
    ORDER BY COALESCE(DATA_LENGTH, 0) DESC
""")
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
total_size = 0
for r in rows:
    rd = dict(zip(cols, r))
    sz = rd.get('DATA_LENGTH') or 0
    total_size += int(sz)
    sz_mb = int(sz) / 1024 / 1024
    print(f"  {rd['TABLE_NAME']:65s} | {str(rd.get('TABLE_ROWS','?')):>12s} rows | {sz_mb:>8.1f} MB | {rd.get('TABLE_TYPE','')}")
print(f"\n  TOTAL SIZE: {total_size/1024/1024/1024:.2f} GB")

# 3. Check if there are materialized views
print()
print("=" * 70)
print("MATERIALIZED VIEWS")
print("=" * 70)
try:
    cur.execute("SHOW MATERIALIZED VIEWS FROM kfm_scm")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if rows:
        for r in rows:
            rd = dict(zip(cols, r))
            print(f"  Name: {rd.get('Name', 'N/A')} | Status: {rd.get('is_active', rd.get('text', 'N/A'))}")
    else:
        print("  No materialized views found.")
except Exception as e:
    print(f"  Error: {e}")

# 4. Check compaction status (this often causes "syncing" feel)
print()
print("=" * 70)
print("BACKENDS STATUS")
print("=" * 70)
try:
    cur.execute("SHOW BACKENDS")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for r in rows:
        rd = dict(zip(cols, r))
        print(f"  ID: {rd.get('BackendId', rd.get('Id', 'N/A'))}")
        print(f"  Host: {rd.get('Host', rd.get('IP', 'N/A'))}")
        print(f"  Alive: {rd.get('Alive', 'N/A')}")
        print(f"  SystemDecommissioned: {rd.get('SystemDecommissioned', 'N/A')}")
        print(f"  TabletNum: {rd.get('TabletNum', 'N/A')}")
        print(f"  DataUsedCapacity: {rd.get('DataUsedCapacity', 'N/A')}")
        print(f"  AvailCapacity: {rd.get('AvailCapacity', 'N/A')}")
        print(f"  TotalCapacity: {rd.get('TotalCapacity', 'N/A')}")
        print(f"  UsedPct: {rd.get('UsedPct', 'N/A')}")
        print(f"  ErrMsg: {rd.get('ErrMsg', 'N/A')}")
        print(f"  LastStartTime: {rd.get('LastStartTime', 'N/A')}")
        print("  ---")
except Exception as e:
    print(f"  Error: {e}")

# 5. Check tablet status for large CDC tables
print()
print("=" * 70)
print("CDC TABLE DETAILS")
print("=" * 70)
cdc_tables = [r for r in rows if '__cdc_' in str(dict(zip(cols, r)).get('TABLE_NAME',''))] if False else []

# Let's get cdc tables from info schema
cur.execute("""
    SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, UPDATE_TIME 
    FROM information_schema.tables 
    WHERE TABLE_SCHEMA='kfm_scm' AND TABLE_NAME LIKE '%%cdc%%'
    ORDER BY DATA_LENGTH DESC
""")
cols2 = [d[0] for d in cur.description]
for r in cur.fetchall():
    rd = dict(zip(cols2, r))
    tbl = rd['TABLE_NAME']
    print(f"\n  >> {tbl}")
    print(f"     Rows: {rd.get('TABLE_ROWS','?')} | Size: {(int(rd.get('DATA_LENGTH',0))/1024/1024):.1f} MB | Updated: {rd.get('UPDATE_TIME')}")
    # Check recent partitions
    try:
        cur.execute(f"SHOW PARTITIONS FROM `{tbl}`")
        pcols = [d[0] for d in cur.description]
        prows = cur.fetchall()
        print(f"     Partitions: {len(prows)}")
        if prows:
            last = dict(zip(pcols, prows[-1]))
            print(f"     Last partition: {last.get('PartitionName','?')} | State: {last.get('State','?')} | Buckets: {last.get('Buckets','?')}")
    except Exception as e:
        print(f"     Partition error: {e}")

conn.close()
print("\nDone.")
