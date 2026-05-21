# -*- coding: utf-8 -*-
"""Deep check: does any trip table have arrival_time per destination?"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(r'g:\My Drive\DOCS\transport_daily_report', 'script'))
from data_pipeline.config import load_starrocks_config
import pymysql

cfg = load_starrocks_config()
conn = pymysql.connect(host=cfg['host'], port=cfg['port'], user=cfg['user'],
    password=cfg['password'], database=cfg['database'], charset='utf8mb4',
    connect_timeout=30, read_timeout=120)

with conn.cursor() as cur:
    # 1. ALL tables in DB
    cur.execute('SHOW TABLES')
    all_tables = [t[0] for t in cur.fetchall()]
    print(f"Total tables: {len(all_tables)}")
    
    # 2. Find ANY table/column with 'arrival' or 'den' or 'cua_hang' or 'location'
    print("\n=== Tables with trip/location/arrival keywords ===")
    for tbl in all_tables:
        if any(kw in tbl.lower() for kw in ['trip', 'location', 'chuyen', 'arrival']):
            cur.execute(f'DESCRIBE {tbl}')
            cols = cur.fetchall()
            col_names = [c[0] for c in cols]
            print(f"\n  {tbl} ({len(col_names)} cols)")
            for c in cols:
                # Highlight interesting columns
                cn = c[0].lower()
                if any(kw in cn for kw in ['time', 'arrival', 'complet', 'status', 'location', 'store', 'dest', 'name']):
                    print(f"    ★ {c[0]:<45} {c[1]}")
                else:
                    print(f"      {c[0]:<45} {c[1]}")

    # 3. Check trip_locations for hidden time data
    print("\n\n=== trip_locations: sample with all fields ===")
    tbl = '__cdc_kfm_ec9d24ab_c49f2956_L2___trip_locations'
    cur.execute(f'SELECT * FROM {tbl} LIMIT 5')
    cols_desc = cur.description
    col_names = [d[0] for d in cols_desc]
    rows = cur.fetchall()
    for i, row in enumerate(rows):
        print(f"\n  --- Row {i+1} ---")
        for cn, val in zip(col_names, row):
            print(f"    {cn:<45} = {str(val)[:100]}")

    # 4. Check kf_trips main table for per-location JSON
    print("\n\n=== kf_trips: check t_locations field (JSON?) ===")
    tbl2 = '__cdc_kfm_kf_inventories_kf_trips'
    cur.execute(f"SELECT t_code, t_locations, t_trip_location_ids FROM {tbl2} WHERE t_departure >= '2026-05-19' LIMIT 2")
    cols_desc2 = cur.description
    col_names2 = [d[0] for d in cols_desc2]
    for row in cur.fetchall():
        print(f"\n  Trip: {row[0]}")
        print(f"    t_locations: {str(row[1])[:200]}")
        print(f"    t_trip_location_ids: {str(row[2])[:200]}")

    # 5. Check if there's a denormalized/joined view we missed
    print("\n\n=== Search ALL columns across ALL tables for 'arrival' ===")
    for tbl in all_tables:
        try:
            cur.execute(f'DESCRIBE {tbl}')
            for c in cur.fetchall():
                if 'arrival' in c[0].lower() or 'den_cua' in c[0].lower() or 'thoi_gian_den' in c[0].lower():
                    print(f"  {tbl}.{c[0]} ({c[1]})")
        except:
            pass

conn.close()
