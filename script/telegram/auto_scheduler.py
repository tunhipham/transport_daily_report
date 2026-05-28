# -*- coding: utf-8 -*-
"""
Auto-scheduler for KFM Delivery Reports.
Runs continuously in the background and sends reports at scheduled times.
Features catch-up logic: if started after the scheduled time, it sends immediately.
Prevents duplicate sends via a state file.
"""
import os
import sys
import time
import json
import subprocess
from datetime import datetime, timedelta

# Default to personal ID for testing. User will change this later to Group ID.
GROUP_CHAT_ID = "5782090339"

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE, "docs", "data", "telegram_schedule_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def sync_tracking_data():
    print("  🔄 Fetching latest tracking data from DB...")
    subprocess.run(["python", "script/dashboard/export_data.py", "--domain", "performance"], cwd=BASE)

def send_report(kho, date_iso):
    cmd = [
        "python", "script/telegram/delivery_report_image.py", 
        "--kho", kho, 
        "--date", date_iso, 
        "--chat-id", GROUP_CHAT_ID,
        "--pilot" # Auto-generates pilot image for HTP/SCV if data exists
    ]
    print(f"  ▶ Generating & Sending: {kho} ({date_iso})")
    subprocess.run(cmd, cwd=BASE)

def check_schedule():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    
    state = load_state()
    if today_str not in state:
        state[today_str] = []
        
    sent_today = state[today_str]
    
    # ── 09:00 | Sáng mở máy: KRC (Hôm nay) & KSL-Tối (Hôm qua) ──
    if now.hour >= 9:
        if "morning_batch" not in sent_today:
            print(f"\n⏰ [09:00 BATCH TRIGGERED] at {now.strftime('%H:%M:%S')}")
            sync_tracking_data()
            send_report("KRC", today_str)
            send_report("KSL-Tối", yesterday_str)
            
            sent_today.append("morning_batch")
            save_state(state)
            print("  ✅ Morning batch completed.")
            
    # ── 15:00 | Chiều: KSL-Sáng (Hôm nay) ──
    if now.hour >= 15:
        if "afternoon_batch" not in sent_today:
            print(f"\n⏰ [15:00 BATCH TRIGGERED] at {now.strftime('%H:%M:%S')}")
            sync_tracking_data()
            send_report("KSL-Sáng", today_str)
            
            sent_today.append("afternoon_batch")
            save_state(state)
            print("  ✅ Afternoon batch completed.")
            
    # ── 16:30 | Chiều muộn: ĐÔNG & MÁT (Hôm nay) ──
    if (now.hour > 16) or (now.hour == 16 and now.minute >= 30):
        if "late_batch" not in sent_today:
            print(f"\n⏰ [16:30 BATCH TRIGGERED] at {now.strftime('%H:%M:%S')}")
            sync_tracking_data()
            send_report("ĐÔNG", today_str)
            send_report("MÁT", today_str)
            
            sent_today.append("late_batch")
            save_state(state)
            print("  ✅ Late batch completed.")

def main():
    print("════════════════════════════════════════════════════════════")
    print(f" 🚀 AUTO-SCHEDULER BÁO CÁO GIAO HÀNG")
    print(f" ⏰ Bắt đầu lúc: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    print("════════════════════════════════════════════════════════════")
    print(" Lịch trình thiết lập:")
    print("  • 09:00 -> KRC (nay) & KSL-Tối (qua)")
    print("  • 15:00 -> KSL-Sáng (nay)")
    print("  • 16:30 -> ĐÔNG (nay) & MÁT (nay)")
    print("------------------------------------------------------------")
    print(" Đang chạy ngầm theo dõi thời gian... (Bấm Ctrl+C để tắt)")
    
    while True:
        try:
            check_schedule()
            time.sleep(30) # Check every 30 seconds
        except KeyboardInterrupt:
            print("\n⏹ Scheduler stopped by user.")
            break
        except Exception as e:
            print(f"\n❌ Error in scheduler loop: {e}")
            import traceback; traceback.print_exc()
            time.sleep(60)

if __name__ == "__main__":
    main()
