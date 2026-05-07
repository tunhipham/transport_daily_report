import pymysql
import sys

conn = pymysql.connect(
    host='103.147.122.56',
    port=9030,
    user='kfm_scm_lam_nguyen',
    password='QPYZfjWWhJcHNi5ab5Au',
    database='kfm_scm',
    connect_timeout=10
)
cur = conn.cursor()

print("=" * 60)
print("1. CHECKING ROUTINE LOADS (CDC sync jobs)")
print("=" * 60)
try:
    cur.execute("SHOW ROUTINE LOAD")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if rows:
        for r in rows:
            row_dict = dict(zip(cols, r))
            print(f"  Name: {row_dict.get('Name', 'N/A')}")
            print(f"  State: {row_dict.get('State', 'N/A')}")
            print(f"  DB: {row_dict.get('DbName', 'N/A')}")
            print(f"  Table: {row_dict.get('TableName', 'N/A')}")
            print(f"  Progress: {row_dict.get('Progress', 'N/A')}")
            print(f"  Reason: {row_dict.get('ReasonOfStateChanged', 'N/A')}")
            print(f"  ErrorMsg: {row_dict.get('ErrorLogUrls', 'N/A')}")
            print("  ---")
    else:
        print("  No routine loads found.")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 60)
print("2. CHECKING PIPE STATUS")
print("=" * 60)
try:
    cur.execute("SHOW PIPES")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if rows:
        for r in rows:
            row_dict = dict(zip(cols, r))
            print(f"  Name: {row_dict.get('PIPE_NAME', row_dict.get('Name', 'N/A'))}")
            print(f"  State: {row_dict.get('STATE', row_dict.get('State', 'N/A'))}")
            print("  ---")
    else:
        print("  No pipes found.")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 60)
print("3. CHECKING RUNNING SYNC/LOAD TASKS")
print("=" * 60)
try:
    cur.execute("SHOW LOAD")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    # Show last 20
    for r in rows[-20:]:
        row_dict = dict(zip(cols, r))
        state = row_dict.get('State', 'N/A')
        label = row_dict.get('Label', 'N/A')
        print(f"  Label: {label} | State: {state}")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 60)
print("4. CHECKING MATERIALIZED VIEW REFRESH")
print("=" * 60)
try:
    cur.execute("SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, UPDATE_TIME FROM information_schema.tables WHERE TABLE_SCHEMA='kfm_scm' AND TABLE_TYPE='BASE TABLE' ORDER BY UPDATE_TIME DESC LIMIT 20")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for r in rows:
        row_dict = dict(zip(cols, r))
        print(f"  Table: {row_dict['TABLE_NAME']:40s} | Rows: {str(row_dict.get('TABLE_ROWS','?')):>10s} | Updated: {row_dict.get('UPDATE_TIME', 'N/A')}")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 60)
print("5. CHECKING RUNNING QUERIES")
print("=" * 60)
try:
    cur.execute("SHOW PROCESSLIST")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for r in rows:
        row_dict = dict(zip(cols, r))
        cmd = row_dict.get('Command', '')
        info = str(row_dict.get('Info', ''))[:100]
        time_val = row_dict.get('Time', 0)
        if cmd != 'Sleep' or int(time_val or 0) > 10:
            print(f"  ID: {row_dict.get('Id')} | User: {row_dict.get('User')} | Time: {time_val}s | Command: {cmd} | Info: {info}")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 60)
print("6. SHOW CATALOG/EXTERNAL CATALOGS")
print("=" * 60)
try:
    cur.execute("SHOW CATALOGS")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for r in rows:
        print(f"  {dict(zip(cols, r))}")
except Exception as e:
    print(f"  Error: {e}")

conn.close()
print("\nDone.")
