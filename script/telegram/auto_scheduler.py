# -*- coding: utf-8 -*-
"""
Auto-scheduler for KFM Delivery Reports.
Runs continuously in the background and sends reports at scheduled times.
Features catch-up logic: if started after the scheduled time, it sends immediately.
Prevents duplicate sends via a state file.

Logging: All output goes to logs/auto_scheduler.log (+ console if available).
Crash resilience: Encoding-safe output, per-item error isolation.
"""
import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta

# ── Safe encoding setup ──────────────────────────────────────
# When launched via Task Scheduler / start /MIN, the console may use cp1252
# which can't encode emoji/Vietnamese → UnicodeEncodeError → crash.
# Fix: reconfigure both stdout AND stderr, with errors='replace' as fallback.
for stream_name in ('stdout', 'stderr'):
    stream = getattr(sys, stream_name, None)
    if stream and hasattr(stream, 'reconfigure'):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

# Force child processes to also use UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Default to personal ID for testing. User will change this later to Group ID.
GROUP_CHAT_ID = "5782090339"

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE, "docs", "data", "telegram_schedule_state.json")
LOG_DIR = os.path.join(BASE, "logs")
LOG_FILE = os.path.join(LOG_DIR, "auto_scheduler.log")

# ── Logging setup ────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("auto_scheduler")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File handler — rotates at 2MB, keeps 3 backups
from logging.handlers import RotatingFileHandler
fh = RotatingFileHandler(LOG_FILE, maxBytes=2*1024*1024, backupCount=3, encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler — may fail in headless mode, that's OK
try:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
except Exception:
    pass


def log(msg, level="info"):
    """Safe logging that never crashes the process."""
    try:
        getattr(logger, level, logger.info)(msg)
    except Exception:
        # Last resort: write raw bytes to log file
        try:
            with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"{datetime.now().isoformat()} [{level.upper()}] {msg}\n")
        except Exception:
            pass


# ── State management ─────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Warning: could not load state file: {e}", "warning")
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ── Actions ──────────────────────────────────────────────────
def sync_tracking_data():
    log("Fetching latest tracking data from DB...")
    result = subprocess.run(
        ["python", "script/dashboard/export_data.py", "--domain", "performance"],
        cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300,
    )
    if result.returncode != 0:
        log(f"WARNING: export_data.py exited with code {result.returncode}", "warning")
        if result.stderr:
            log(f"  stderr: {result.stderr[:500]}", "warning")
    else:
        log("Tracking data synced OK")


def send_report(kho, date_iso, is_pilot=False):
    cmd = [
        "python", "script/telegram/delivery_report_image.py",
        "--kho", kho,
        "--date", date_iso,
        "--chat-id", GROUP_CHAT_ID
    ]
    if is_pilot:
        cmd.append("--pilot")
    log(f"Generating & Sending: {kho} ({date_iso})")
    try:
        result = subprocess.run(
            cmd, cwd=BASE, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=300,
        )
        if result.returncode != 0:
            log(f"FAILED send_report {kho}: exit code {result.returncode}", "error")
            if result.stderr:
                log(f"  stderr: {result.stderr[:500]}", "error")
        else:
            log(f"OK: {kho} ({date_iso}) sent successfully")
            if result.stdout:
                # Log last few meaningful lines
                lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
                for line in lines[-5:]:
                    log(f"  | {line}")
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: send_report {kho} exceeded 5 min", "error")
    except Exception as e:
        log(f"ERROR in send_report {kho}: {e}", "error")


def check_schedule():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    state = load_state()
    if today_str not in state:
        state[today_str] = []

    sent_today = state[today_str]

    # ── 09:00 | Sang mo may: KRC (Hom nay) & KSL-Toi (Hom qua) ──
    if now.hour >= 9:
        if "morning_batch" not in sent_today:
            log(f"=== [09:00 BATCH TRIGGERED] at {now.strftime('%H:%M:%S')} ===")
            sync_tracking_data()
            send_report("KRC", today_str, is_pilot=True)
            send_report("KSL-Tối", yesterday_str, is_pilot=True)

            sent_today.append("morning_batch")
            save_state(state)
            log("Morning batch completed.")

    # ── 15:00 | Chieu: KSL-Sang (Hom nay) ──
    if now.hour >= 15:
        if "afternoon_batch" not in sent_today:
            log(f"=== [15:00 BATCH TRIGGERED] at {now.strftime('%H:%M:%S')} ===")
            sync_tracking_data()
            send_report("KSL-Sáng", today_str)

            sent_today.append("afternoon_batch")
            save_state(state)
            log("Afternoon batch completed.")

    # ── 16:30 | Chieu muon: DONG & MAT (Hom nay) ──
    if (now.hour > 16) or (now.hour == 16 and now.minute >= 30):
        if "late_batch" not in sent_today:
            log(f"=== [16:30 BATCH TRIGGERED] at {now.strftime('%H:%M:%S')} ===")
            sync_tracking_data()
            send_report("ĐÔNG", today_str)
            send_report("MÁT", today_str)

            sent_today.append("late_batch")
            save_state(state)
            log("Late batch completed.")

    # ── Cleanup: remove state entries older than 7 days ──
    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    old_keys = [k for k in state if k < cutoff]
    for k in old_keys:
        del state[k]
    if old_keys:
        save_state(state)


def main():
    log("=" * 60)
    log("AUTO-SCHEDULER BAO CAO GIAO HANG — started")
    log(f"Time: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    log(f"PID: {os.getpid()}")
    log(f"Log file: {LOG_FILE}")
    log("=" * 60)
    log("Schedule:")
    log("  09:00 -> KRC (today) & KSL-Toi (yesterday)")
    log("  15:00 -> KSL-Sang (today)")
    log("  16:30 -> DONG (today) & MAT (today)")
    log("-" * 60)
    log("Running in background... (Ctrl+C to stop)")

    while True:
        try:
            check_schedule()
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            log("Scheduler stopped by user.")
            break
        except Exception as e:
            log(f"Error in scheduler loop: {e}", "error")
            import traceback
            log(traceback.format_exc(), "error")
            time.sleep(60)


if __name__ == "__main__":
    main()
