import requests
import json
import pymysql
import pandas as pd
import os
import codecs
from datetime import datetime

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

START_DATE = '2026-05-18 00:00:00'
END_DATE = '2026-05-24 23:59:59'

print(f"Exporting data from {START_DATE} to {END_DATE}")

with pd.ExcelWriter('output/trip_data_18_to_24_05.xlsx', engine='openpyxl') as writer:
    
    # ================= ClickHouse =================
    print("Fetching ClickHouse data...")
    try:
        url = "http://103.140.248.114:32015/"
        auth = ("scm_lam", "xukco1-roghaB-fuqfum")
        
        # kf_trip_locations_items
        ch_query = f"""
        SELECT *
        FROM kdb.kf_trip_locations_items
        WHERE t_departure >= '{START_DATE}' AND t_departure <= '{END_DATE}'
        LIMIT 10000
        """
        response = requests.post(url, auth=auth, params={"database": "kdb", "query": ch_query + " FORMAT JSON"})
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                df_ch = pd.DataFrame(data['data'])
                # Convert list/dict columns to strings so Excel doesn't complain
                for col in df_ch.columns:
                    df_ch[col] = df_ch[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
                df_ch.to_excel(writer, sheet_name='CH_kf_trip_loc_items', index=False)
                print(f"  - kf_trip_locations_items: {len(df_ch)} rows")
            else:
                print("  - kf_trip_locations_items: 0 rows")
        else:
            print(f"ClickHouse Error: {response.text}")
    except Exception as e:
        print(f"ClickHouse exception: {e}")

    # ================= StarRocks =================
    print("\nFetching StarRocks data...")
    try:
        conn = pymysql.connect(
            host="103.147.122.56",
            port=9030,
            user="kfm_scm_lam_nguyen",
            password="QPYZfjWWhJcHNi5ab5Au",
            database="kfm_scm"
        )
        
        sr_queries = {
            "SR_kf_trips": f"SELECT * FROM __cdc_kfm_kf_inventories_kf_trips WHERE t_departure >= '{START_DATE}' AND t_departure <= '{END_DATE}' LIMIT 10000",
            "SR_kf_trips_loc_items": f"SELECT * FROM __cdc_kfm_kf_inventories_kf_trips_locations_items WHERE updated_at >= '{START_DATE}' AND updated_at <= '{END_DATE}' LIMIT 10000",
            "SR_krc_deliv_sched": f"SELECT * FROM krc_dashboard_delivery_schedule WHERE ngay >= '2026-05-18' AND ngay <= '2026-05-24' LIMIT 10000",
            "SR_krc_deliv_receipts": f"SELECT * FROM krc_dashboard_delivery_receipts WHERE ngay_chuyen >= '2026-05-18' AND ngay_chuyen <= '2026-05-24' LIMIT 10000"
        }
        
        for sheet_name, query in sr_queries.items():
            try:
                df_sr = pd.read_sql(query, conn)
                if not df_sr.empty:
                    # Convert timezone-aware datetimes to timezone-naive datetimes for Excel
                    for col in df_sr.columns:
                        if pd.api.types.is_datetime64_any_dtype(df_sr[col]):
                            df_sr[col] = df_sr[col].dt.tz_localize(None)
                        else:
                            df_sr[col] = df_sr[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
                            
                    df_sr.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"  - {sheet_name}: {len(df_sr)} rows")
                else:
                    print(f"  - {sheet_name}: 0 rows")
            except Exception as inner_e:
                print(f"  - Error querying {sheet_name}: {inner_e}")
                
        conn.close()
    except Exception as e:
        print(f"StarRocks exception: {e}")

print("\nDone! Exported to output/trip_data_18_to_24_05.xlsx")
