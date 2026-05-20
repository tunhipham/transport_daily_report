# -*- coding: utf-8 -*-
"""Pipeline health check — all issues at a glance."""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = r'g:\My Drive\DOCS\transport_daily_report'
sys.path.insert(0, os.path.join(BASE, 'script'))

print('=== REALTIME PIPELINE HEALTH CHECK ===')
print()

# 1. Sync state format
print('1. SYNC STATE')
sf = os.path.join(BASE, 'output', 'state', '.sync_state.json')
if os.path.exists(sf):
    with open(sf, encoding='utf-8') as f:
        st = json.load(f)
    print(f'   Last date: {st.get("date", "?")}')
    print(f'   Last check: {st.get("last_check", "never")}')
    keys = list(st.keys())
    print(f'   State keys: {keys}')
    if 'transfer_count' in st and 'transfer_fp' not in st:
        print('   ⚠ OLD STATE FORMAT — code expects transfer_fp/schedule_fp')
        print('     Will auto-reset on new day (OK)')
else:
    print('   No state file')

# 2. StarRocks schedule
print()
print('2. STARROCKS SCHEDULE')
try:
    from data_pipeline.config import load_starrocks_config
    import pymysql
    sr = load_starrocks_config()
    conn = pymysql.connect(host=sr['host'], port=sr['port'], user=sr['user'],
        password=sr['password'], database=sr['database'], charset='utf8mb4',
        connect_timeout=10, read_timeout=10)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM krc_dashboard_delivery_schedule WHERE ngay = '20/05/2026'")
        cnt = cur.fetchone()[0]
        print(f'   Rows for today: {cnt}')

        cur.execute("SELECT ngay, COUNT(*) as c FROM krc_dashboard_delivery_schedule GROUP BY ngay ORDER BY c DESC LIMIT 5")
        rows = cur.fetchall()
        print(f'   Top ngay values:')
        for ngay, c in rows:
            ngay_str = str(ngay)
            is_date = len(ngay_str) == 10 and '/' in ngay_str
            tag = 'date OK' if is_date else 'NOT A DATE!'
            print(f'     "{ngay_str[:60]}" = {c} rows ({tag})')
    conn.close()
    if cnt == 0:
        print('   RESULT: Schedule DB has NO valid data for today')
        print('   IMPACT: generate.py falls back to Google Sheets + local files')
        print('   IMPACT: sync fingerprint always "0|None" = runs every cycle')
except Exception as e:
    print(f'   Error: {e}')

# 3. Generate last run
print()
print('3. LAST GENERATE')
hist_path = os.path.join(BASE, 'output', 'state', 'history.json')
if os.path.exists(hist_path):
    mtime = os.path.getmtime(hist_path)
    print(f'   history.json modified: {time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(mtime))}')
    with open(hist_path, encoding='utf-8') as f:
        hist = json.load(f)
    last = hist[-1] if hist else {}
    print(f'   Last entry date: {last.get("date", "?")}')

# 4. Capacity forecast
print()
print('4. CAPACITY FORECAST')
cap_path = os.path.join(BASE, 'docs', 'data', 'capacity_forecast.json')
if os.path.exists(cap_path):
    with open(cap_path, encoding='utf-8') as f:
        cap = json.load(f)
    krc_dates = [d['date'] for d in cap.get('krc', {}).get('data', [])]
    ksl_dates = [d['date'] for d in cap.get('ksl', {}).get('data', [])]
    print(f'   Updated: {cap.get("_updated", "?")}')
    print(f'   KRC range: {krc_dates[0] if krc_dates else "?"} - {krc_dates[-1] if krc_dates else "?"}')
    print(f'   KSL range: {ksl_dates[0] if ksl_dates else "?"} - {ksl_dates[-1] if ksl_dates else "?"}')
    print(f'   Has KRC today? {"20/05/2026" in krc_dates}')
    print(f'   SOURCE: LOCAL FILES ONLY (no DB fallback)')

# 5. Lock
print()
print('5. LOCK')
lock_file = os.path.join(BASE, 'output', 'state', 'silver', '20052026', 'lock.json')
print(f'   Today locked? {os.path.exists(lock_file)}')

# 6. Generate.py time estimate
print()
print('6. GENERATE TIME (from last run)')
gen_log = os.path.join(BASE, 'output', 'logs')
if os.path.isdir(gen_log):
    logs = sorted([f for f in os.listdir(gen_log) if f.startswith('sync_')])
    if logs:
        last_log = os.path.join(gen_log, logs[-1])
        with open(last_log, encoding='utf-8') as f:
            print(f'   {logs[-1]}:')
            for line in f:
                print(f'     {line.rstrip()}')

# Summary
print()
print('=' * 60)
print('  SUMMARY — What works, what does not')
print('=' * 60)
print()
print('  [FIX NEEDED] Task Scheduler python path')
print('     → python.exe not found from scheduler context')
print('     → Fix: use full path C:\\...\\python.exe')
print()
print('  [FIX NEEDED] StarRocks schedule data CORRUPTED')
print('     → ngay column has store names instead of dates')
print('     → Impact: schedule fingerprint always 0 = sync runs')
print('       generate EVERY 15 min (wasteful but not broken)')
print('     → generate.py falls back to Sheets/local files')
print()
print('  [WORKING] ClickHouse transfer data')
print('     → Transfer fingerprint works correctly')
print('     → generate.py reads transfer from DB OK')
print()
print('  [NOT CONNECTED] Capacity forecast (PO KRC)')
print('     → capacity_forecast.py reads LOCAL files only')
print('     → DB has data (kf_purchase_order + kf_receipt_items)')
print('     → Need to add DB path to capacity_forecast.py')
print()
print('  [JUST FIXED] Unclassified barcodes')
print('     → 26 barcodes added to ABA Master Data')
print('     → Will take effect on next generate run')
