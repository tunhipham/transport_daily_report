# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(r'g:\My Drive\DOCS\transport_daily_report', 'script'))
from data_pipeline.config import load_starrocks_config
import pymysql

sr = load_starrocks_config()
conn = pymysql.connect(host=sr['host'], port=sr['port'], user=sr['user'],
    password=sr['password'], database=sr['database'], charset='utf8mb4',
    connect_timeout=10, read_timeout=10)

with conn.cursor() as cur:
    # Schedule for today
    cur.execute(
        "SELECT source, COUNT(source) as cnt, COUNT(DISTINCT diem_den) as sthi, "
        "COUNT(DISTINCT tuyen) as xe "
        "FROM krc_dashboard_delivery_schedule "
        "WHERE ngay = '20/05/2026' GROUP BY source ORDER BY source"
    )
    rows = cur.fetchall()
    print('=== Schedule today (20/05/2026) ===')
    for src, cnt, sthi, xe in rows:
        print(f'  {src}: {cnt} rows, {sthi} STHI, {xe} xe')
    if not rows:
        print('  (no data)')

    # Fingerprint — same as sync_realtime.py
    cur.execute(
        "SELECT COUNT(ngay), MAX(updated_at) "
        "FROM krc_dashboard_delivery_schedule WHERE ngay = '2026-05-20'"
    )
    r = cur.fetchone()
    print(f'\n  Fingerprint (ISO): {r[0]}|{r[1]}')

    cur.execute(
        "SELECT COUNT(ngay), MAX(updated_at) "
        "FROM krc_dashboard_delivery_schedule WHERE ngay = '20/05/2026'"
    )
    r2 = cur.fetchone()
    print(f'  Fingerprint (VN):  {r2[0]}|{r2[1]}')

conn.close()

# Check what format sync_realtime.py uses
print('\n=== sync_realtime.py uses ===')
print('  check_schedule_fingerprint() queries:')
print('  WHERE ngay = %s with date_iso (YYYY-MM-DD)')
print(f'  Today ISO: 2026-05-20')
