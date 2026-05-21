# -*- coding: utf-8 -*-
"""
sync_status.py — Quick status check for Daily Report pipeline
==============================================================
Double-click run-sync-status.bat or:
    python script/data_pipeline/sync_status.py

Shows:
  ✅ Task Scheduler status (enabled/disabled, last run)
  ✅ Today's sync log (recent entries)
  ✅ Lock status (Telegram sent or not)
  ✅ Last generate/deploy info
  ✅ Data freshness (last fingerprint check)
"""
import os, sys, json, subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

STATE_FILE = os.path.join(BASE, "output", "state", ".sync_state.json")
LOCK_DIR = os.path.join(BASE, "output", "state", "silver")
LOG_DIR = os.path.join(BASE, "output", "logs")

# ── Colors ──
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"
    BG_GREEN  = "\033[42m"
    BG_RED    = "\033[41m"
    BG_YELLOW = "\033[43m"


def header(text):
    print(f"\n{C.BOLD}{C.CYAN}{'─'*56}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'─'*56}{C.RESET}")


def badge(text, color):
    return f"{color}{C.BOLD} {text} {C.RESET}"


def main():
    now = datetime.now()
    today = now.strftime("%d/%m/%Y")
    today_iso = now.strftime("%Y-%m-%d")
    today_tag = now.strftime("%d%m%Y")

    print(f"\n{C.BOLD}{C.WHITE}{'═'*56}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  📊 DAILY REPORT — STATUS CHECK{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  {now.strftime('%d/%m/%Y %H:%M:%S')}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}{'═'*56}{C.RESET}")

    # ── 1. Task Scheduler ──
    header("⏰ TASK SCHEDULER")
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", "\\KFM\\SyncRealtime", "/v", "/fo", "LIST"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            info = {}
            for line in lines:
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key in ("Status", "Last Run Time", "Next Run Time", "Scheduled Task State", "Last Result"):
                        info[key] = val

            state_str = info.get("Scheduled Task State", "?")
            if state_str == "Enabled":
                print(f"  Task:       {badge('ENABLED', C.BG_GREEN)}")
            else:
                print(f"  Task:       {badge('DISABLED', C.BG_RED)}  ⚠ Không tự chạy!")
            
            status = info.get("Status", "?")
            status_color = C.GREEN if status == "Running" else C.YELLOW if status == "Ready" else C.RED
            print(f"  Status:     {status_color}{status}{C.RESET}")
            print(f"  Last run:   {info.get('Last Run Time', '?')}")
            
            last_result = info.get("Last Result", "?")
            if last_result == "0":
                print(f"  Result:     {C.GREEN}✅ Success{C.RESET}")
            elif last_result == "1":
                print(f"  Result:     {C.YELLOW}⚠ Exit 1 (data chưa sẵn sàng?){C.RESET}")
            elif last_result == "-1073741510":
                print(f"  Result:     {C.YELLOW}⚠ Terminated (PC sleep/restart){C.RESET}")
            else:
                print(f"  Result:     {C.RED}❌ Code {last_result}{C.RESET}")

            print(f"  Next run:   {info.get('Next Run Time', '?')}")
        else:
            print(f"  {C.RED}❌ Task \\KFM\\SyncRealtime not found!{C.RESET}")
    except Exception as e:
        print(f"  {C.RED}⚠ Cannot query Task Scheduler: {e}{C.RESET}")

    # ── 2. Sync State ──
    header("📡 SYNC STATE")
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        
        state_date = state.get("date", "?")
        is_today = state_date == today_iso
        
        if is_today:
            print(f"  Date:       {C.GREEN}{state_date} (hôm nay ✓){C.RESET}")
        else:
            print(f"  Date:       {C.YELLOW}{state_date} (chưa sync hôm nay){C.RESET}")
        
        last_check = state.get("last_check", "?")
        if last_check != "?":
            try:
                lc = datetime.fromisoformat(last_check)
                ago = (now - lc).total_seconds()
                if ago < 3600:
                    ago_str = f"{int(ago // 60)} phút trước"
                elif ago < 86400:
                    ago_str = f"{ago / 3600:.1f} giờ trước"
                else:
                    ago_str = f"{ago / 86400:.1f} ngày trước"
                print(f"  Last check: {lc.strftime('%H:%M:%S %d/%m')} ({ago_str})")
            except:
                print(f"  Last check: {last_check}")
        
        last_deploy = state.get("last_deploy", "?")
        if last_deploy != "?":
            try:
                ld = datetime.fromisoformat(last_deploy)
                print(f"  Last deploy:{C.GREEN} {ld.strftime('%H:%M:%S %d/%m')}{C.RESET}")
            except:
                print(f"  Last deploy: {last_deploy}")
        
        # Fingerprints
        tfp = state.get("transfer_fp", "?")
        sfp = state.get("schedule_fp", "?")
        if tfp != "?":
            parts = tfp.split("|")
            print(f"  Transfer:   {C.DIM}{parts[0]} rows | updated {parts[1] if len(parts)>1 else '?'}{C.RESET}")
        if sfp != "?":
            parts = sfp.split("|")
            print(f"  Schedule:   {C.DIM}{parts[0]} rows | updated {parts[1] if len(parts)>1 else '?'}{C.RESET}")
    else:
        print(f"  {C.YELLOW}⚠ No state file found{C.RESET}")

    # ── 3. Lock Status ──
    header("🔒 TELEGRAM LOCK")
    lock_dir = os.path.join(LOCK_DIR, today_tag)
    lock_file = os.path.join(lock_dir, "lock.json")
    if os.path.exists(lock_file):
        with open(lock_file, encoding="utf-8") as f:
            lock = json.load(f)
        locked_at = lock.get("locked_at", "?")
        try:
            la = datetime.fromisoformat(locked_at)
            locked_at = la.strftime("%H:%M:%S")
        except:
            pass
        print(f"  Status:     {badge('LOCKED', C.BG_GREEN)}  Telegram đã gửi lúc {locked_at}")
        print(f"  {C.DIM}Dashboard vẫn tiếp tục update{C.RESET}")
    else:
        hour = now.hour
        if hour < 8:
            print(f"  Status:     {C.YELLOW}⏳ Chưa tới cutoff (8:00 AM){C.RESET}")
        else:
            print(f"  Status:     {badge('UNLOCKED', C.BG_YELLOW)}  Telegram chưa gửi")
            print(f"  {C.DIM}Sẽ gửi khi generate thành công sau 8:00 AM{C.RESET}")

    # ── 4. Today's Sync Log ──
    header("📋 SYNC LOG HÔM NAY")
    log_file = os.path.join(LOG_DIR, f"sync_{today_iso}.log")
    if os.path.exists(log_file):
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
        
        # Count stats
        ok_count = sum(1 for l in lines if "] OK " in l)
        skip_count = sum(1 for l in lines if "] SKIP " in l)
        fail_count = sum(1 for l in lines if "] FAIL " in l or "] ERR " in l)
        dry_count = sum(1 for l in lines if "] DRY " in l)
        lock_count = sum(1 for l in lines if "] LOCK " in l)
        
        print(f"  Total:      {len([l for l in lines if l.strip()])} entries")
        if ok_count:
            print(f"  {C.GREEN}✅ OK: {ok_count}{C.RESET}", end="")
        if skip_count:
            print(f"  {C.DIM}⏭ SKIP: {skip_count}{C.RESET}", end="")
        if dry_count:
            print(f"  {C.YELLOW}🔍 DRY: {dry_count}{C.RESET}", end="")
        if fail_count:
            print(f"  {C.RED}❌ FAIL: {fail_count}{C.RESET}", end="")
        if lock_count:
            print(f"  {C.MAGENTA}🔒 LOCK: {lock_count}{C.RESET}", end="")
        print()
        
        # Show last 8 lines
        recent = [l.rstrip() for l in lines if l.strip()][-8:]
        print(f"\n  {C.DIM}── Recent ──{C.RESET}")
        for line in recent:
            # Color code by status
            if "] OK " in line:
                print(f"  {C.GREEN}{line}{C.RESET}")
            elif "] FAIL " in line or "] ERR " in line:
                print(f"  {C.RED}{line}{C.RESET}")
            elif "] LOCK " in line:
                print(f"  {C.MAGENTA}{line}{C.RESET}")
            elif "] DRY " in line:
                print(f"  {C.YELLOW}{line}{C.RESET}")
            else:
                print(f"  {C.DIM}{line}{C.RESET}")
    else:
        print(f"  {C.YELLOW}📭 Chưa có log — sync chưa chạy hôm nay{C.RESET}")
        # Show yesterday's summary
        yesterday_iso = (now.replace(hour=0, minute=0, second=0) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_log = os.path.join(LOG_DIR, f"sync_{yesterday_iso}.log")
        if os.path.exists(yesterday_log):
            with open(yesterday_log, encoding="utf-8") as f:
                ylines = f.readlines()
            ok_y = sum(1 for l in ylines if "] OK " in l)
            print(f"  {C.DIM}Hôm qua ({yesterday_iso}): {len([l for l in ylines if l.strip()])} entries, {ok_y} OK{C.RESET}")

    # ── 5. Quick verdict ──
    print(f"\n{C.BOLD}{C.WHITE}{'═'*56}{C.RESET}")
    
    # Determine overall status
    is_locked = os.path.exists(lock_file)
    has_log = os.path.exists(log_file)
    
    if is_locked:
        print(f"{C.BOLD}{C.GREEN}  ✅ DONE — Report đã generate + Telegram đã gửi{C.RESET}")
    elif has_log and ok_count > 0:
        print(f"{C.BOLD}{C.GREEN}  ✅ RUNNING — Đã generate, dashboard đang update{C.RESET}")
    elif has_log:
        print(f"{C.BOLD}{C.YELLOW}  ⏳ SYNCING — Đang poll, chờ data thay đổi...{C.RESET}")
    elif now.hour < 6:
        print(f"{C.BOLD}{C.DIM}  🌙 SLEEPING — Ngoài giờ sync (06:00-22:00){C.RESET}")
    elif now.hour >= 22:
        print(f"{C.BOLD}{C.DIM}  🌙 SLEEPING — Ngoài giờ sync (06:00-22:00){C.RESET}")
    else:
        print(f"{C.BOLD}{C.YELLOW}  ⏳ WAITING — Chờ sync cycle tiếp theo...{C.RESET}")
    
    print(f"{C.BOLD}{C.WHITE}{'═'*56}{C.RESET}\n")


if __name__ == "__main__":
    main()
