# -*- coding: utf-8 -*-
"""
auto_inventory_watch.py — Monday kiểm kê refresh for Lịch Tuần

Monday pipeline (07:00→12:00):
  - 07:00-11:00: Watch kiểm kê changes from Google Sheets (log only)
  - 12:00 cutoff: Re-generate Excel → export JSON → deploy → send summary + file
  - User confirm → --deliver: send updated Excel to group SCM-NCP

Usage:
  python script/dashboard/auto_inventory_watch.py              # One-shot check
  python script/dashboard/auto_inventory_watch.py --watch      # Watch mode (loop every 1h until 12:00)
  python script/dashboard/auto_inventory_watch.py --dry-run    # Check only, no deploy/notify
  python script/dashboard/auto_inventory_watch.py --force      # Force run (ignore day-of-week check)
  python script/dashboard/auto_inventory_watch.py --backup     # Backup: one-shot full pipeline (any day)
  python script/dashboard/auto_inventory_watch.py --deliver    # Send updated Excel to group SCM-NCP

Schedule: runs via Windows Task Scheduler on Mondays only.
          Use --backup for ad-hoc runs outside Monday.
"""

import os, sys, json, argparse, subprocess, logging, time, atexit
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.path.join(BASE, "output", "state")
STATE_PATH = os.path.join(STATE_DIR, "inventory_watch_state.json")
LOCK_PATH = os.path.join(STATE_DIR, "inventory_watch.lock")
LOG_PATH = os.path.join(BASE, "output", "logs", "inventory_watch.log")
TELEGRAM_CONFIG = os.path.join(BASE, "config", "telegram.json")
WEEKLY_PLAN_JSON = os.path.join(BASE, "docs", "data", "weekly_plan.json")

# Import shared libs
sys.path.insert(0, os.path.join(BASE, "script"))
from lib.telegram import load_telegram_config, send_telegram_text, send_telegram_document, delete_telegram_message

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


def load_state():
    """Load state (last telegram message_id etc)."""
    os.makedirs(STATE_DIR, exist_ok=True)
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save state."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_notification(message):
    """Send Telegram notification. Deletes previous message first."""
    bot_token, chat_id = load_telegram_config(TELEGRAM_CONFIG, domain="weekly_plan")
    if not bot_token or not chat_id:
        log.warning("  ⚠ Telegram not configured for weekly_plan domain")
        return False

    # Delete previous message
    state = load_state()
    prev_mid = state.get("last_telegram_msg_id")
    if prev_mid:
        ok = delete_telegram_message(prev_mid, bot_token, chat_id)
        if ok:
            log.info(f"  🗑️ Deleted previous Telegram message (msg_id={prev_mid})")
        else:
            log.info(f"  ℹ Could not delete previous message (msg_id={prev_mid})")

    # Send new message
    mid = send_telegram_text(message, bot_token, chat_id)
    if mid:
        state["last_telegram_msg_id"] = mid
        save_state(state)
    return mid is not None


# ══════════════════════════════════════════════════════════════════════
#  Main check cycle
# ══════════════════════════════════════════════════════════════════════

def run_check(dry_run=False, is_final=False):
    """Run one inventory check cycle.

    is_final=False (intermediate): fetch kiểm kê, log changes only — no deploy/export
    is_final=True  (cutoff 12h):   re-gen Excel → export JSON → deploy → send summary + file

    Returns: 'changed', 'unchanged', or 'error'.
    """
    now = datetime.now()
    now_str = now.strftime("%d/%m/%Y %H:%M")
    week_label, week_start, week_end = get_current_week()
    week_num = int(week_label[1:])
    mode = "CUTOFF" if is_final else "MONITOR"

    log.info(f"\n{'═'*55}")
    log.info(f"  📋 Inventory Watch [{mode}] — {now_str}")
    log.info(f"  📅 {week_label}: {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}")
    log.info(f"{'═'*55}")

    # ── Step 1: Read BEFORE state from dashboard ──
    log.info(f"\n  📖 Reading current {week_label} inventory from dashboard...")
    before = read_week_inventory(week_label, week_start, week_end)
    log.info(f"     → {len(before)} stores with kiểm kê this week")
    for code, info in sorted(before.items()):
        log.info(f"       • {code} {info['name']}: {info['date']}")

    if not is_final:
        # ── INTERMEDIATE CYCLE: just fetch + compare, don't act ──
        log.info(f"\n  👁 Monitoring only (deploy at cutoff {WATCH_END_HOUR}:{WATCH_END_MINUTE:02d})")
        export_ok = run_export()
        if not export_ok:
            log.info("  ⚠ Export failed this cycle, will retry next cycle")
            return "error"
        after = read_week_inventory(week_label, week_start, week_end)
        diff = diff_week_inventory(before, after)
        log.info(f"\n{format_diff_log(diff, week_label)}")
        if diff["has_changes"]:
            log.info("  📌 Changes detected — will be applied at cutoff")
        return "changed" if diff["has_changes"] else "unchanged"

    # ══════════════════════════════════════════════════
    #  FINAL CYCLE (cutoff): full pipeline
    # ══════════════════════════════════════════════════
    if dry_run:
        log.info("\n  🏃 DRY RUN — skipping full pipeline")
        return "unchanged"

    # Step 2: Re-generate Excel for current week (fresh kiểm kê)
    log.info(f"\n  📝 Re-generating Excel W{week_num}...")
    regen_ok = run_generate_excel(week_num)
    if not regen_ok:
        log.error("  ❌ Excel re-generation failed")

    # Step 3: Re-export JSON
    log.info(f"\n  📅 Re-exporting weekly plan JSON...")
    export_ok = run_export()
    if not export_ok:
        log.error("  ❌ Export failed")
        return "error"

    # Step 4: Diff vs Thursday baseline (shift + kiểm kê + days)
    thu_diff = diff_vs_thursday(week_label, week_num)

    # Step 5: Deploy dashboard
    log.info(f"\n  🚀 Deploying dashboard...")
    deploy_ok = run_deploy()

    # Step 6: Send Telegram summary + Excel file
    send_monday_summary(thu_diff, week_label, week_num, week_start, week_end)

    # Step 7: Save diff to state for --deliver
    save_monday_diff(thu_diff, week_label, week_num)

    # ── Summary ──
    n_changes = len(thu_diff.get("changes", []))
    log.info(f"\n  {'─'*45}")
    log.info(f"  📊 Kết quả CUTOFF:")
    log.info(f"     Excel:    {'✅' if regen_ok   else '❌'}")
    log.info(f"     Export:   {'✅' if export_ok  else '❌'}")
    log.info(f"     Deploy:   {'✅' if deploy_ok  else '❌'}")
    log.info(f"     Changes vs Thu: {n_changes}")
    for c in thu_diff.get("changes", []):
        log.info(f"       • {c}")
    log.info(f"  {'─'*45}")

    return "changed" if n_changes > 0 else "unchanged"


def run_generate_excel(week_num):
    """Run generate_excel.py --week {nn} to re-generate current week's Excel."""
    script = os.path.join(BASE, "script", "domains", "weekly_plan", "generate_excel.py")
    log.info(f"  📝 Running generate_excel.py --week {week_num}...")
    try:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, script, "--week", str(week_num)],
            capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            timeout=120, cwd=BASE, env=env
        )
        if result.returncode == 0:
            log.info(f"  ✅ Excel W{week_num} re-generated")
            return True
        else:
            log.warning(f"  ⚠ generate_excel returned code {result.returncode}")
            if result.stderr:
                log.warning(f"     {result.stderr[:200]}")
            return False
    except Exception as e:
        log.error(f"  ❌ generate_excel error: {e}")
        return False


def diff_vs_thursday(week_label, week_num):
    """Diff current weekly_plan.json vs Thursday baseline.
    Compares: shift, inventory_date (within current week only), days.
    Returns dict with 'changes' (list of human-readable strings) and 'has_changes'."""
    baseline_path = os.path.join(BASE, "output", "state", f"thursday_baseline_W{week_num}.json")
    json_path = os.path.join(BASE, "docs", "data", "weekly_plan.json")

    if not os.path.exists(baseline_path):
        log.warning(f"  ⚠ Thursday baseline not found: {baseline_path}")
        log.info("  ℹ Falling back to same-run kiểm kê diff only")
        return {"changes": [], "has_changes": False}

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    thu_stores = baseline.get("stores", {})

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mon_stores_list = data.get("weeks", {}).get(week_label, {}).get("stores", [])
    mon_stores = {s["code"]: s for s in mon_stores_list}

    # Week date range for filtering kiểm kê
    _, week_start, week_end = get_current_week()

    def _kk_in_week(date_str):
        """Check if a kiểm kê date string falls within current week."""
        if not date_str:
            return False
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y").date()
            return week_start <= dt <= week_end
        except ValueError:
            return False

    changes = []

    log.info(f"\n  🔍 Diffing vs Thursday baseline ({baseline.get('saved_at', '?')})...")
    log.info(f"     Thu: {len(thu_stores)} stores | Mon: {len(mon_stores)} stores")
    log.info(f"     Week range: {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}")

    for code in sorted(set(thu_stores) & set(mon_stores)):
        old = thu_stores[code]
        new = mon_stores[code]
        kk_changed = False

        # Shift change
        old_shift = old.get("shift", "")
        new_shift = new.get("shift", "")
        if old_shift != new_shift:
            changes.append(f"đổi shift {code} {old_shift}→{new_shift}")

        # Kiểm kê change — only if relevant to this week
        old_kk = old.get("inventory_date", "")
        new_kk = new.get("inventory_date", "")
        if old_kk != new_kk:
            old_in_week = _kk_in_week(old_kk)
            new_in_week = _kk_in_week(new_kk)
            # Only report if either old or new date is within this week
            if old_in_week or new_in_week:
                kk_changed = True
                if old_kk and new_kk:
                    changes.append(f"dời kiểm kê {code} {old_kk}→{new_kk}")
                elif new_kk:
                    changes.append(f"thêm kiểm kê {code} {new_kk}")
                else:
                    changes.append(f"hủy kiểm kê {code} (was {old_kk})")

        # Days change — only if NOT already explained by shift or kiểm kê change
        old_days = old.get("days", [])
        new_days = new.get("days", [])
        if old_days != new_days:
            if old_shift == new_shift and not kk_changed:
                changes.append(f"đổi lịch giao {code}")

    # Added/removed stores
    for code in sorted(set(mon_stores) - set(thu_stores)):
        changes.append(f"thêm store {code}")
    for code in sorted(set(thu_stores) - set(mon_stores)):
        changes.append(f"bỏ store {code}")

    for c in changes:
        log.info(f"     • {c}")
    if not changes:
        log.info("     ✓ Không thay đổi so với thứ 5")

    return {"changes": changes, "has_changes": len(changes) > 0}


def send_monday_summary(thu_diff, week_label, week_num, week_start, week_end):
    """Send Telegram summary + Excel file + draft group caption."""
    bot_token, chat_id = load_telegram_config(TELEGRAM_CONFIG, domain="weekly_plan")
    if not bot_token or not chat_id:
        log.warning("  ⚠ Telegram not configured")
        return

    # Delete previous Monday message
    state = load_state()
    prev_mid = state.get("last_telegram_msg_id")
    if prev_mid:
        delete_telegram_message(prev_mid, bot_token, chat_id)

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = week_start.strftime("%d/%m")
    we = week_end.strftime("%d/%m")
    changes = thu_diff.get("changes", [])

    # Build draft group caption
    if changes:
        change_text = ", ".join(changes)
        draft_caption = f"SCM gửi lại lịch đi hàng {week_label} có cập nhật thay đổi: {change_text}"
    else:
        draft_caption = f"SCM gửi lại lịch đi hàng {week_label} (cập nhật thứ 2)"

    # Build summary message
    lines = [
        f"📋 <b>Lịch Tuần {week_label} — Monday Update</b>",
        f"📅 {ws}–{we} | 🕐 {now_str}",
        "",
    ]

    if not changes:
        lines.append("✅ Không thay đổi so với thứ 5")
    else:
        lines.append(f"🔄 <b>Thay đổi v/s thứ 5 ({len(changes)}):</b>")
        for c in changes:
            lines.append(f"  • {c}")
        lines.append("")

    lines.append("✅ Dashboard đã cập nhật")
    lines.append("📎 File Excel kèm bên dưới")
    lines.append("")
    lines.append("─── Draft caption gửi group ───")
    lines.append(f"<i>{draft_caption}</i>")
    lines.append("")
    lines.append("Reply '<b>OK</b>' để gửi group SCM-NCP với caption trên 👆")

    msg = "\n".join(lines)
    mid = send_telegram_text(msg, bot_token, chat_id)
    if mid:
        state["last_telegram_msg_id"] = mid
        save_state(state)
        log.info(f"  ✅ Telegram summary sent (msg_id={mid})")

    # Send Excel file
    excel_path = os.path.join(PLAN_DIR, f"Lịch đi hàng ST W{week_num}.xlsx")
    if os.path.exists(excel_path):
        caption = f"📋 Lịch đi hàng W{week_num} — cập nhật {now_str}"
        fmid = send_telegram_document(excel_path, caption, bot_token, chat_id)
        if fmid:
            log.info(f"  ✅ Excel file sent (msg_id={fmid})")
    else:
        log.warning(f"  ⚠ Excel not found: {excel_path}")


def save_monday_diff(thu_diff, week_label, week_num):
    """Save Monday diff to state for --deliver."""
    state = load_state()
    changes = thu_diff.get("changes", [])

    # Build group caption
    if changes:
        change_text = ", ".join(changes)
        group_caption = f"SCM gửi lại lịch đi hàng {week_label} có cập nhật thay đổi: {change_text}"
    else:
        group_caption = f"SCM gửi lại lịch đi hàng {week_label} (cập nhật thứ 2)"

    state["monday_diff"] = {
        "week_label": week_label,
        "week_num": week_num,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "has_changes": thu_diff.get("has_changes", False),
        "changes": changes,
        "group_caption": group_caption,
    }
    save_state(state)
    log.info(f"  💾 Monday diff saved to state")


def deliver_monday():
    """--deliver: Send updated Excel to group SCM-NCP with diff caption."""
    state = load_state()
    md = state.get("monday_diff", {})

    if not md:
        log.info("  ⚠ No Monday diff found. Run --watch or --backup first.")
        return

    week_label = md["week_label"]
    week_num = md["week_num"]

    # Load config
    with open(TELEGRAM_CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    wp = cfg.get("weekly_plan", {})
    bot_token = wp.get("bot_token")
    group_chat_id = wp.get("group_chat_id")
    personal_chat_id = wp.get("chat_id")

    if not bot_token or not group_chat_id:
        log.info("  ❌ Telegram config missing (bot_token or group_chat_id)")
        return

    # Use pre-built caption from state
    caption = md.get("group_caption", f"SCM gửi lại lịch đi hàng {week_label} (cập nhật thứ 2)")

    # Find Excel
    excel_path = os.path.join(PLAN_DIR, f"Lịch đi hàng ST W{week_num}.xlsx")
    if not os.path.exists(excel_path):
        log.info(f"  ❌ Excel not found: {excel_path}")
        return

    fsize = os.path.getsize(excel_path)
    log.info(f"  📤 Delivering {week_label} to SCM-NCP group ({fsize:,} bytes)...")

    mid = send_telegram_document(excel_path, caption, bot_token, group_chat_id)
    if mid:
        log.info(f"  ✅ Delivered to group! (msg_id={mid})")
        if personal_chat_id:
            send_telegram_text(
                f"✅ Lịch đi hàng {week_label} (Monday update) đã gửi group SCM-NCP",
                bot_token, personal_chat_id
            )
    else:
        log.info("  ❌ Failed to deliver to group")


# ══════════════════════════════════════════════════════════════════════
#  Watch mode
# ══════════════════════════════════════════════════════════════════════

WATCH_END_HOUR = 12
WATCH_END_MINUTE = 0
POLL_INTERVAL_SEC = 3600  # 1 hour
PLAN_DIR = os.path.join(BASE, "output", "artifacts", "weekly transport plan")


def watch_mode(dry_run=False):
    """Watch mode: intermediate cycles (log only) → final cutoff cycle (full pipeline)."""
    if not acquire_lock():
        return
    atexit.register(release_lock)

    log.info(f"\n{'═'*55}")
    log.info(f"  👁️  Inventory Watch — WATCH MODE")
    log.info(f"  📅 Monitor 07:00→{WATCH_END_HOUR}:{WATCH_END_MINUTE:02d}, cutoff = full pipeline")
    log.info(f"  🔒 PID: {os.getpid()}")
    log.info(f"{'═'*55}")

    cycle = 0
    while True:
        now = datetime.now()
        end_time = now.replace(hour=WATCH_END_HOUR, minute=WATCH_END_MINUTE, second=0)

        if now >= end_time:
            # ── CUTOFF: run final cycle ──
            log.info(f"\n  ⏰ Cutoff {WATCH_END_HOUR}:{WATCH_END_MINUTE:02d} — running FINAL cycle")
            try:
                run_check(dry_run=dry_run, is_final=True)
            except Exception as e:
                log.error(f"  ❌ Final cycle error: {e}")
                import traceback
                log.error(traceback.format_exc())
            log.info(f"\n  ✅ Watch mode complete.")
            break

        # ── INTERMEDIATE CYCLE ──
        cycle += 1
        log.info(f"\n  ── Cycle #{cycle} (monitor) ──")

        try:
            run_check(dry_run=dry_run, is_final=False)
        except Exception as e:
            log.error(f"  ❌ Cycle error: {e}")
            import traceback
            log.error(traceback.format_exc())

        # Sleep until next cycle
        now = datetime.now()
        next_run = now + timedelta(seconds=POLL_INTERVAL_SEC)

        if next_run >= end_time:
            # Next run would be past cutoff — sleep until cutoff
            remaining = (end_time - now).total_seconds()
            if remaining > 60:
                log.info(f"  💤 Sleeping {int(remaining // 60)} min until cutoff {WATCH_END_HOUR}:{WATCH_END_MINUTE:02d}...")
                time.sleep(remaining)
            # Loop back to run final cycle
        else:
            log.info(f"  💤 Sleeping {POLL_INTERVAL_SEC // 60} min until {next_run.strftime('%H:%M')}...")
            time.sleep(POLL_INTERVAL_SEC)

    release_lock()


# ══════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Monday kiểm kê refresh — Lịch Tuần")
    parser.add_argument("--watch", action="store_true",
                        help="Watch mode: poll every 1h until 12:00, full pipeline at cutoff")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check only, no deploy/notify")
    parser.add_argument("--force", action="store_true",
                        help="Force run (ignore day-of-week check)")
    parser.add_argument("--backup", action="store_true",
                        help="Backup: one-shot full pipeline (any day)")
    parser.add_argument("--deliver", action="store_true",
                        help="Send updated Excel to group SCM-NCP (after user confirm)")
    args = parser.parse_args()

    now = datetime.now()

    # Deliver mode: send to group (any day)
    if args.deliver:
        log.info("\n  📤 DELIVER MODE — sending to group SCM-NCP")
        deliver_monday()
        return

    # Backup mode: run full pipeline immediately (any day)
    if args.backup:
        log.info("\n  🔄 BACKUP MODE — full pipeline (one-shot)")
        run_check(dry_run=args.dry_run, is_final=True)
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
        run_check(dry_run=args.dry_run, is_final=True)


if __name__ == "__main__":
    main()
