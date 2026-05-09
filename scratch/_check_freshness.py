# Quick freshness check for StarRocks + ClickHouse
import pymysql, json, requests, sys
sys.stdout.reconfigure(encoding='utf-8')

# StarRocks
with open('config/mcp_starrocks.json') as f:
    sr = json.load(f)
conn = pymysql.connect(host=sr['host'], port=sr['port'], user=sr['user'], password=sr['password'], database=sr['database'])
cur = conn.cursor()

print("=== StarRocks Data Freshness ===")

# KRC schedule for today/tomorrow
cur.execute("SELECT ngay, source, COUNT(1) cnt FROM krc_dashboard_delivery_schedule WHERE ngay IN ('08/05/2026','09/05/2026') GROUP BY ngay, source ORDER BY ngay, source")
print("\nKRC Schedule:")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]}): {r[2]} rows")

# Transfer items today
cur.execute("SELECT DATE(created_at) d, COUNT(1) FROM __cdc_kfm_kf_inventories_kf_transfer_items WHERE created_at >= '2026-05-06' GROUP BY d ORDER BY d")
print("\nTransfer Items (last 3 days):")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} rows")

# Trips today
cur.execute("SELECT DATE(created_at) d, COUNT(1) FROM __cdc_kfm_kf_inventories_kf_trips WHERE created_at >= '2026-05-06' GROUP BY d ORDER BY d")
print("\nTrips (last 3 days):")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} rows")

# Latest timestamps
cur.execute("SELECT MAX(created_at) FROM __cdc_kfm_kf_inventories_kf_transfer_items")
print(f"\nLatest transfer: {cur.fetchone()[0]}")

cur.execute("SELECT MAX(created_at) FROM __cdc_kfm_kf_inventories_kf_trips")
print(f"Latest trip: {cur.fetchone()[0]}")

cur.execute("SELECT MAX(updated_at) FROM krc_dashboard_delivery_schedule")
print(f"Latest KRC schedule update: {cur.fetchone()[0]}")

conn.close()

# ClickHouse
print("\n=== ClickHouse Data Freshness ===")
with open('config/mcp_clickhouse.json') as f:
    ch = json.load(f)
def q(sql):
    r = requests.get(ch['base_url'], params={**ch['params'], 'query': sql}, timeout=10)
    return r.text.strip()

print(f"kf_product_static: {q('SELECT count() FROM kf_product_static')} rows")
print(f"kf_branch_location (active): {q('SELECT count() FROM kf_branch_location WHERE branch_status = 1')} rows")
print(f"kf_transfer_mart (last 3d): {q('SELECT max(transfer_date), count() FROM kf_transfer_mart WHERE transfer_date >= today() - 3 FORMAT TabSeparated')}")

