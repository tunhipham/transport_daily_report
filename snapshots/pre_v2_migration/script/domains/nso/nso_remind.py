# -*- coding: utf-8 -*-
"""
nso_remind.py — NSO Reminder: check missing info in master_schedule
====================================================================
Cross-check NSO stores opening this week + next week vs master_schedule.json
and NSO_SCHEDULE. Send Telegram reminder to personal chat.

Usage:
    python script/domains/nso/nso_remind.py              # send reminder
    python script/domains/nso/nso_remind.py --dry-run     # preview only
"""
import os, sys, json, argparse, requests
from datetime import datetime, date, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "script"))
sys.path.insert(0, os.path.join(REPO_ROOT, "script", "domains", "nso"))
sys.path.insert(0, os.path.join(REPO_ROOT, "script", "dashboard"))

from generate import STORES as NSO_STORES, parse_date as nso_parse_date, get_display_name
from export_weekly_plan import NSO_SCHEDULE

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════
TELEGRAM_CONFIG = os.path.join(REPO_ROOT, "config", "telegram.json")
MASTER_SCHEDULE = os.path.join(REPO_ROOT, "data", "master_schedule.json")

DAY_NAMES = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "CN"}


def week_range(d):
    """Return (monday, sunday) of the week containing date d."""
    mon = d - timedelta(days=d.weekday())
    sun = mon + timedelta(days=6)
    return mon, sun


def load_master_codes():
    """Load store codes from master_schedule.json."""
    if not os.path.exists(MASTER_SCHEDULE):
        print("  ⚠ master_schedule.json not found")
        return set()
    with open(MASTER_SCHEDULE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["code"] for s in data.get("stores", [])}


def get_nso_for_weeks(today):
    """Get NSO stores opening this week and next week.

    Returns:
        this_week: list of (store, opening_date, day_name)
        next_week: list of (store, opening_date, day_name)
    """
    mon_this, sun_this = week_range(today)
    mon_next = mon_this + timedelta(days=7)
    sun_next = mon_next + timedelta(days=6)

    this_week = []
    next_week = []

    for s in NSO_STORES:
        try:
            d = nso_parse_date(s["opening_date"])
        except Exception:
            continue

        day_name = DAY_NAMES.get(d.weekday(), "?")

        if mon_this <= d <= sun_this:
            this_week.append((s, d, day_name))
        elif mon_next <= d <= sun_next:
            next_week.append((s, d, day_name))

    this_week.sort(key=lambda x: x[1])
    next_week.sort(key=lambda x: x[1])
    return this_week, next_week


def check_missing(stores_list, master_codes):
    """Check which NSO stores are missing info.

    Returns list of (store, opening_date, day_name, issues[])
    """
    results = []
    for s, d, day_name in stores_list:
        issues = []
        code = s.get("code")

        # Check 1: has code?
        if not code:
            issues.append("❌ Chưa có mã store (code)")

        # Check 2: in master_schedule?
        if code and code not in master_codes:
            issues.append("❌ Chưa có trong master_schedule")

        # Check 3: in NSO_SCHEDULE (has schedule_ve + shift)?
        sched = NSO_SCHEDULE.get(code, {}) if code else {}
        if not sched.get("schedule_ve"):
            issues.append("⚠ Thiếu schedule_ve (lịch về hàng)")
        if not sched.get("shift"):
            issues.append("⚠ Thiếu shift (Ngày/Đêm)")

        # Check 4: has version?
        if not s.get("version"):
            issues.append("⚠ Thiếu version (2000/1500/1000/700)")

        if issues:
            results.append((s, d, day_name, issues))

    return results


def build_message(today, this_week, next_week, missing_this, missing_next):
    """Build Telegram reminder message."""
    mon_this, sun_this = week_range(today)
    mon_next = mon_this + timedelta(days=7)
    sun_next = mon_next + timedelta(days=6)

    lines = []
    lines.append(f"🏪 <b>NSO Reminder — {today.strftime('%d/%m/%Y')}</b>")
    lines.append("")

    # This week summary
    lines.append(f"📌 <b>TUẦN NÀY ({mon_this.strftime('%d/%m')} → {sun_this.strftime('%d/%m')}):</b>")
    if this_week:
        for s, d, day_name in this_week:
            code = s.get("code") or "—"
            name = get_display_name(s)
            is_thu5 = d.weekday() == 3  # Thursday
            thu5_flag = " ⚡" if is_thu5 else ""
            lines.append(f"  • <code>{code}</code> — {name}")
            lines.append(f"    📅 KT {d.strftime('%d/%m')} ({day_name}){thu5_flag}")
    else:
        lines.append("  Không có NSO khai trương tuần này.")
    lines.append("")

    # Next week summary
    lines.append(f"📌 <b>TUẦN SAU ({mon_next.strftime('%d/%m')} → {sun_next.strftime('%d/%m')}):</b>")
    if next_week:
        for s, d, day_name in next_week:
            code = s.get("code") or "—"
            name = get_display_name(s)
            is_thu5 = d.weekday() == 3
            thu5_flag = " ⚡" if is_thu5 else ""
            lines.append(f"  • <code>{code}</code> — {name}")
            lines.append(f"    📅 KT {d.strftime('%d/%m')} ({day_name}){thu5_flag}")
    else:
        lines.append("  Không có NSO khai trương tuần sau.")
    lines.append("")

    # Missing info
    all_missing = missing_this + missing_next
    if all_missing:
        lines.append("⚠️ <b>CẦN BỔ SUNG:</b>")
        for s, d, day_name, issues in all_missing:
            code = s.get("code") or "—"
            name_short = (s.get("name_full") or s.get("name_mail") or "")[:30]
            is_thu5 = d.weekday() == 3
            lines.append(f"  <code>{code}</code> — {name_short} (KT {d.strftime('%d/%m')}, {day_name})")
            for iss in issues:
                lines.append(f"    {iss}")
            if is_thu5:
                lines.append(f"    ⚡ KT Thứ 5 — cần lịch tuần trước Thứ 5!")
        lines.append("")
        lines.append("💡 Hỏi lịch về hàng daily cho các store trên.")
    else:
        lines.append("✅ Tất cả NSO đã có đủ thông tin trong master_schedule!")

    return "\n".join(lines)


def send_telegram(message, dry_run=False):
    """Send message via Telegram bot to personal chat."""
    with open(TELEGRAM_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)

    remind_cfg = config.get("nso_remind", {})
    bot_token = remind_cfg.get("bot_token")
    chat_id = remind_cfg.get("chat_id")

    if not bot_token or not chat_id:
        print("  ⚠ nso_remind config not found in telegram.json")
        return False

    if dry_run:
        print(f"\n  📱 [DRY RUN] Would send to chat {chat_id}:")
        # Print plain text version
        plain = message.replace("<b>", "").replace("</b>", "")
        plain = plain.replace("<code>", "").replace("</code>", "")
        print(plain)
        return True

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        print(f"  ✅ Telegram reminder sent to chat {chat_id}")
        return True
    except Exception as e:
        print(f"  ❌ Telegram send failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="NSO Reminder — check missing info")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't send")
    args = parser.parse_args()

    today = date.today()
    now = datetime.now()
    print(f"\n{'='*55}")
    print(f"  🏪 NSO Reminder — {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}")

    # Load data
    master_codes = load_master_codes()
    print(f"  📋 Master schedule: {len(master_codes)} stores")
    print(f"  🏪 NSO stores: {len(NSO_STORES)} total")
    print(f"  📅 NSO_SCHEDULE: {len(NSO_SCHEDULE)} entries")

    # Get stores for this week + next week
    this_week, next_week = get_nso_for_weeks(today)
    print(f"\n  📌 Tuần này: {len(this_week)} NSO stores")
    print(f"  📌 Tuần sau: {len(next_week)} NSO stores")

    # Check missing info
    missing_this = check_missing(this_week, master_codes)
    missing_next = check_missing(next_week, master_codes)
    print(f"  ⚠ Thiếu info: {len(missing_this)} tuần này, {len(missing_next)} tuần sau")

    # Build and send message
    message = build_message(today, this_week, next_week, missing_this, missing_next)
    send_telegram(message, dry_run=args.dry_run)

    print(f"\n{'='*55}\n")


if __name__ == "__main__":
    main()
