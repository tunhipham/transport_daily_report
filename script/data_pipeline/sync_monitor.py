# -*- coding: utf-8 -*-
"""
sync_monitor.py — Quick health dashboard for realtime sync pipeline.

Usage:
    python script/data_pipeline/sync_monitor.py          # Today status
    python script/data_pipeline/sync_monitor.py --days 3  # Last 3 days
"""
import os, sys, json, argparse
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOG_DIR = os.path.join(BASE, "output", "logs")
STATE_FILE = os.path.join(BASE, "output", "state", ".sync_state.json")
HISTORY_FILE = os.path.join(BASE, "output", "state", "history.json")
CAPACITY_FILE = os.path.join(BASE, "docs", "data", "capacity_forecast.json")
LOCK_DIR = os.path.join(BASE, "output", "state", "silver")


def load_json(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return None


def show_status(days=1):
    now = datetime.now()
    print(f"\n{'═'*60}")
    print(f"  🔄 Sync Realtime Monitor — {now.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'═'*60}")

    # ── 1. Sync State ──
    print(f"\n{'─'*60}")
    print(f"  1. SYNC STATE")
    print(f"{'─'*60}")
    state = load_json(STATE_FILE)
    if state:
        last_check = state.get('last_check', 'never')
        if last_check != 'never':
            try:
                lc = datetime.fromisoformat(last_check)
                age = now - lc
                age_str = f"{int(age.total_seconds()//60)} phút trước"
            except:
                age_str = last_check
        else:
            age_str = 'never'

        print(f"  Date:         {state.get('date', '?')}")
        print(f"  Last check:   {age_str}")
        print(f"  Transfer FP:  {state.get('transfer_fp', state.get('transfer_count', '?'))}")
        print(f"  Schedule FP:  {state.get('schedule_fp', state.get('schedule_count', '?'))}")
        print(f"  Deploy hash:  {state.get('deploy_hash', '?')[:16]}...")
    else:
        print(f"  ⚠ No state file")

    # ── 2. Sync Logs ──
    print(f"\n{'─'*60}")
    print(f"  2. SYNC LOG (last {days} day(s))")
    print(f"{'─'*60}")
    for d in range(days):
        dt = now - timedelta(days=d)
        log_file = os.path.join(LOG_DIR, f"sync_{dt.strftime('%Y-%m-%d')}.log")
        if os.path.exists(log_file):
            print(f"\n  📅 {dt.strftime('%d/%m/%Y')}:")
            with open(log_file, encoding='utf-8') as f:
                lines = f.readlines()

            # Summary
            ok_count = sum(1 for l in lines if '] OK ' in l)
            skip_count = sum(1 for l in lines if 'SKIP' in l)
            err_count = sum(1 for l in lines if 'ERR' in l or 'FAIL' in l)
            lock_count = sum(1 for l in lines if 'LOCK' in l)

            print(f"     Entries: {len(lines)} | OK: {ok_count} | SKIP: {skip_count} | LOCK: {lock_count} | ERR: {err_count}")

            # Show all lines
            for line in lines:
                line = line.rstrip()
                # Color coding via emoji
                if '] OK ' in line:
                    print(f"     ✅ {line}")
                elif 'SKIP' in line:
                    print(f"     ⏭️  {line}")
                elif 'LOCK' in line:
                    print(f"     🔒 {line}")
                elif 'ERR' in line or 'FAIL' in line:
                    print(f"     ❌ {line}")
                elif 'DRY' in line:
                    print(f"     🧪 {line}")
                else:
                    print(f"     ▪️  {line}")
        else:
            print(f"\n  📅 {dt.strftime('%d/%m/%Y')}: no log file")

    # ── 3. Lock Status ──
    print(f"\n{'─'*60}")
    print(f"  3. LOCK STATUS")
    print(f"{'─'*60}")
    today_tag = now.strftime('%d%m%Y')
    lock_file = os.path.join(LOCK_DIR, today_tag, 'lock.json')
    if os.path.exists(lock_file):
        lock_data = load_json(lock_file)
        locked_at = lock_data.get('locked_at', '?') if lock_data else '?'
        print(f"  Today ({today_tag}): 🔒 LOCKED at {locked_at}")
    else:
        print(f"  Today ({today_tag}): 🔓 NOT LOCKED")

    # ── 4. History (last generate output) ──
    print(f"\n{'─'*60}")
    print(f"  4. LAST GENERATE OUTPUT")
    print(f"{'─'*60}")
    hist = load_json(HISTORY_FILE)
    if hist and len(hist) > 0:
        last = hist[-1]
        mtime = os.path.getmtime(HISTORY_FILE)
        print(f"  Date:     {last.get('date', '?')}")
        print(f"  Modified: {datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')}")
        khos = last.get('khos', {})
        print(f"  Branches: {len(khos)}")
        for name, data in khos.items():
            tons = data.get('san_luong_tan', 0)
            items = data.get('sl_items', 0)
            xe = data.get('sl_xe', 0)
            sthi = data.get('sl_sthi', 0)
            print(f"    {name:<10} {tons:>7.1f}T | {items:>10,.0f} items | {xe:>3} xe | {sthi:>4} STHI")

    # ── 5. Capacity Forecast ──
    print(f"\n{'─'*60}")
    print(f"  5. CAPACITY FORECAST")
    print(f"{'─'*60}")
    cap = load_json(CAPACITY_FILE)
    if cap:
        print(f"  Updated: {cap.get('_updated', '?')}")
        today_vn = now.strftime('%d/%m/%Y')

        krc_today = [d for d in cap.get('krc', {}).get('data', []) if d['date'] == today_vn]
        ksl_today = [d for d in cap.get('ksl', {}).get('data', []) if d['date'] == today_vn]

        if krc_today:
            d = krc_today[0]
            bar = '█' * int(d['pct_capacity'] / 5) + '░' * (20 - int(d['pct_capacity'] / 5))
            print(f"  KRC today: {d['tons']:>6.1f}T / {cap['krc']['benchmark_tons']}T  [{bar}] {d['pct_capacity']}%")
        else:
            print(f"  KRC today: ⚠ NO DATA")

        if ksl_today:
            d = ksl_today[0]
            bar = '█' * int(d['pct_capacity'] / 5) + '░' * (20 - int(d['pct_capacity'] / 5))
            print(f"  KSL today: {d['items']:>7,} / {cap['ksl']['benchmark_items']:,}  [{bar}] {d['pct_capacity']}%")
        else:
            print(f"  KSL today: ⚠ NO DATA")

    # ── 6. Task Scheduler ──
    print(f"\n{'─'*60}")
    print(f"  6. TASK SCHEDULER")
    print(f"{'─'*60}")
    import subprocess
    try:
        r = subprocess.run(
            ['schtasks', '/Query', '/TN', '\\KFM\\SyncRealtime', '/FO', 'LIST', '/V'],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.split('\n'):
            line = line.strip()
            if any(k in line for k in ['Status:', 'Last Run', 'Last Result', 'Next Run', 'Task To Run']):
                # Highlight result
                if 'Last Result' in line:
                    code = line.split(':')[-1].strip()
                    tag = '✅' if code == '0' else '❌'
                    print(f"  {tag} {line}")
                else:
                    print(f"     {line}")
    except Exception as e:
        print(f"  ⚠ Cannot query: {e}")

    print(f"\n{'═'*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=1, help='Number of days of logs to show')
    args = parser.parse_args()
    show_status(args.days)
