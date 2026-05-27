# -*- coding: utf-8 -*-
"""
trip_cutoff_export.py — Tuesday 09:00 cutoff: export final Excel files
======================================================================
At Tuesday 9:00 AM (cutoff), generate the performance report Excel files
for the previous week and send a Telegram notification with the files ready.

Usage:
    python script/telegram/trip_cutoff_export.py              # Run full
    python script/telegram/trip_cutoff_export.py --dry-run    # Preview
    python script/telegram/trip_cutoff_export.py --notify-only  # Just Telegram
"""
import os, sys, json, argparse, subprocess
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUTPUT = os.path.join(BASE, "output")


def load_config():
    tg_path = os.path.join(BASE, "config", "telegram.json")
    with open(tg_path, encoding="utf-8") as f:
        return json.load(f)


def get_cutoff_dates():
    """Get the week date range for cutoff.
    Cutoff is Tuesday 09:00 for the previous week (Mon-Sun).
    """
    today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    prev_monday = this_monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6)
    week_num = prev_monday.isocalendar()[1]
    return prev_monday, prev_sunday, week_num


def run_performance_report(end_date_str, month, year):
    """Run generate.py --realtime with end-date cutoff."""
    cmd = [
        sys.executable, "-u",
        os.path.join(BASE, "script", "domains", "performance", "generate.py"),
        "--realtime",
        "--months", str(month),
        "--year", str(year),
        "--end-date", end_date_str,
    ]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ⚠ stderr: {result.stderr}")
    return result.returncode == 0


def find_output_files(month, year):
    """Find generated Excel/HTML files."""
    perf_dir = os.path.join(OUTPUT, "artifacts", "performance")
    files = []
    if os.path.isdir(perf_dir):
        month_str = f"T{month:02d}"
        for f in os.listdir(perf_dir):
            if month_str in f and str(year) in f and (f.endswith('.xlsx') or f.endswith('.html')):
                files.append(os.path.join(perf_dir, f))
    return files


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


def send_telegram_file(bot_token, chat_id, filepath, caption=""):
    """Send a file via Telegram."""
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    with open(filepath, "rb") as f:
        r = requests.post(url,
                          data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                          files={"document": (os.path.basename(filepath), f)},
                          timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Trip cutoff — T3 09:00 export")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")
    parser.add_argument("--notify-only", action="store_true", help="Only send Telegram notification")
    args = parser.parse_args()

    now = datetime.now()
    print(f"{'='*60}")
    print(f"  ✂️ Trip Cutoff Export — {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}")

    prev_monday, prev_sunday, week_num = get_cutoff_dates()
    month = prev_sunday.month
    year = prev_sunday.year
    end_date_str = prev_sunday.strftime("%d/%m/%Y")

    print(f"  W{week_num}: {prev_monday.strftime('%d/%m/%Y')} → {end_date_str}")
    print(f"  Month: T{month:02d}/{year}")

    telegram_cfg = load_config()
    bot_token = telegram_cfg["trip_reminder"]["bot_token"]
    chat_id = telegram_cfg["trip_reminder"]["chat_id"]

    if args.notify_only:
        msg = (
            f"⏰ <b>CUTOFF T3 09:00 — W{week_num}</b>\n\n"
            f"Chạy <code>run-trip-cutoff.bat</code> hoặc:\n"
            f"<code>python script/telegram/trip_cutoff_export.py</code>\n\n"
            f"Để xuất Excel báo cáo tuần W{week_num}."
        )
        if not args.dry_run:
            send_telegram(bot_token, chat_id, msg)
            print(f"  ✅ Notification sent!")
        else:
            print(f"  [DRY RUN] {msg}")
        return

    if args.dry_run:
        print(f"  [DRY RUN] Would run performance report with --end-date {end_date_str}")
        return

    # Run performance report
    print(f"\n  📊 Running performance report...")
    success = run_performance_report(end_date_str, month, year)

    if not success:
        msg = f"❌ <b>Cutoff W{week_num} FAILED</b>\nPerformance report generation failed!"
        send_telegram(bot_token, chat_id, msg)
        return

    # Find output files
    output_files = find_output_files(month, year)
    print(f"\n  📁 Output files: {len(output_files)}")
    for f in output_files:
        print(f"    {os.path.basename(f)}")

    # Send notification
    msg = (
        f"✅ <b>Cutoff W{week_num} — Done!</b>\n\n"
        f"📅 {prev_monday.strftime('%d/%m')} → {prev_sunday.strftime('%d/%m/%Y')}\n"
        f"📁 {len(output_files)} file(s) ready\n\n"
        f"Files in: <code>output/artifacts/performance/</code>"
    )
    send_telegram(bot_token, chat_id, msg)

    # Send Excel files via Telegram
    for fpath in output_files:
        if fpath.endswith('.xlsx'):
            try:
                send_telegram_file(bot_token, chat_id, fpath,
                                   caption=f"📊 W{week_num} — {os.path.basename(fpath)}")
                print(f"  ✅ Sent: {os.path.basename(fpath)}")
            except Exception as e:
                print(f"  ⚠ Failed to send {os.path.basename(fpath)}: {e}")

    print(f"\n{'='*60}")
    print(f"  ✅ Cutoff W{week_num} complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
