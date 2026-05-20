# -*- coding: utf-8 -*-
"""
trip_reminder.py — T2+T3 Telegram reminder for incomplete trips
================================================================
Queries StarRocks for trips that were NOT completed (status 1,2)
during the previous week (Mon→Sun), and sends a detailed summary
to the personal Telegram chat.

Schedule:
  Monday    08:00 → First remind
  Tuesday   08:00 → Second remind (cutoff warning)

Usage:
    python script/telegram/trip_reminder.py            # Run
    python script/telegram/trip_reminder.py --dry-run  # Preview
    python script/telegram/trip_reminder.py --second   # Force T3 mode
"""
import os, sys, json, argparse
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ── Config ──
def load_config():
    tg_path = os.path.join(BASE, "config", "telegram.json")
    with open(tg_path, encoding="utf-8") as f:
        return json.load(f)


def get_week_range():
    """Return (monday, sunday) of the PREVIOUS week as YYYY-MM-DD."""
    today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    prev_monday = this_monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6)
    return prev_monday.strftime("%Y-%m-%d"), prev_sunday.strftime("%Y-%m-%d")


def get_week_number():
    today = datetime.now()
    prev_week = today - timedelta(days=7)
    return prev_week.isocalendar()[1]


# ── StarRocks Query ──
def query_incomplete_trips(start_date, end_date):
    """Query incomplete trips from StarRocks.
    Returns list of trip dicts with transfer codes.
    """
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
            trips.append({
                "code": code,
                "status": int(status),
                "departure_date": dep,
                "license": plate or "",
                "driver": driver or "",
                "transfer_codes": tcodes,
            })

    conn.close()
    return trips


def format_status(status):
    return {1: "🆕 Tạo mới", 2: "🚚 Đang giao"}.get(status, f"Status {status}")


def format_date_vn(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    return f"{dt.strftime('%d/%m')} ({weekdays[dt.weekday()]})"


def build_message(trips, week_num, is_second_remind=False):
    remind_label = "⚠️ LẦN 2 — CUTOFF 09:00" if is_second_remind else "📋 Dzí trip"

    if not trips:
        return (
            f"✅ <b>Trip Report W{week_num}</b>\n\n"
            f"Tất cả trips tuần W{week_num} đã hoàn thành. 🎉"
        )

    by_date = {}
    for t in trips:
        d = t["departure_date"]
        by_date.setdefault(d, []).append(t)

    lines = [f"🔴 <b>Trips chưa hoàn thành — W{week_num}</b>"]
    lines.append(f"{remind_label}\n")

    for date in sorted(by_date.keys()):
        date_vn = format_date_vn(date)
        day_trips = by_date[date]
        lines.append(f"📅 <b>{date_vn}</b> — {len(day_trips)} trip(s)")

        for t in day_trips:
            status = format_status(t["status"])
            pt_str = ", ".join(t["transfer_codes"][:3])
            if len(t["transfer_codes"]) > 3:
                pt_str += f" +{len(t['transfer_codes'])-3}"
            if not pt_str:
                pt_str = "(no PT)"

            lines.append(
                f"  <code>{t['code']}</code> | {t['driver']} | {pt_str} | {status}"
            )
        lines.append("")

    lines.append(f"<b>Tổng: {len(trips)} trips</b>")
    if is_second_remind:
        lines.append(f"\n⏰ <b>Cutoff 09:00 — xử lý trước khi generate report</b>")

    return "\n".join(lines)


# ── Telegram ──
def send_telegram(bot_token, chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Trip reminder — T2+T3 8AM")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--second", action="store_true", help="Force T3 mode (cutoff warning)")
    args = parser.parse_args()

    now = datetime.now()
    is_tuesday = now.weekday() == 1 or args.second

    print(f"{'='*60}")
    print(f"  🚛 Trip Reminder — {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"  {'T3 (lần 2)' if is_tuesday else 'T2 (lần 1)'}")
    print(f"{'='*60}")

    telegram_cfg = load_config()

    start, end = get_week_range()
    week_num = get_week_number()
    print(f"  Tuần W{week_num}: {start} → {end}")

    print(f"  Querying StarRocks...")
    trips = query_incomplete_trips(start, end)

    if not trips:
        print(f"  ✅ Không có trip chưa hoàn thành!")
    else:
        print(f"  ⚠ {len(trips)} trips chưa hoàn thành")

    msg = build_message(trips, week_num, is_second_remind=is_tuesday)
    print(f"\n{msg}\n")

    if args.dry_run:
        print("  [DRY RUN] — Không gửi Telegram")
        return

    bot_token = telegram_cfg["trip_reminder"]["bot_token"]
    chat_id = telegram_cfg["trip_reminder"]["chat_id"]

    print(f"  Sending to chat_id={chat_id}...")
    try:
        send_telegram(bot_token, chat_id, msg)
        print(f"  ✅ Sent!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
