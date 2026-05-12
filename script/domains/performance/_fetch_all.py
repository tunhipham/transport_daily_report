"""
_fetch_all.py - Fetch monthly plan data for a range of months.
Helper for run-performance.bat to avoid batch for-loop issues.

Usage:
  python script/domains/performance/_fetch_all.py --year 2026 --start-month 3 --end-month 5
"""
import sys, subprocess, os

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--start-month", type=int, required=True)
    parser.add_argument("--end-month", type=int, required=True)
    args = parser.parse_args()

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    fetch_script = os.path.join(base, "script", "domains", "performance", "fetch_monthly.py")

    for m in range(args.start_month, args.end_month + 1):
        print(f"\n{'='*60}")
        print(f"  Fetching T{m:02d}/{args.year}...")
        print(f"{'='*60}")
        result = subprocess.run(
            [sys.executable, "-u", fetch_script, "--month", str(m), "--year", str(args.year)],
            cwd=base,
        )
        if result.returncode != 0:
            print(f"  [WARN] Fetch failed for month {m}")


if __name__ == "__main__":
    main()
