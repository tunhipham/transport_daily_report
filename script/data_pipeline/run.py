# -*- coding: utf-8 -*-
"""
Pipeline Runner — orchestrates extract → bronze → validate → silver.

Usage:
  python script/data_pipeline/run.py --date DD/MM/YYYY
  python script/data_pipeline/run.py --date today
  python script/data_pipeline/run.py --date today --domain daily
  python script/data_pipeline/run.py --date today --domain performance --week-start 2026-05-11 --week-end 2026-05-17
  python script/data_pipeline/run.py --date today --force  (override silver lock)
"""
import os
import sys
import argparse
from datetime import datetime, timedelta

# Setup paths
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


from data_pipeline.config import get_bronze_dir, get_silver_dir
from data_pipeline.validators import validate_and_promote
from lib.state_manager import StateManager, DataLockError


def run_daily_pipeline(date_tag: str, force: bool = False):
    """Run pipeline for daily report: transfer + KRC schedule."""
    sm = StateManager()

    # Check lock
    if not force:
        try:
            sm.check_write_allowed(date_tag)
        except DataLockError as e:
            print(f"  🔒 {e}")
            return False

    bronze_dir = get_bronze_dir(date_tag)
    silver_dir = get_silver_dir(date_tag)

    print(f"\n{'='*60}")
    print(f"  DAILY PIPELINE — {date_tag}")
    print(f"  Bronze: {bronze_dir}")
    print(f"  Silver: {silver_dir}")
    print(f"{'='*60}\n")

    # Step 1: Extract
    print("── EXTRACT ──")
    from data_pipeline.extractors.starrocks_transfer import StarrocksTransferExtractor
    from data_pipeline.extractors.clickhouse_schedules import StarrocksScheduleExtractor

    extractors = [
        StarrocksTransferExtractor(date_tag, bronze_dir),
        StarrocksScheduleExtractor(date_tag, bronze_dir),
    ]

    for ext in extractors:
        try:
            ext.run()
        except Exception as e:
            print(f"  ❌ Extractor {ext.name} failed: {e}")

    # Step 2: Validate & Promote
    print("\n── VALIDATE & PROMOTE ──")
    results = validate_and_promote(bronze_dir, silver_dir)

    # Summary
    print(f"\n── SUMMARY ──")
    print(f"  ✅ Promoted: {len(results['promoted'])} files")
    if results['failed']:
        print(f"  ❌ Failed: {len(results['failed'])} files")
    print()

    return len(results['failed']) == 0


def run_performance_pipeline(date_tag: str, week_start: str = None, week_end: str = None, force: bool = False):
    """Run pipeline for performance report: trip data."""
    sm = StateManager()

    if not force:
        try:
            sm.check_write_allowed(date_tag)
        except DataLockError as e:
            print(f"  🔒 {e}")
            return False

    bronze_dir = get_bronze_dir(date_tag)
    silver_dir = get_silver_dir(date_tag)

    print(f"\n{'='*60}")
    print(f"  PERFORMANCE PIPELINE — {date_tag}")
    if week_start:
        print(f"  Week: {week_start} → {week_end}")
    print(f"  Bronze: {bronze_dir}")
    print(f"  Silver: {silver_dir}")
    print(f"{'='*60}\n")

    # Step 1: Extract trips
    print("── EXTRACT ──")
    from data_pipeline.extractors.starrocks_trips import StarrocksTripsExtractor

    ext = StarrocksTripsExtractor(date_tag, bronze_dir, week_start=week_start, week_end=week_end)
    try:
        ext.run()
    except Exception as e:
        print(f"  ❌ Trips extractor failed: {e}")
        return False

    # Step 2: Validate & Promote
    print("\n── VALIDATE & PROMOTE ──")
    results = validate_and_promote(bronze_dir, silver_dir)

    print(f"\n── SUMMARY ──")
    print(f"  ✅ Promoted: {len(results['promoted'])} files")
    if results['failed']:
        print(f"  ❌ Failed: {len(results['failed'])} files")
    print()

    return len(results['failed']) == 0


def parse_date(date_str: str) -> str:
    """Parse date argument to DDMMYYYY tag."""
    if date_str.lower() == "today":
        return datetime.now().strftime("%d%m%Y")
    elif date_str.lower() == "yesterday":
        return (datetime.now() - timedelta(days=1)).strftime("%d%m%Y")
    else:
        # Try DD/MM/YYYY
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%d%m%Y")
        except ValueError:
            pass
        # Try DDMMYYYY
        if len(date_str) == 8 and date_str.isdigit():
            return date_str
        raise ValueError(f"Cannot parse date: {date_str}. Use DD/MM/YYYY, today, or yesterday.")


def main():
    parser = argparse.ArgumentParser(description="KFM Data Pipeline")
    parser.add_argument("--date", required=True, help="Target date: DD/MM/YYYY, today, yesterday")
    parser.add_argument("--domain", choices=["daily", "performance", "all"], default="all",
                        help="Which pipeline to run")
    parser.add_argument("--week-start", help="Week start YYYY-MM-DD (performance only)")
    parser.add_argument("--week-end", help="Week end YYYY-MM-DD (performance only)")
    parser.add_argument("--force", action="store_true", help="Override silver lock")
    args = parser.parse_args()

    date_tag = parse_date(args.date)
    print(f"🚀 KFM Data Pipeline — date_tag={date_tag}")

    # Session tracking
    sm = StateManager()
    session = sm.open_session(f"pipeline-{args.domain}")

    success = True
    try:
        if args.domain in ("daily", "all"):
            sm.log_step(session, "daily_pipeline", "running")
            ok = run_daily_pipeline(date_tag, force=args.force)
            sm.log_step(session, "daily_pipeline", "done" if ok else "failed")
            if not ok:
                success = False

        if args.domain in ("performance", "all"):
            sm.log_step(session, "performance_pipeline", "running")
            ok = run_performance_pipeline(date_tag, args.week_start, args.week_end, force=args.force)
            sm.log_step(session, "performance_pipeline", "done" if ok else "failed")
            if not ok:
                success = False

        sm.close_session(session, "success" if success else "partial")
    except Exception as e:
        sm.close_session(session, "failed", str(e))
        raise


if __name__ == "__main__":
    main()
