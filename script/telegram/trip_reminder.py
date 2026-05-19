# -*- coding: utf-8 -*-
"""
trip_reminder.py — Monday 8AM Telegram reminder for incomplete trips
====================================================================
Queries ClickHouse kf_trip_locations_items for trips that were NOT completed
(status != 3) during the previous week, and sends a summary to the personal
Telegram chat.

Usage:
    python script/telegram/trip_reminder.py            # Run manually
    python script/telegram/trip_reminder.py --dry-run  # Preview without sending

Scheduler: Windows Task Scheduler, every Monday 8:00 AM
"""
import os, sys, json, argparse
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──
def load_config():
    """Load data_sources.json + telegram.json."""
    ds_path = os.path.join(BASE, "config", "data_sources.json")
    tg_path = os.path.join(BASE, "config", "telegram.json")
    
    with open(ds_path, encoding="utf-8") as f:
        data_sources = json.load(f)
    with open(tg_path, encoding="utf-8") as f:
        telegram = json.load(f)
    
    return data_sources, telegram


def get_week_range():
    """Return (monday, sunday) of the PREVIOUS week as date strings YYYY-MM-DD."""
    today = datetime.now()
    # Current week's Monday
    this_monday = today - timedelta(days=today.weekday())
    # Previous week
    prev_monday = this_monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6)
    return prev_monday.strftime("%Y-%m-%d"), prev_sunday.strftime("%Y-%m-%d")


def get_week_number():
    """Return ISO week number for the previous week."""
    today = datetime.now()
    prev_week = today - timedelta(days=7)
    return prev_week.isocalendar()[1]


# ── ClickHouse Query ──
def query_incomplete_trips(start_date, end_date):
    """Query incomplete trips from ClickHouse."""
    from data_pipeline.config import load_clickhouse_config
    import requests

    cfg = load_clickhouse_config()
    params = {
        "user": cfg["user"],
        "password": cfg["password"],
        "database": cfg["database"],
    }

    sql = f"""
        SELECT 
            t_code,
            t_status,
            toString(toDate(t_departure)) AS departure_date,
            t_from_location_name_abbreviates AS from_kho,
            tl_branch_id,
            t_license_number,
            t_driver_name
        FROM kf_trip_locations_items
        WHERE toYear(t_departure) BETWEEN 2023 AND 2027
          AND toDate(t_departure) BETWEEN '{start_date}' AND '{end_date}'
          AND t_status IN (1, 2)
        ORDER BY t_departure
        FORMAT JSONEachRow
    """

    r = requests.get(
        cfg["base_url"],
        params={**params, "query": sql},
        timeout=60,
    )
    r.raise_for_status()

    trips = {}
    for line in r.text.strip().split("\n"):
        if not line.strip():
            continue
        obj = json.loads(line)
        code = obj["t_code"]
        if code not in trips:
            trips[code] = {
                "code": code,
                "status": obj["t_status"],
                "departure_date": obj["departure_date"],
                "from_kho": obj["from_kho"],
                "destinations": set(),
                "license": obj["t_license_number"],
                "driver": obj["t_driver_name"],
            }
        trips[code]["destinations"].add(obj["tl_branch_id"])

    return list(trips.values())


def format_status(status):
    """Human-readable status."""
    return {1: "Tạo mới", 2: "Đang giao"}.get(status, f"Status {status}")


def format_date_vn(date_str):
    """YYYY-MM-DD → DD/MM."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%d/%m")


# ── Telegram ──
def send_telegram(bot_token, chat_id, text):
    """Send message via Telegram Bot API."""
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
    parser = argparse.ArgumentParser(description="Trip reminder — Monday 8AM")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  🚛 Trip Reminder — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}")

    data_sources, telegram_cfg = load_config()
    
    start, end = get_week_range()
    week_num = get_week_number()
    print(f"  Tuần W{week_num}: {start} → {end}")

    # Query incomplete trips
    print(f"  Querying ClickHouse...")
    trips = query_incomplete_trips(start, end)
    
    if not trips:
        print(f"  ✅ Không có trip chưa hoàn thành!")
        msg = (
            f"✅ <b>Trip Report W{week_num}</b>\n\n"
            f"Tất cả trips tuần W{week_num} đã hoàn thành. 🎉"
        )
    else:
        print(f"  ⚠ {len(trips)} trips chưa hoàn thành")
        
        # Group by date → kho
        by_date = {}
        for t in trips:
            d = t["departure_date"]
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(t)
        
        lines = [f"🔴 <b>Trips chưa hoàn thành — W{week_num}</b>\n"]
        
        # If compact (> 20 trips), show summary per date + kho
        if len(trips) > 20:
            for date in sorted(by_date.keys()):
                date_vn = format_date_vn(date)
                day_trips = by_date[date]
                # Group by kho
                by_kho = {}
                for t in day_trips:
                    kho = t["from_kho"]
                    if isinstance(kho, list):
                        kho = ", ".join(str(x) for x in kho if x)
                        kho = kho.replace("[", "").replace("]", "").replace("'", "")
                    if kho not in by_kho:
                        by_kho[kho] = {"s1": 0, "s2": 0}
                    if t["status"] == 1:
                        by_kho[kho]["s1"] += 1
                    else:
                        by_kho[kho]["s2"] += 1
                
                parts = []
                for kho in sorted(by_kho.keys()):
                    counts = by_kho[kho]
                    detail = []
                    if counts["s2"]:
                        detail.append(f"{counts['s2']} đang giao")
                    if counts["s1"]:
                        detail.append(f"{counts['s1']} tạo mới")
                    parts.append(f"{kho}: {' + '.join(detail)}")
                
                lines.append(f"📅 <b>{date_vn}</b> ({len(day_trips)} trips)")
                for p in parts:
                    lines.append(f"  • {p}")
        else:
            # Detailed list for small numbers
            for date in sorted(by_date.keys()):
                date_vn = format_date_vn(date)
                day_trips = by_date[date]
                lines.append(f"\n📅 <b>{date_vn}</b>:")
                for t in day_trips:
                    status = format_status(t["status"])
                    from_kho = t["from_kho"]
                    if isinstance(from_kho, list):
                        from_kho = ", ".join(str(x) for x in from_kho if x)
                        from_kho = from_kho.replace("[", "").replace("]", "").replace("'", "")
                    n_dest = len(t["destinations"])
                    lines.append(
                        f"  • {t['code']} | {from_kho} → {n_dest} điểm | {status}"
                    )
        
        lines.append(f"\n<b>Tổng: {len(trips)} trips</b>")
        msg = "\n".join(lines)

    print(f"\n{msg}\n")

    if args.dry_run:
        print("  [DRY RUN] — Không gửi Telegram")
        return

    # Send
    bot_token = telegram_cfg["trip_reminder"]["bot_token"]
    chat_id = telegram_cfg["trip_reminder"]["chat_id"]  # Personal chat

    print(f"  Sending to chat_id={chat_id}...")
    try:
        send_telegram(bot_token, chat_id, msg)
        print(f"  ✅ Sent!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
