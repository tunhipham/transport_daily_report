# -*- coding: utf-8 -*-
"""
sync_realtime.py — Smart sync: lightweight check → generate → deploy
=====================================================================
Every 15 min (06:00-22:00):
  1. Lightweight DB check: COUNT(*) for today (~1s)
  2. Compare with last known count → SKIP if unchanged
  3. If changed: full generate → hash check → deploy

This avoids querying 75K+ rows every 15 min.

Usage:
    python script/data_pipeline/sync_realtime.py              # Run once
    python script/data_pipeline/sync_realtime.py --force       # Force full generate
    python script/data_pipeline/sync_realtime.py --dry-run     # Preview only
"""
import os, sys, json, hashlib, subprocess, time
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HISTORY_FILE = os.path.join(BASE, "output", "state", "history.json")
STATE_FILE = os.path.join(BASE, "output", "state", ".sync_state.json")
LOCK_DIR = os.path.join(BASE, "output", "state", "silver")
LOG_DIR = os.path.join(BASE, "output", "logs")


def get_today_str():
    return datetime.now().strftime("%d/%m/%Y")


def get_today_iso():
    return datetime.now().strftime("%Y-%m-%d")


# ── State management (counts + hash) ──

def load_state():
    """Load last known DB counts + deploy hash."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── Lightweight DB checks (~1s each) ──

def check_transfer_fingerprint(date_iso):
    """Quick fingerprint from ClickHouse: COUNT + MAX(updated_at) + SUM(quantity).
    Catches INSERTs, DELETEs, AND UPDATEs (status changes, quantity edits).
    """
    try:
        from data_pipeline.config import load_clickhouse_config
        import requests

        cfg = load_clickhouse_config()
        params = {"user": cfg["user"], "password": cfg["password"], "database": cfg["database"]}
        sql = (
            f"SELECT COUNT(*), MAX(raw_created_at), SUM(transfer_quantity) "
            f"FROM kf_transfer_mart "
            f"WHERE toDate(transfer_date) = '{date_iso}' AND deleted = 0 AND status != 6"
        )
        r = requests.get(cfg["base_url"], params={**params, "query": sql}, timeout=15)
        r.raise_for_status()
        # Returns "count\tmax_updated\tsum_qty\n"
        parts = r.text.strip().split("\t")
        return f"{parts[0]}|{parts[1]}|{parts[2]}"  # e.g. "89215|2026-05-19 10:30:00|1234567"
    except Exception as e:
        print(f"    ⚠ Transfer check failed: {e}")
        return "ERR"  # Unknown → force full check


def check_schedule_fingerprint(date_iso):
    """Quick fingerprint from StarRocks: COUNT + MAX(updated_at)."""
    try:
        from data_pipeline.config import load_starrocks_config
        import pymysql

        sr = load_starrocks_config()
        conn = pymysql.connect(
            host=sr["host"], port=sr["port"], user=sr["user"],
            password=sr["password"], database=sr["database"],
            charset="utf8mb4", connect_timeout=10, read_timeout=10,
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), MAX(updated_at) FROM krc_dashboard_delivery_schedule WHERE ngay = %s",
                (date_iso,)
            )
            row = cur.fetchone()
        conn.close()
        return f"{row[0]}|{row[1]}"  # e.g. "753|2026-05-19 08:30:00"
    except Exception as e:
        print(f"    ⚠ Schedule check failed: {e}")
        return "ERR"


# ── Lock ──

def is_locked(date_str):
    parts = date_str.split("/")
    date_tag = f"{parts[0]}{parts[1]}{parts[2]}"
    lock_file = os.path.join(LOCK_DIR, date_tag, "lock.json")
    return os.path.exists(lock_file)


def create_lock(date_str, history_hash):
    parts = date_str.split("/")
    date_tag = f"{parts[0]}{parts[1]}{parts[2]}"
    lock_dir = os.path.join(LOCK_DIR, date_tag)
    os.makedirs(lock_dir, exist_ok=True)
    lock_file = os.path.join(lock_dir, "lock.json")
    lock_data = {
        "locked_at": datetime.now().isoformat(),
        "date": date_str,
        "hash": history_hash,
        "reason": "cutoff_8am",
    }
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, ensure_ascii=False, indent=2)
    return lock_file


# ── Logging ──

def log_sync(status, details=""):
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"sync_{today}.log")
    ts = datetime.now().strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {status} {details}\n")


# ── Generate + Deploy ──

def compute_history_hash():
    if not os.path.exists(HISTORY_FILE):
        return None
    with open(HISTORY_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        return None
    last = data[-1]
    raw = json.dumps(last, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()


def run_generate(date_str):
    script = os.path.join(BASE, "script", "domains", "daily", "generate.py")
    cmd = [sys.executable, script, "--date", date_str, "--source", "auto"]
    print(f"  🏃 generate.py --date {date_str} --source auto")
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  ❌ generate.py failed (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-3:]:
                print(f"    {line}")
        return False
    return True


def run_deploy(domain="daily"):
    script = os.path.join(BASE, "script", "dashboard", "deploy.py")
    cmd = [sys.executable, script, "--domain", domain]
    print(f"  🚀 deploy.py --domain {domain}")
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ❌ deploy.py failed")
        return False
    return True


# ── Main ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Smart sync — lightweight check → generate → deploy")
    parser.add_argument("--force", action="store_true", help="Force full generate (skip count check)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--lock", action="store_true", help="Force lock today")
    args = parser.parse_args()

    now = datetime.now()
    today = get_today_str()
    today_iso = get_today_iso()
    hour = now.hour

    print(f"{'='*60}")
    print(f"  🔄 Sync Realtime — {now.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}")

    # Time window
    if hour < 6 or hour >= 22:
        print(f"  ⏸ Outside sync window (06:00-22:00)")
        log_sync("SKIP", "outside window")
        return

    # Lock check
    if is_locked(today) and not args.force:
        print(f"  🔒 Today is LOCKED. Use --force to override.")
        log_sync("SKIP", "locked")
        return

    # ── Process lock (prevent concurrent writes) ──
    lock_file = os.path.join(BASE, "output", "state", ".sync.lock")
    if os.path.exists(lock_file):
        # Check if lock is stale (>10 min = probably crashed)
        lock_age = time.time() - os.path.getmtime(lock_file)
        if lock_age < 600:
            print(f"  🔒 Another sync is running (lock age: {lock_age:.0f}s). Skipping.")
            log_sync("SKIP", f"locked by another process ({lock_age:.0f}s)")
            return
        else:
            print(f"  ⚠ Stale lock detected ({lock_age:.0f}s). Removing.")
            os.remove(lock_file)

    # Acquire lock
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        _run_sync(args, today, today_iso, hour)
    finally:
        # Release lock
        if os.path.exists(lock_file):
            os.remove(lock_file)


def _run_sync(args, today, today_iso, hour):
    now = datetime.now()

    # ── Step 1: Lightweight DB fingerprint check (~1s total) ──
    state = load_state()
    last_transfer = state.get("transfer_fp", "")
    last_schedule = state.get("schedule_fp", "")
    last_date = state.get("date", "")
    last_deploy_hash = state.get("deploy_hash", "")

    # Reset if date changed
    if last_date != today_iso:
        last_transfer = ""
        last_schedule = ""
        last_deploy_hash = ""
        print(f"  📅 New day — resetting state")

    print(f"  🔍 Lightweight DB fingerprint check...")
    t0 = time.time()
    cur_transfer = check_transfer_fingerprint(today_iso)
    cur_schedule = check_schedule_fingerprint(today_iso)
    check_time = time.time() - t0

    print(f"    Transfer: {last_transfer or 'none'} → {cur_transfer}")
    print(f"    Schedule: {last_schedule or 'none'} → {cur_schedule}")
    print(f"    Check time: {check_time:.1f}s")

    # Both DB down → skip (generate would also fail)
    if cur_transfer == "ERR" and cur_schedule == "ERR":
        print(f"  ❌ Both DBs unreachable — skipping (will retry next cycle)")
        log_sync("ERR", f"both DBs down ({check_time:.1f}s)")
        return

    data_changed = (
        args.force or
        cur_transfer != last_transfer or
        cur_schedule != last_schedule
    )

    # One DB error but the other changed → still run (generate has fallback)
    if not data_changed and (cur_transfer == "ERR" or cur_schedule == "ERR"):
        # DB error but no change detected on working DB → skip
        print(f"  ⚠ Partial DB error, working DB unchanged — skipping")
        log_sync("SKIP", f"partial ERR, no change ({check_time:.1f}s)")
        return

    if not data_changed:
        print(f"  ⏭ No change — skipping generate")
        log_sync("SKIP", f"unchanged ({check_time:.1f}s)")
        return

    print(f"  ✨ Data changed — running full generate")

    if args.dry_run:
        print(f"  [DRY RUN] — Would generate + deploy")
        log_sync("DRY", f"changed")
        return

    # ── Step 2: Full generate ──
    t1 = time.time()
    ok = run_generate(today)
    gen_time = time.time() - t1

    if not ok:
        log_sync("FAIL", f"generate failed ({gen_time:.1f}s)")
        sys.exit(1)

    print(f"  ⏱ Generate: {gen_time:.1f}s")

    # ── Step 3: Hash check → deploy if output changed ──
    new_hash = compute_history_hash()

    if new_hash == last_deploy_hash and not args.force:
        print(f"  ⏭ Output unchanged — skipping deploy")
        state.update({
            "date": today_iso,
            "transfer_fp": cur_transfer,
            "schedule_fp": cur_schedule,
            "deploy_hash": last_deploy_hash,
            "last_check": now.isoformat(),
        })
        save_state(state)
        log_sync("SKIP", f"output same ({gen_time:.1f}s)")
        return

    # Deploy
    deploy_ok = run_deploy("daily")

    # Save state
    state.update({
        "date": today_iso,
        "transfer_fp": cur_transfer,
        "schedule_fp": cur_schedule,
        "deploy_hash": new_hash if deploy_ok else last_deploy_hash,
        "last_check": now.isoformat(),
        "last_deploy": now.isoformat() if deploy_ok else state.get("last_deploy"),
    })
    save_state(state)

    if deploy_ok:
        print(f"  ✅ Deploy SUCCESS")
        log_sync("OK", f"T:{cur_transfer} S:{cur_schedule} gen:{gen_time:.1f}s")
    else:
        log_sync("FAIL", f"deploy failed")
        sys.exit(1)

    # Lock at 8AM cutoff
    if args.lock or (hour >= 8 and not is_locked(today)):
        lock_path = create_lock(today, new_hash)
        print(f"  🔒 Locked: {lock_path}")
        log_sync("LOCK", today)

    print(f"\n{'='*60}")
    print(f"  ✅ Done — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
