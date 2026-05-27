# -*- coding: utf-8 -*-
"""
trip_reminder.py — T2+T3 Telegram reminder for incomplete trips
================================================================
T2 08:00 → Send list of incomplete trips + stores to personal Telegram
T3 08:00 → Second reminder with cutoff warning (09:00 deadline)

Queries ClickHouse for trips NOT completed (status != 3) during
the previous week, including per-store breakdown from tl_arrival.

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


def load_ch_config():
    ch_path = os.path.join(BASE, "config", "mcp_clickhouse.json")
    with open(ch_path, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["base_url"], cfg["params"]


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


# ── ClickHouse Query ──
def query_incomplete_trips(start_date, end_date):
    """Query incomplete trips from ClickHouse with per-store breakdown."""
    import requests as _req

    base_url, params = load_ch_config()

    # Get incomplete trips (status 1,2) with per-store arrival info
    sql = f"""
    SELECT
        t.t_code AS trip_code,
        CAST(t.t_status AS Int32) AS status,
        toString(toDate(t.t_departure)) AS dep_date,
        t.t_license_number AS plate,
        t.t_driver_name AS driver,
        arrayJoin(t.t_from_location_name_abbreviates) AS noi_chuyen,
        b.branch_name_abbreviate AS dest,
        t.tl_arrival AS arrival
    FROM kdb.kf_trip_locations_items t
    LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
    WHERE toDate(t.t_departure) BETWEEN '{start_date}' AND '{end_date}'
      AND t.t_status IN (1, 2)
    ORDER BY t.t_departure, t.t_code
    FORMAT JSON
    """

    r = _req.get(base_url, params={**params, "query": sql}, timeout=60)
    r.raise_for_status()
    data = r.json().get("data", [])

    # Group by trip_code
    trips = {}
    for row in data:
        code = row["trip_code"]
        if code not in trips:
            trips[code] = {
                "code": code,
                "status": int(row["status"]),
                "departure_date": row["dep_date"],
                "license": row.get("plate", ""),
                "driver": row.get("driver", ""),
                "noi_chuyen": row.get("noi_chuyen", ""),
                "stores_done": [],
                "stores_pending": [],
            }
        dest = row.get("dest", "")
        arrival = str(row.get("arrival", "")).strip()
        has_arrival = arrival and arrival not in ("", "0001-01-01T00:00:00Z", "0001-01-01 00:00:00")

        if dest:
            if has_arrival:
                if dest not in trips[code]["stores_done"]:
                    trips[code]["stores_done"].append(dest)
            else:
                if dest not in trips[code]["stores_pending"]:
                    trips[code]["stores_pending"].append(dest)

    return list(trips.values())


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

    total_stores_pending = 0

    for date in sorted(by_date.keys()):
        date_vn = format_date_vn(date)
        day_trips = by_date[date]
        lines.append(f"📅 <b>{date_vn}</b> — {len(day_trips)} trip(s)")

        for t in day_trips:
            status = format_status(t["status"])
            done = len(t["stores_done"])
            pending = len(t["stores_pending"])
            total = done + pending
            total_stores_pending += pending

            # Store breakdown
            store_info = f"{done}/{total} stores done"
            if t["stores_pending"]:
                pending_list = ", ".join(t["stores_pending"][:5])
                if len(t["stores_pending"]) > 5:
                    pending_list += f" +{len(t['stores_pending'])-5}"
                store_info += f"\n      ❌ Chưa: {pending_list}"

            lines.append(
                f"  <code>{t['code']}</code> | {t['driver']} | {t['noi_chuyen']}"
                f"\n      {status} | {store_info}"
            )
        lines.append("")

    lines.append(f"<b>Tổng: {len(trips)} trips, {total_stores_pending} stores chưa giao</b>")
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

    print(f"  Querying ClickHouse...")
    trips = query_incomplete_trips(start, end)

    if not trips:
        print(f"  ✅ Không có trip chưa hoàn thành!")
    else:
        total_pending_stores = sum(len(t["stores_pending"]) for t in trips)
        print(f"  ⚠ {len(trips)} trips chưa hoàn thành ({total_pending_stores} stores pending)")

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
