# -*- coding: utf-8 -*-
"""
Weekly Plan Finalize — Thursday automation for Lịch về hàng.

Modes:
  --check   12:00 Thu → check data readiness, send Telegram reminder
  --send    13:00 Thu → generate Excel, send file for review
  --deliver (future) → after user confirms, send to team group

Usage:
  python script/domains/weekly_plan/finalize.py --check
  python script/domains/weekly_plan/finalize.py --send
"""
import os, sys, io, json, argparse

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timedelta, date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO_ROOT)

from script.lib.telegram import load_telegram_config, send_telegram_text, send_telegram_document

# Config
TELEGRAM_CFG = os.path.join(REPO_ROOT, "config", "telegram.json")
MASTER_SCHEDULE = os.path.join(REPO_ROOT, "data", "master_schedule.json")
PLAN_DIR = os.path.join(REPO_ROOT, "output", "artifacts", "weekly transport plan")


def get_next_week_info():
    """Get week number and date range for NEXT week (the week being planned)."""
    today = date.today()
    # Next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    next_sunday = next_monday + timedelta(days=6)
    week_num = next_monday.isocalendar()[1]
    return week_num, next_monday, next_sunday


def check_readiness():
    """Check if all data is ready for weekly plan generation.
    Returns (is_ready, issues_list, info_dict)."""
    issues = []
    info = {}
    
    # 1. Check master_schedule.json exists and has data
    if not os.path.exists(MASTER_SCHEDULE):
        issues.append("❌ master_schedule.json không tìm thấy")
    else:
        with open(MASTER_SCHEDULE, "r", encoding="utf-8") as f:
            ms = json.load(f)
        stores = ms.get("stores", [])
        info["total_stores"] = len(stores)
        if len(stores) < 100:
            issues.append(f"⚠️ master_schedule chỉ có {len(stores)} stores (expected 150+)")
        
        # Check for stores missing schedule_ve
        missing_sched = [s for s in stores if not s.get("schedule_ve")]
        if missing_sched:
            names = [f"{s.get('code', '?')} {s.get('name', '?')}" for s in missing_sched[:5]]
            issues.append(f"⚠️ {len(missing_sched)} stores thiếu schedule_ve: {', '.join(names)}")
    
    # 2. Check NSO data — any upcoming stores that need attention?
    nso_file = os.path.join(REPO_ROOT, "data", "nso_master.json")
    if os.path.exists(nso_file):
        with open(nso_file, "r", encoding="utf-8") as f:
            nso = json.load(f)
        nso_stores = nso.get("stores", [])
        week_num, next_mon, next_sun = get_next_week_info()
        
        # Find NSO stores opening in next week range
        upcoming_nso = []
        for s in nso_stores:
            try:
                od = s.get("opening_date", "")
                opening = datetime.strptime(od, "%d/%m/%Y").date()
                # Check if any of D to D+3 falls within next week
                for d in range(4):
                    day = opening + timedelta(days=d)
                    if next_mon <= day <= next_sun:
                        upcoming_nso.append(s)
                        break
            except:
                pass
        
        info["nso_count"] = len(upcoming_nso)
        if upcoming_nso:
            nso_names = [f"{s.get('code', '?')} ({s.get('opening_date', '?')})" for s in upcoming_nso]
            info["nso_stores"] = nso_names
    
    # 3. Check kiểm kê availability (Google Sheets)
    try:
        import requests
        # Same sheet ID used in generate_excel.py
        SHEET_ID = "1B5y0WEgzLihNNnqtHaGNqmWn-hd2R8kJdJcGKPNxyUE"
        RANGE = "Kiểm kê!A:D"
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Ki%E1%BB%83m%20k%C3%AA&range=A:D"
        resp = requests.get(url, timeout=15, verify=False)
        if resp.status_code == 200:
            lines = resp.text.strip().split('\n')
            info["kiem_ke_count"] = max(0, len(lines) - 1)  # minus header
            if info["kiem_ke_count"] < 50:
                issues.append(f"⚠️ Kiểm kê chỉ có {info['kiem_ke_count']} entries (expected 70+)")
    except Exception as e:
        info["kiem_ke_count"] = "?"
    
    # 4. Check if Excel for next week already exists
    week_num, _, _ = get_next_week_info()
    excel_path = os.path.join(PLAN_DIR, f"Lịch đi hàng ST W{week_num}.xlsx")
    info["excel_exists"] = os.path.exists(excel_path)
    info["week_num"] = week_num
    
    is_ready = len(issues) == 0
    return is_ready, issues, info


def send_readiness_check():
    """12:00 Thursday: Check readiness and send Telegram reminder."""
    bot_token, chat_id = load_telegram_config(TELEGRAM_CFG, domain="weekly_plan")
    if not bot_token:
        print("❌ Telegram config missing")
        return
    
    week_num, next_mon, next_sun = get_next_week_info()
    is_ready, issues, info = check_readiness()
    
    print(f"\n📋 Weekly Plan Readiness Check — W{week_num}")
    print(f"   {next_mon.strftime('%d/%m')} → {next_sun.strftime('%d/%m')}")
    
    # Build Telegram message
    lines = [
        f"📋 <b>Weekly Plan W{week_num} — Readiness Check</b>",
        f"📅 {next_mon.strftime('%d/%m')} → {next_sun.strftime('%d/%m/%Y')}",
        "",
    ]
    
    # Data summary
    lines.append("📊 <b>Data Status:</b>")
    lines.append(f"  • Stores: {info.get('total_stores', '?')}")
    lines.append(f"  • Kiểm kê: {info.get('kiem_ke_count', '?')} entries")
    
    if info.get("nso_count", 0) > 0:
        lines.append(f"  • NSO châm hàng: {info['nso_count']} stores")
        for n in info.get("nso_stores", []):
            lines.append(f"    → {n}")
    else:
        lines.append("  • NSO châm hàng: 0")
    
    lines.append(f"  • Excel W{week_num}: {'✅ đã có' if info.get('excel_exists') else '⏳ chưa tạo'}")
    lines.append("")
    
    if is_ready:
        lines.append("✅ <b>Data sẵn sàng!</b>")
        lines.append("13h sẽ auto generate + gửi file review.")
        lines.append("")
        lines.append("Nếu có update/thay đổi, reply trước 13h nhé! 🙏")
    else:
        lines.append("⚠️ <b>Có vấn đề cần xử lý:</b>")
        for issue in issues:
            lines.append(f"  {issue}")
        lines.append("")
        lines.append("Vui lòng kiểm tra và fix trước 13h!")
    
    msg = "\n".join(lines)
    print(msg)
    
    mid = send_telegram_text(msg, bot_token, chat_id)
    if mid:
        print(f"\n✅ Reminder sent to Telegram (msg_id={mid})")
    else:
        print("\n❌ Failed to send Telegram reminder")


def generate_and_send():
    """13:00 Thursday: Generate Excel, export JSON, save baseline, send for review."""
    bot_token, chat_id = load_telegram_config(TELEGRAM_CFG, domain="weekly_plan")
    if not bot_token:
        print("❌ Telegram config missing")
        return
    
    week_num, next_mon, next_sun = get_next_week_info()
    
    print(f"\n📋 Generating Weekly Plan W{week_num}...")
    
    # Step 1: Generate Excel
    try:
        from script.domains.weekly_plan.generate_excel import main as gen_main
        gen_main(week_num)
    except Exception as e:
        error_msg = f"❌ <b>Weekly Plan W{week_num} — Generate Failed</b>\n\nError: {e}"
        send_telegram_text(error_msg, bot_token, chat_id)
        print(f"❌ Generate failed: {e}")
        return
    
    # Step 2: Export JSON + Deploy (so dashboard is up to date)
    import subprocess
    export_script = os.path.join(REPO_ROOT, "script", "dashboard", "export_weekly_plan.py")
    print(f"\n📅 Exporting weekly plan JSON...")
    subprocess.run([sys.executable, export_script], cwd=REPO_ROOT, timeout=120)
    
    # Step 3: Save Thursday baseline snapshot for Monday diff
    _save_thursday_baseline(week_num)
    
    # Step 4: Find the Excel file
    excel_path = os.path.join(PLAN_DIR, f"Lịch đi hàng ST W{week_num}.xlsx")
    if not os.path.exists(excel_path):
        error_msg = f"❌ <b>Weekly Plan W{week_num}</b>\n\nExcel file not found: {excel_path}"
        send_telegram_text(error_msg, bot_token, chat_id)
        return
    
    file_size = os.path.getsize(excel_path)
    
    # Step 5: Send Excel file for review
    caption = (
        f"📋 <b>Lịch về hàng W{week_num}</b>\n"
        f"📅 {next_mon.strftime('%d/%m')} → {next_sun.strftime('%d/%m/%Y')}\n"
        f"📊 File size: {file_size:,} bytes\n\n"
        f"Review xong reply 'OK' để gửi team nhé! ✅"
    )
    
    mid = send_telegram_document(excel_path, caption, bot_token, chat_id)
    if mid:
        print(f"\n✅ Excel sent to Telegram for review (msg_id={mid})")
    else:
        print("\n❌ Failed to send Excel to Telegram")


def _save_thursday_baseline(week_num):
    """Save current weekly_plan.json W{nn} stores as Thursday baseline.
    Monday watch will diff against this to detect all changes (shift, kiểm kê, days)."""
    json_path = os.path.join(REPO_ROOT, "docs", "data", "weekly_plan.json")
    baseline_path = os.path.join(REPO_ROOT, "output", "state", f"thursday_baseline_W{week_num}.json")
    
    if not os.path.exists(json_path):
        print(f"  ⚠ weekly_plan.json not found, cannot save baseline")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    week_key = f"W{week_num}"
    week_data = data.get("weeks", {}).get(week_key, {})
    stores = week_data.get("stores", [])
    
    baseline = {
        "week": week_key,
        "week_num": week_num,
        "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "stores": {s["code"]: s for s in stores},
    }
    
    os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 Thursday baseline saved: {len(stores)} stores → {baseline_path}")


def deliver_to_group(week_override=None):
    """14:00 Thursday: Send Excel to SCM - NCP group."""
    # Load config
    with open(TELEGRAM_CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    wp_cfg = cfg.get("weekly_plan", {})
    bot_token = wp_cfg.get("bot_token")
    group_chat_id = wp_cfg.get("group_chat_id")
    personal_chat_id = wp_cfg.get("chat_id")
    
    if not bot_token or not group_chat_id:
        print("❌ Telegram config missing (bot_token or group_chat_id)")
        return
    
    week_num = week_override or get_next_week_info()[0]
    
    # Find Excel file
    excel_path = os.path.join(PLAN_DIR, f"Lịch đi hàng ST W{week_num}.xlsx")
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return
    
    file_size = os.path.getsize(excel_path)
    print(f"📤 Delivering W{week_num} to SCM - NCP group ({file_size:,} bytes)...")
    
    caption = f"SCM gửi lịch về hàng W{week_num}"
    
    mid = send_telegram_document(excel_path, caption, bot_token, group_chat_id)
    if mid:
        print(f"✅ Delivered to group! (msg_id={mid})")
        # Also notify personal chat
        if personal_chat_id:
            send_telegram_text(
                f"✅ Lịch về hàng W{week_num} đã gửi group SCM - NCP",
                bot_token, personal_chat_id
            )
    else:
        print("❌ Failed to deliver to group")


def test_send():
    """Test: send current week's Excel file to Telegram."""
    bot_token, chat_id = load_telegram_config(TELEGRAM_CFG, domain="weekly_plan")
    if not bot_token:
        print("❌ Telegram config missing")
        return
    
    # Find the latest Excel file
    import glob
    files = sorted(glob.glob(os.path.join(PLAN_DIR, "Lịch đi hàng ST W*.xlsx")))
    if not files:
        print("❌ No Excel files found")
        return
    
    latest = files[-1]
    basename = os.path.basename(latest)
    file_size = os.path.getsize(latest)
    
    print(f"📤 Sending {basename} ({file_size:,} bytes)...")
    
    caption = (
        f"📋 <b>{basename}</b>\n"
        f"📊 File size: {file_size:,} bytes\n"
        f"🧪 Test send — {datetime.now().strftime('%H:%M %d/%m/%Y')}"
    )
    
    mid = send_telegram_document(latest, caption, bot_token, chat_id)
    if mid:
        print(f"✅ Sent! (msg_id={mid})")
    else:
        print("❌ Failed to send")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly Plan Finalize")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="12h: Check readiness + send reminder")
    group.add_argument("--send", action="store_true", help="13h: Generate Excel + send for review")
    group.add_argument("--deliver", action="store_true", help="14h: Send Excel to SCM-NCP group")
    group.add_argument("--test", action="store_true", help="Test: send latest Excel to personal chat")
    parser.add_argument("--week", type=int, help="Override week number")
    args = parser.parse_args()
    
    if args.check:
        send_readiness_check()
    elif args.send:
        generate_and_send()
    elif args.deliver:
        deliver_to_group(week_override=args.week)
    elif args.test:
        test_send()
