# Check DB data for user's questions
import sys, os
sys.path.insert(0, os.path.join(r"G:\My Drive\DOCS\transport_daily_report", "script"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pymysql, requests

conn = pymysql.connect(host="103.147.122.56", port=9030, user="kfm_scm_lam_nguyen",
                       password="QPYZfjWWhJcHNi5ab5Au", database="kfm_scm",
                       charset="utf8mb4", connect_timeout=10)
cur = conn.cursor()

# Q1: KRC schedule — có kho nào khác không?
print("=" * 80)
print("Q1: krc_dashboard_delivery_schedule — source (kho) nào có?")
print("=" * 80)
cur.execute("SELECT source, COUNT(*) as cnt FROM krc_dashboard_delivery_schedule WHERE ngay = '18/05/2026' GROUP BY source")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} rows")

# Q2: ClickHouse kf_transfer_mart — sample data có barcode?
print()
print("=" * 80)
print("Q2: ClickHouse kf_transfer_mart — sample 5 rows")
print("=" * 80)
resp = requests.post(
    "http://103.140.248.114:32015/",
    params={
        "user": "scm_lam",
        "password": "xukco1-roghaB-fuqfum",
        "database": "kdb",
        "query": "SELECT product_id, from_branch_id, to_branch_id, transfer_quantity, received_quantity, transfer_date, type FROM kf_transfer_mart WHERE toDate(transfer_date) = '2026-05-18' LIMIT 5 FORMAT JSON"
    },
    timeout=15,
)
data = resp.json()
for r in data.get("data", []):
    print(f"  product_id={r['product_id'][:20]:20s} | from={r['from_branch_id'][:20]:20s} | to={r['to_branch_id'][:20]:20s} | qty={r['transfer_quantity']} | date={r['transfer_date']}")

# Q2b: How many transfer rows today?
resp2 = requests.post(
    "http://103.140.248.114:32015/",
    params={
        "user": "scm_lam",
        "password": "xukco1-roghaB-fuqfum",
        "database": "kdb",
        "query": "SELECT count() as cnt FROM kf_transfer_mart WHERE toDate(transfer_date) = '2026-05-18' FORMAT JSON"
    },
    timeout=15,
)
cnt = resp2.json().get("data", [{}])[0].get("cnt", 0)
print(f"\n  Total rows today: {cnt}")

# Q2c: Can we get barcode from product_id? Check kf_product_static
print()
print("=" * 80)
print("Q2c: kf_product_static — does it have barcode?")
print("=" * 80)
resp3 = requests.post(
    "http://103.140.248.114:32015/",
    params={
        "user": "scm_lam",
        "password": "xukco1-roghaB-fuqfum",
        "database": "kdb",
        "query": "DESCRIBE kf_product_static FORMAT TabSeparated"
    },
    timeout=15,
)
for line in resp3.text.strip().split("\n")[:15]:
    col = line.split("\t")[0]
    typ = line.split("\t")[1] if "\t" in line else ""
    print(f"  {col:30s} {typ}")

conn.close()
