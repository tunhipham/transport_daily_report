import requests
import pymysql
import pandas as pd
import os
import json
import ast

os.makedirs('output', exist_ok=True)

START_DATE = '2026-05-18 00:00:00'
END_DATE = '2026-05-24 23:59:59'

print(f"Exporting data from {START_DATE} to {END_DATE} with locations...")

with pd.ExcelWriter('output/trip_data_18_to_24_05.xlsx', engine='openpyxl') as writer:
    
    # 1. Get Branch Dictionary from ClickHouse
    url = "http://103.140.248.114:32015/"
    auth = ("scm_lam", "xukco1-roghaB-fuqfum")
    print("Fetching branch dictionary...")
    branch_dict = {}
    try:
        q_dict = "SELECT id, branch_code, branch_name FROM kdb.kf_branch_location FORMAT JSON"
        res_dict = requests.post(url, auth=auth, params={"database": "kdb", "query": q_dict})
        if res_dict.status_code == 200:
            for row in res_dict.json()['data']:
                branch_dict[row['id']] = row['branch_name']
        else:
            print("Failed to get branch dictionary", res_dict.text)
    except Exception as e:
        print("Error fetching branch dictionary:", e)

    # 2. Fetch ClickHouse Data (Joined with branch)
    print("Fetching ClickHouse data...")
    try:
        ch_query = f"""
        SELECT t.*, b.branch_code AS tl_branch_code, b.branch_name AS tl_branch_name
        FROM kdb.kf_trip_locations_items t
        LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
        WHERE t.t_departure >= '{START_DATE}' AND t.t_departure <= '{END_DATE}'
        LIMIT 10000
        """
        response = requests.post(url, auth=auth, params={"database": "kdb", "query": ch_query + " FORMAT JSON"})
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                df_ch = pd.DataFrame(data['data'])
                # Move branch_name to the front for easier reading
                cols = df_ch.columns.tolist()
                if 'tl_branch_name' in cols:
                    cols.insert(2, cols.pop(cols.index('tl_branch_name')))
                    df_ch = df_ch[cols]
                
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

    # 3. Fetch StarRocks Data
    print("Fetching StarRocks data...")
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
        
        def map_location_array(loc_str):
            if not loc_str or pd.isna(loc_str): return loc_str
            try:
                # loc_str might be stringified JSON array
                loc_list = json.loads(loc_str)
                names = [branch_dict.get(loc_id, loc_id) for loc_id in loc_list]
                return ", ".join(names)
            except:
                return loc_str
                
        def map_single_location(loc_id):
            if not loc_id or pd.isna(loc_id): return loc_id
            return branch_dict.get(str(loc_id), loc_id)

        for sheet_name, query in sr_queries.items():
            try:
                df_sr = pd.read_sql(query, conn)
                if not df_sr.empty:
                    # Map locations
                    if 't_locations' in df_sr.columns:
                        df_sr['t_locations_names'] = df_sr['t_locations'].apply(map_location_array)
                        # Move to front
                        cols = df_sr.columns.tolist()
                        cols.insert(2, cols.pop(cols.index('t_locations_names')))
                        df_sr = df_sr[cols]
                    
                    if 'tl_id' in df_sr.columns:
                        df_sr['tl_name'] = df_sr['tl_id'].apply(map_single_location)
                        cols = df_sr.columns.tolist()
                        cols.insert(2, cols.pop(cols.index('tl_name')))
                        df_sr = df_sr[cols]

                    # Convert types
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

print("Done!")
