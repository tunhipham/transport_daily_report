# -*- coding: utf-8 -*-
"""
Auto-scheduler for KFM Delivery Reports.

Modes:
  --once     Run check_schedule() once and exit.  (Recommended: use with Windows Task Scheduler)
  (default)  Run continuously with while-True loop (legacy, fragile).
  --run-batch morning|afternoon|late   Force a specific batch NOW (ignores time check).

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
import argparse
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


# ── Batch definitions ────────────────────────────────────────
# Each batch: (name, trigger_hour, actions)
# actions is a list of (kho, date_func, pilot_flag)
BATCHES = [
    ("morning_batch",   9, [
        ("KRC",      "today",     True),
        ("KSL-Tối",  "yesterday", True),
    ]),
    ("afternoon_batch", 15, [
        ("KSL-Sáng", "today",     False),
    ]),
    ("late_batch",      17, [
        ("ĐÔNG",     "today",     False),
        ("MÁT",      "today",     False),
    ]),
]


def run_batch(batch_name, today_str, yesterday_str):
    """Execute a single batch by name. Returns True if it ran."""
    for name, _, actions in BATCHES:
        if name == batch_name:
            log(f"=== [{batch_name.upper()} FORCED] at {datetime.now().strftime('%H:%M:%S')} ===")
            sync_tracking_data()
            for kho, date_key, pilot in actions:
                d = today_str if date_key == "today" else yesterday_str
                send_report(kho, d, is_pilot=pilot)
            return True
    log(f"Unknown batch: {batch_name}", "error")
    return False


def check_schedule(force_batch=None):
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    state = load_state()
    if today_str not in state:
        state[today_str] = []

    sent_today = state[today_str]

    # ── Force a specific batch (--run-batch) ──
    if force_batch:
        if force_batch in sent_today:
            log(f"Batch '{force_batch}' already sent today, forcing re-send...")
            sent_today.remove(force_batch)
        run_batch(force_batch, today_str, yesterday_str)
        sent_today.append(force_batch)
        save_state(state)
        log(f"{force_batch} completed (forced).")
        return

    # ── Normal schedule check ──
    data_synced = False
    for batch_name, trigger_hour, actions in BATCHES:
        if now.hour >= trigger_hour and batch_name not in sent_today:
            log(f"=== [{batch_name.upper()} TRIGGERED] at {now.strftime('%H:%M:%S')} ===")
            if not data_synced:
                sync_tracking_data()
                data_synced = True
            for kho, date_key, pilot in actions:
                d = today_str if date_key == "today" else yesterday_str
                send_report(kho, d, is_pilot=pilot)
            sent_today.append(batch_name)
            save_state(state)
            log(f"{batch_name} completed.")

    # ── Cleanup: remove state entries older than 7 days ──
    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    old_keys = [k for k in state if k < cutoff]
    for k in old_keys:
        del state[k]
    if old_keys:
        save_state(state)


def _log_banner(mode_label):
    log("=" * 60)
    log(f"AUTO-SCHEDULER BAO CAO GIAO HANG — {mode_label}")
    log(f"Time: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    log(f"PID: {os.getpid()}")
    log(f"Log file: {LOG_FILE}")
    log("=" * 60)
    log("Schedule:")
    for name, hour, actions in BATCHES:
        khos = " & ".join(k for k, _, _ in actions)
        log(f"  {hour:02d}:00 -> {khos}")
    log("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="KFM Delivery Report Scheduler")
    parser.add_argument("--once", action="store_true",
                        help="Run check_schedule() once and exit (for Task Scheduler)")
    parser.add_argument("--run-batch", choices=["morning_batch", "afternoon_batch", "late_batch"],
                        help="Force a specific batch NOW (ignores time/state)")
    args = parser.parse_args()

    if args.run_batch:
        _log_banner(f"FORCE {args.run_batch}")
        check_schedule(force_batch=args.run_batch)
        log("Done.")
        return

    if args.once:
        _log_banner("once")
        try:
            check_schedule()
        except Exception as e:
            log(f"Error in check_schedule: {e}", "error")
            import traceback
            log(traceback.format_exc(), "error")
            sys.exit(1)
        log("Done (--once).")
        return

    # ── Legacy: continuous loop ──
    _log_banner("started (loop)")
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
