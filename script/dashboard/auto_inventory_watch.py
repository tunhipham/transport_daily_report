# -*- coding: utf-8 -*-
"""
auto_inventory_watch.py — Monitor kiểm kê schedule changes on Mondays

Compares inventory dates in the current weekly plan (dashboard) with
fresh data from Google Sheets. Reports only changes affecting the
current week's stores (new, changed, cancelled inventory dates).

Usage:
  python script/dashboard/auto_inventory_watch.py              # One-shot check
  python script/dashboard/auto_inventory_watch.py --watch      # Watch mode (loop every 1h until 17:30)
  python script/dashboard/auto_inventory_watch.py --dry-run    # Check only, no deploy/notify
  python script/dashboard/auto_inventory_watch.py --force      # Force run (ignore day-of-week check)
  python script/dashboard/auto_inventory_watch.py --backup     # Backup: fetch + update + notify (any day, one-shot)

Schedule: runs via Windows Task Scheduler on Mondays only.
          Use --backup for ad-hoc runs outside Monday.
"""

import os, sys, json, argparse, subprocess, logging, time, atexit
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.path.join(BASE, "output", "state")
LOCK_PATH = os.path.join(STATE_DIR, "inventory_watch.lock")
LOG_PATH = os.path.join(BASE, "output", "logs", "inventory_watch.log")
TELEGRAM_CONFIG = os.path.join(BASE, "config", "telegram.json")
WEEKLY_PLAN_JSON = os.path.join(BASE, "docs", "data", "weekly_plan.json")

# Import shared libs
sys.path.insert(0, os.path.join(BASE, "script"))
from lib.telegram import load_telegram_config, send_telegram_text

# ── Logging ──────────────────────────────────────────────────────────

def setup_logging():
    """Setup logging to both file and console."""
    logger = logging.getLogger("inventory_watch")
    logger.setLevel(logging.INFO)
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)
    # File handler
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    fh = logging.FileHandler(LOG_PATH, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter('%(asctime)s  %(message)s', datefmt='%Y-%m-%d %H:%M'))
    logger.addHandler(fh)
    return logger

log = setup_logging()

# ══════════════════════════════════════════════════════════════════════
#  Instance locking (prevent duplicate watch processes)
# ══════════════════════════════════════════════════════════════════════

def acquire_lock():
    """Try to acquire lock file. Returns True if successful."""
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    if os.path.exists(LOCK_PATH):
        try:
            with open(LOCK_PATH, "r") as f:
                pid = int(f.read().strip())
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                log.info(f"  ⚠ Another instance running (PID {pid}), exiting.")
                return False
        except (ValueError, OSError):
            pass
    with open(LOCK_PATH, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    """Release lock file."""
    try:
        if os.path.exists(LOCK_PATH):
            with open(LOCK_PATH, "r") as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(LOCK_PATH)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Week calculation (same anchor as auto_compose.py)
# ══════════════════════════════════════════════════════════════════════

ANCHOR_WEEK = 14
ANCHOR_START = datetime(2026, 3, 30)  # Monday W14


def get_current_week():
    """Get current week label (e.g. 'W17') and date range.
    Returns (week_label, week_start_date, week_end_date).
    """
    today = datetime.now().date()
    days_diff = (today - ANCHOR_START.date()).days
    weeks_diff = days_diff // 7
    week_num = ANCHOR_WEEK + weeks_diff
    week_start = (ANCHOR_START + timedelta(weeks=weeks_diff)).date()
    week_end = week_start + timedelta(days=6)
    return f"W{week_num}", week_start, week_end


def _parse_date(date_str):
    """Parse dd/mm/yyyy string to date object."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════════
#  Read inventory from weekly_plan.json
# ══════════════════════════════════════════════════════════════════════

def read_week_inventory(week_label, week_start, week_end):
    """Read current weekly_plan.json and extract inventory dates
    for stores in the given week that fall within the week's date range.

    Returns dict: store_code → inventory_date_str (only dates within the week).
    """
    if not os.path.exists(WEEKLY_PLAN_JSON):
        log.warning(f"  ⚠ {WEEKLY_PLAN_JSON} not found")
        return {}

    with open(WEEKLY_PLAN_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    weeks = data.get("weeks", {})
    week_data = weeks.get(week_label, {})
    stores = week_data.get("stores", [])

    inventory = {}
    for store in stores:
        code = store.get("code", "")
        inv_date_str = store.get("inventory_date", "")
        name = store.get("name", "")
        if not inv_date_str:
            continue
        dt = _parse_date(inv_date_str)
        if dt and week_start <= dt <= week_end:
            inventory[code] = {
                "date": inv_date_str,
                "name": name,
            }

    return inventory


# ══════════════════════════════════════════════════════════════════════
#  Diff: before vs after export
# ══════════════════════════════════════════════════════════════════════

def diff_week_inventory(before, after):
    """Compare before and after inventory for the current week.
    
    Returns diff with:
    - added: stores that gained an inventory date in this week
    - removed: stores that lost their inventory date from this week
    - changed: stores whose inventory date changed within this week
    - unchanged: stores with same inventory date
    """
    before_codes = set(before.keys())
    after_codes = set(after.keys())

    added = sorted(after_codes - before_codes)
    removed = sorted(before_codes - after_codes)

    changed = []
    unchanged = []
    for code in sorted(before_codes & after_codes):
        if before[code]["date"] != after[code]["date"]:
            changed.append({
                "code": code,
                "name": after[code]["name"],
                "old_date": before[code]["date"],
                "new_date": after[code]["date"],
            })
        else:
            unchanged.append(code)

    return {
        "added": [{
            "code": c,
            "name": after[c]["name"],
            "date": after[c]["date"],
        } for c in added],
        "removed": [{
            "code": c,
            "name": before[c]["name"],
            "date": before[c]["date"],
        } for c in removed],
        "changed": changed,
        "unchanged": unchanged,
        "has_changes": bool(added or removed or changed),
    }


def format_diff_log(diff, week_label):
    """Format diff for console/log output."""
    lines = [f"  📅 {week_label} — Kết quả so sánh:"]

    if diff["added"]:
        lines.append(f"  🆕 Thêm mới ({len(diff['added'])}):")
        for s in diff["added"]:
            lines.append(f"     • {s['code']} {s['name']}: {s['date']}")

    if diff["changed"]:
        lines.append(f"  🔄 Đổi lịch ({len(diff['changed'])}):")
        for s in diff["changed"]:
            lines.append(f"     • {s['code']} {s['name']}: {s['old_date']} → {s['new_date']}")

    if diff["removed"]:
        lines.append(f"  🗑️ Hủy kiểm kê ({len(diff['removed'])}):")
        for s in diff["removed"]:
            lines.append(f"     • {s['code']} {s['name']}: {s['date']}")

    if not diff["has_changes"]:
        lines.append(f"  ✓ Không thay đổi ({len(diff['unchanged'])} stores giữ nguyên)")

    return "\n".join(lines)


def format_telegram_message(diff, week_label, week_start, week_end):
    """Format Telegram HTML message — only shows what changed in this week."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = week_start.strftime("%d/%m")
    we = week_end.strftime("%d/%m")

    lines = [f"📋 <b>Kiểm Kê {week_label} ({ws}–{we})</b>"]
    lines.append(f"🕐 Cập nhật: {now_str}")
    lines.append("")

    if not diff["has_changes"]:
        lines.append(f"✅ Lịch kiểm kê tuần này không thay đổi ({len(diff['unchanged'])} stores)")
        lines.append("")
        lines.append("🔗 https://tunhipham.github.io/transport_daily_report/")
        return "\n".join(lines)

    if diff["changed"]:
        lines.append(f"🔄 <b>Đổi lịch ({len(diff['changed'])}):</b>")
        for s in diff["changed"]:
            lines.append(f"  • {s['code']} {s['name']}: {s['old_date']} → {s['new_date']}")
        lines.append("")

    if diff["added"]:
        lines.append(f"🆕 <b>Thêm kiểm kê ({len(diff['added'])}):</b>")
        for s in diff["added"]:
            lines.append(f"  • {s['code']} {s['name']}: {s['date']}")
        lines.append("")

    if diff["removed"]:
        lines.append(f"🗑️ <b>Hủy kiểm kê ({len(diff['removed'])}):</b>")
        for s in diff["removed"]:
            lines.append(f"  • {s['code']} {s['name']}: {s['date']}")
        lines.append("")

    lines.append("✅ Dashboard đã cập nhật")
    lines.append("🔗 https://tunhipham.github.io/transport_daily_report/")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
#  Export & Deploy
# ══════════════════════════════════════════════════════════════════════

def run_export():
    """Run export_weekly_plan.py to regenerate weekly_plan.json."""
    script = os.path.join(BASE, "script", "dashboard", "export_weekly_plan.py")
    log.info("  📅 Re-exporting weekly plan...")
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            timeout=120, cwd=BASE
        )
        if result.returncode == 0:
            log.info("  ✅ Weekly plan re-exported")
            return True
        else:
            log.warning(f"  ⚠ Export returned code {result.returncode}")
            if result.stderr:
                log.warning(f"     {result.stderr[:200]}")
            return False
    except Exception as e:
        log.error(f"  ❌ Export error: {e}")
        return False


def run_deploy():
    """Run deploy.py --domain weekly_plan to push to GitHub Pages."""
    script = os.path.join(BASE, "script", "dashboard", "deploy.py")
    log.info("  🚀 Deploying to GitHub Pages...")
    try:
        result = subprocess.run(
            [sys.executable, script, "--domain", "weekly_plan"],
            capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            timeout=180, cwd=BASE
        )
        if result.returncode == 0:
            log.info("  ✅ Deployed to GitHub Pages")
            return True
        else:
            log.warning(f"  ⚠ Deploy returned code {result.returncode}")
            if result.stdout:
                if "nothing to commit" in result.stdout or "No changes" in result.stdout:
                    log.info("  ℹ No changes to deploy (data unchanged after export)")
                    return True
            return False
    except Exception as e:
        log.error(f"  ❌ Deploy error: {e}")
        return False


def send_notification(message):
    """Send Telegram notification."""
    bot_token, chat_id = load_telegram_config(TELEGRAM_CONFIG, domain="weekly_plan")
    if not bot_token or not chat_id:
        log.warning("  ⚠ Telegram not configured for weekly_plan domain")
        return False
    mid = send_telegram_text(message, bot_token, chat_id)
    return mid is not None


# ══════════════════════════════════════════════════════════════════════
#  Main check cycle
# ══════════════════════════════════════════════════════════════════════

def run_check(dry_run=False):
    """Run one inventory check cycle.
    
    Flow:
    1. Read CURRENT weekly_plan.json → get this week's inventory (BEFORE)
    2. Run export_weekly_plan.py (fetches fresh Google Sheets)
    3. Read UPDATED weekly_plan.json → get this week's inventory (AFTER)
    4. Diff BEFORE vs AFTER → report changes
    
    Returns: 'changed', 'unchanged', or 'error'.
    """
    now = datetime.now()
    now_str = now.strftime("%d/%m/%Y %H:%M")
    log.info(f"\n{'═'*55}")
    log.info(f"  📋 Inventory Watch — {now_str}")
    log.info(f"{'═'*55}")

    # ── Determine current week ──
    week_label, week_start, week_end = get_current_week()
    log.info(f"\n  📅 {week_label}: {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}")

    # ── Step 1: Read BEFORE state from dashboard ──
    log.info(f"\n  📖 Reading current {week_label} inventory from dashboard...")
    before = read_week_inventory(week_label, week_start, week_end)
    log.info(f"     → {len(before)} stores with kiểm kê this week")
    for code, info in sorted(before.items()):
        log.info(f"       • {code} {info['name']}: {info['date']}")

    # ── Step 2: Re-export (fetch fresh Google Sheets) ──
    if not dry_run:
        export_ok = run_export()
        if not export_ok:
            log.error("  ❌ Export failed, cannot compare")
            return "error"
    else:
        log.info("\n  🏃 DRY RUN — skipping export")

    # ── Step 3: Read AFTER state from dashboard ──
    log.info(f"\n  📖 Reading updated {week_label} inventory from dashboard...")
    after = read_week_inventory(week_label, week_start, week_end)
    log.info(f"     → {len(after)} stores with kiểm kê this week")

    # ── Step 4: Diff ──
    diff = diff_week_inventory(before, after)
    log.info(f"\n{format_diff_log(diff, week_label)}")

    if dry_run:
        log.info("\n  🏃 DRY RUN — skipping deploy/notify")
        return "changed" if diff["has_changes"] else "unchanged"

    # ── Deploy ──
    deploy_ok = run_deploy()

    # ── Telegram notify ──
    telegram_msg = format_telegram_message(diff, week_label, week_start, week_end)
    notify_ok = send_notification(telegram_msg)

    # ── Summary ──
    log.info(f"\n  {'─'*45}")
    log.info(f"  📊 Kết quả:")
    log.info(f"     Export:   ✅")
    log.info(f"     Deploy:   {'✅' if deploy_ok   else '❌'}")
    log.info(f"     Telegram: {'✅' if notify_ok   else '❌'}")
    if diff["has_changes"]:
        total = len(diff['added']) + len(diff['changed']) + len(diff['removed'])
        log.info(f"     Changes:  {total} ({len(diff['added'])} thêm, {len(diff['changed'])} đổi, {len(diff['removed'])} hủy)")
    else:
        log.info(f"     Changes:  Không thay đổi")
    log.info(f"  {'─'*45}")

    return "changed" if diff["has_changes"] else "unchanged"


# ══════════════════════════════════════════════════════════════════════
#  Watch mode
# ══════════════════════════════════════════════════════════════════════

WATCH_END_HOUR = 17
WATCH_END_MINUTE = 30
POLL_INTERVAL_SEC = 3600  # 1 hour


def watch_mode(dry_run=False):
    """Run in watch mode: loop every 1h until 17:30."""
    if not acquire_lock():
        return
    atexit.register(release_lock)

    log.info(f"\n{'═'*55}")
    log.info(f"  👁️  Inventory Watch — WATCH MODE")
    log.info(f"  📅 Chạy mỗi {POLL_INTERVAL_SEC // 60} phút đến {WATCH_END_HOUR}:{WATCH_END_MINUTE:02d}")
    log.info(f"  🔒 PID: {os.getpid()}")
    log.info(f"{'═'*55}")

    cycle = 0
    while True:
        now = datetime.now()

        # Check end time
        end_time = now.replace(hour=WATCH_END_HOUR, minute=WATCH_END_MINUTE, second=0)
        if now >= end_time:
            log.info(f"\n  ⏰ Đã qua {WATCH_END_HOUR}:{WATCH_END_MINUTE:02d} — stopping watch mode.")
            break

        cycle += 1
        log.info(f"\n  ── Cycle #{cycle} ──")

        try:
            run_check(dry_run=dry_run)
        except Exception as e:
            log.error(f"  ❌ Cycle error: {e}")
            import traceback
            log.error(traceback.format_exc())

        # Calculate sleep time
        now = datetime.now()
        next_run = now + timedelta(seconds=POLL_INTERVAL_SEC)

        # Don't sleep past end time
        if next_run >= end_time:
            remaining = (end_time - now).total_seconds()
            if remaining > 60:
                log.info(f"  💤 Sleeping {int(remaining // 60)} min (last cycle before {WATCH_END_HOUR}:{WATCH_END_MINUTE:02d})...")
                time.sleep(remaining)
            log.info(f"\n  ⏰ Watch mode complete.")
            break
        else:
            log.info(f"  💤 Sleeping {POLL_INTERVAL_SEC // 60} min until {next_run.strftime('%H:%M')}...")
            time.sleep(POLL_INTERVAL_SEC)

    release_lock()


# ══════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Inventory Schedule Watch — Monday auto-update")
    parser.add_argument("--watch", action="store_true",
                        help="Watch mode: poll every 1h until 17:30")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check only, no deploy/notify")
    parser.add_argument("--force", action="store_true",
                        help="Force run (ignore day-of-week check)")
    parser.add_argument("--backup", action="store_true",
                        help="Backup mode: one-shot fetch + update + notify (any day)")
    args = parser.parse_args()

    now = datetime.now()

    # Backup mode: skip all checks, just run
    if args.backup:
        log.info("\n  🔄 BACKUP MODE — manual fetch + update + notify")
        run_check(dry_run=args.dry_run)
        return

    # Day-of-week check (skip unless Monday or --force)
    if now.weekday() != 0 and not args.force:
        day_name = now.strftime("%A")
        log.info(f"  ⏭ Today is {day_name} — inventory watch only runs on Monday.")
        log.info(f"  💡 Use --force or --backup to run anyway.")
        return

    if args.watch:
        watch_mode(dry_run=args.dry_run)
    else:
        run_check(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
