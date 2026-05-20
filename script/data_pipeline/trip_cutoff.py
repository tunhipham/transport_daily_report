# -*- coding: utf-8 -*-
"""
trip_cutoff.py — T3 09:00 Cutoff: decide incomplete trips → generate report
=============================================================================
Flow:
  1. Query incomplete trips from StarRocks
  2. Write list to temp file, open in Notepad
  3. User edits: keep line = mark as on-time, delete line = exclude
  4. After Notepad closes → read decisions → generate performance report → deploy

Usage:
    python script/data_pipeline/trip_cutoff.py                # Interactive
    python script/data_pipeline/trip_cutoff.py --exclude-all  # Auto-exclude all, no Notepad
    python script/data_pipeline/trip_cutoff.py --dry-run      # Preview only
"""
import os, sys, json, subprocess, argparse
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DECISIONS_DIR = os.path.join(BASE, "output", "state", "trip_decisions")
TEMP_FILE = os.path.join(BASE, "output", "state", "trip_decisions", "_pending.txt")


def get_week_range():
    today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    prev_monday = this_monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6)
    return prev_monday.strftime("%Y-%m-%d"), prev_sunday.strftime("%Y-%m-%d")


def get_week_number():
    today = datetime.now()
    prev_week = today - timedelta(days=7)
    return prev_week.isocalendar()[1]


def query_incomplete_trips(start_date, end_date):
    from data_pipeline.config import load_starrocks_config
    import pymysql

    sr = load_starrocks_config()
    conn = pymysql.connect(
        host=sr["host"], port=sr["port"], user=sr["user"],
        password=sr["password"], database=sr["database"],
        charset="utf8mb4", connect_timeout=30, read_timeout=60,
    )

    trips = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT t_code, CAST(t_status AS INT) as status,
                   DATE_FORMAT(t_departure, '%%Y-%%m-%%d') as dep_date,
                   t_license_number, t_driver_name,
                   t_transfercodes
            FROM __cdc_kfm_kf_inventories_kf_trips
            WHERE DATE(t_departure) BETWEEN %s AND %s
              AND t_status IN (1, 2)
              AND deleted = 0
            ORDER BY t_departure, t_code
        """, (start_date, end_date))

        for row in cur.fetchall():
            code, status, dep, plate, driver, tcodes_raw = row
            tcodes = json.loads(tcodes_raw) if tcodes_raw else []
            status_label = {1: "Tạo mới", 2: "Đang giao"}.get(int(status), str(status))
            trips.append({
                "code": code,
                "status": int(status),
                "status_label": status_label,
                "departure_date": dep,
                "license": plate or "",
                "driver": driver or "",
                "transfer_codes": tcodes,
            })

    conn.close()
    return trips


def write_decision_file(trips, week_num):
    """Write trip list to temp file for user editing."""
    os.makedirs(DECISIONS_DIR, exist_ok=True)

    lines = [
        f"# TRIP CUTOFF — W{week_num}",
        f"# Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"#",
        f"# HƯỚNG DẪN:",
        f"#   - GIỮ dòng = cho trip hoàn thành (on-time)",
        f"#   - XÓA dòng = bỏ trip (exclude from report)",
        f"#   - Save + đóng Notepad → tự generate report",
        f"#",
        f"# Format: TRIP_CODE | NGÀY | TÀI XẾ | PT CODES | STATUS",
        f"# ═══════════════════════════════════════════════════════",
        f"",
    ]

    for t in trips:
        pt_str = ", ".join(t["transfer_codes"][:3])
        if len(t["transfer_codes"]) > 3:
            pt_str += f" +{len(t['transfer_codes'])-3}"
        if not pt_str:
            pt_str = "(no PT)"

        lines.append(
            f"{t['code']} | {t['departure_date']} | {t['driver']} | {pt_str} | {t['status_label']}"
        )

    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return TEMP_FILE


def read_decisions(trips):
    """Read user's edited file. Returns (keep_trips, exclude_trips)."""
    if not os.path.exists(TEMP_FILE):
        return [], trips

    with open(TEMP_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse kept trip codes from file
    kept_codes = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Extract trip code (first field before |)
        parts = line.split("|")
        code = parts[0].strip()
        if code.startswith("TRIP"):
            kept_codes.add(code)

    keep = [t for t in trips if t["code"] in kept_codes]
    exclude = [t for t in trips if t["code"] not in kept_codes]

    return keep, exclude


def save_final_decisions(keep, exclude, week_num):
    """Save decision record for audit trail."""
    os.makedirs(DECISIONS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    decision_file = os.path.join(DECISIONS_DIR, f"W{week_num}_{today}.json")

    record = {
        "week": week_num,
        "decided_at": datetime.now().isoformat(),
        "keep_as_ontime": [{"code": t["code"], "date": t["departure_date"],
                            "driver": t["driver"]} for t in keep],
        "excluded": [{"code": t["code"], "date": t["departure_date"],
                      "driver": t["driver"]} for t in exclude],
    }

    with open(decision_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return decision_file


def run_performance_report():
    """Generate performance report for the relevant month."""
    now = datetime.now()
    prev_week = now - timedelta(days=7)
    month = prev_week.month
    year = prev_week.year

    script = os.path.join(BASE, "script", "domains", "performance", "generate.py")
    cmd = [sys.executable, script, "--month", f"{month:02d}", "--year", str(year)]
    print(f"\n  🏃 Generating performance report T{month:02d}/{year}...")
    result = subprocess.run(cmd, cwd=BASE, timeout=300)
    return result.returncode == 0


def run_deploy():
    script = os.path.join(BASE, "script", "dashboard", "deploy.py")
    cmd = [sys.executable, script, "--domain", "performance"]
    print(f"  🚀 Deploying performance dashboard...")
    result = subprocess.run(cmd, cwd=BASE, timeout=120)
    return result.returncode == 0


def send_telegram_cutoff_notice(trips, week_num):
    """Send Telegram notification that cutoff is ready."""
    tg_path = os.path.join(BASE, "config", "telegram.json")
    with open(tg_path, encoding="utf-8") as f:
        tg = json.load(f)

    bot_token = tg["trip_reminder"]["bot_token"]
    chat_id = tg["trip_reminder"]["chat_id"]

    lines = [
        f"✂️ <b>Trip Cutoff Ready — W{week_num}</b>",
        f"",
        f"⚠ {len(trips)} trips chưa hoàn thành.",
        f"",
    ]
    for t in trips[:10]:
        pt_str = ", ".join(t["transfer_codes"][:2]) or "(no PT)"
        lines.append(f"  <code>{t['code']}</code> | {t['driver']} | {t['status_label']}")

    if len(trips) > 10:
        lines.append(f"  ... +{len(trips)-10} trips")

    lines.append(f"")
    lines.append(f"👉 Chạy <code>run-trip-cutoff.bat</code> để quyết định")

    msg = "\n".join(lines)

    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        print(f"  ✅ Telegram notification sent")
    except Exception as e:
        print(f"  ❌ Telegram error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Trip cutoff — T3 09:00")
    parser.add_argument("--exclude-all", action="store_true",
                        help="Auto-exclude all incomplete trips (no Notepad)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, don't generate report")
    parser.add_argument("--no-deploy", action="store_true",
                        help="Generate report but skip deploy")
    parser.add_argument("--notify-only", action="store_true",
                        help="Only send Telegram notification (for Task Scheduler)")
    args = parser.parse_args()

    now = datetime.now()
    print(f"{'='*60}")
    print(f"  ✂️ Trip Cutoff — {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}")

    start, end = get_week_range()
    week_num = get_week_number()
    print(f"  Tuần W{week_num}: {start} → {end}")

    print(f"  Querying StarRocks...")
    trips = query_incomplete_trips(start, end)

    if not trips:
        print(f"\n  ✅ Tất cả trips đã hoàn thành — generate report luôn!")
        if not args.dry_run and not args.notify_only:
            ok = run_performance_report()
            if ok and not args.no_deploy:
                run_deploy()
        return

    print(f"  ⚠ {len(trips)} trips chưa hoàn thành\n")
    for t in trips:
        pt_str = ", ".join(t["transfer_codes"][:3]) or "(no PT)"
        print(f"    {t['code']} | {t['departure_date']} | {t['driver']} | {pt_str} | {t['status_label']}")

    # Notify-only mode: send Telegram and exit (for Task Scheduler)
    if args.notify_only:
        print(f"\n  📱 Sending Telegram notification...")
        send_telegram_cutoff_notice(trips, week_num)
        return

    if args.exclude_all:
        print(f"\n  → Auto-exclude ALL {len(trips)} trips")
        keep, exclude = [], trips
    elif args.dry_run:
        print(f"\n  [DRY RUN] — Sẽ mở Notepad để chọn trips")
        return
    else:
        # Write file and open Notepad
        temp_path = write_decision_file(trips, week_num)
        print(f"\n  📝 Mở Notepad — chỉnh sửa rồi SAVE + ĐÓNG...")
        print(f"     GIỮ dòng = cho on-time, XÓA dòng = bỏ")
        print(f"     File: {temp_path}")
        print()

        # Open Notepad and WAIT for it to close
        subprocess.run(["notepad.exe", temp_path])

        # Read decisions
        keep, exclude = read_decisions(trips)

    print(f"\n  📊 Kết quả:")
    print(f"     ✅ Giữ (on-time): {len(keep)} trips")
    for t in keep:
        print(f"        {t['code']} | {t['driver']}")
    print(f"     ❌ Bỏ (exclude): {len(exclude)} trips")
    for t in exclude:
        print(f"        {t['code']} | {t['driver']}")

    # Save decisions for audit
    decision_file = save_final_decisions(keep, exclude, week_num)
    print(f"\n  💾 Decisions saved: {decision_file}")

    if args.dry_run:
        print(f"  [DRY RUN] — Không generate report")
        return

    # Generate report (reads decisions from trip_decisions/ dir)
    ok = run_performance_report()
    if ok:
        print(f"  ✅ Performance report generated!")
        if not args.no_deploy:
            run_deploy()
    else:
        print(f"  ❌ Performance report failed")
        sys.exit(1)

    # Cleanup temp file
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)

    print(f"\n{'='*60}")
    print(f"  ✅ Trip cutoff complete — W{week_num}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
