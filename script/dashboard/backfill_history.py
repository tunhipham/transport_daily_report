"""
backfill_history.py — Backfill missing dates into history.json
=============================================================
Runs the data collection pipeline for specified dates and updates history.
Skips HTML rendering and Telegram — only updates history.json.

Usage:
    python script/dashboard/backfill_history.py --dates 16/03/2026 17/03/2026 18/03/2026 19/03/2026
"""
import os, sys, json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.path.insert(0, os.path.join(BASE, "script", "domains", "daily"))

from generate import (
    read_sthi_data, load_master_data, read_pt_data,
    calculate_summary, load_history, save_history,
)


def backfill_date(date_str, master_tl):
    """Collect data for a single date and return result dict."""
    parts = date_str.split("/")
    date_for_file = f"{parts[0]}.{parts[1]}.{parts[2]}"
    date_tag = f"{parts[0]}{parts[1]}{parts[2]}"

    print(f"\n{'='*50}")
    print(f"  Backfilling: {date_str}")
    print(f"{'='*50}")

    # STHI+XE
    print("\n  Reading STHI+XE...")
    sthi_rows, sthi_warnings = read_sthi_data(date_str, date_for_file, date_tag=date_tag)
    for w in sthi_warnings:
        print(f"    W: {w}")

    # PT
    print("  Reading PT data...")
    pt_rows, pt_warnings = read_pt_data(date_str, master_tl)
    for w in pt_warnings:
        print(f"    W: {w}")

    # Summary
    result = calculate_summary(sthi_rows, pt_rows, date_str)
    print(f"\n  Result: {result['total_tons']:.2f} tan, {result['total_xe']} xe, "
          f"{result['total_sthi']} ST, {result['total_items']:.0f} items")

    return result


def main():
    dates = []
    if "--dates" in sys.argv:
        idx = sys.argv.index("--dates")
        for i in range(idx + 1, len(sys.argv)):
            if sys.argv[i].startswith("--"):
                break
            dates.append(sys.argv[i])

    if not dates:
        print("Usage: python backfill_history.py --dates DD/MM/YYYY DD/MM/YYYY ...")
        return

    print(f"Loading master data...")
    master_tl = load_master_data()

    results = []
    for d in dates:
        try:
            r = backfill_date(d, master_tl)
            results.append(r)
        except Exception as e:
            print(f"  ERROR on {d}: {e}")
            import traceback
            traceback.print_exc()

    if not results:
        print("\nNo data collected.")
        return

    # Update history
    print(f"\n{'='*50}")
    print(f"  Updating history.json...")
    history = load_history()
    existing_dates = {h["date"] for h in history}
    added = 0
    for r in results:
        if r["date"] in existing_dates:
            # Replace existing entry
            history = [h for h in history if h["date"] != r["date"]]
        history.append({
            "date": r["date"],
            "total_sthi": r["total_sthi"],
            "total_items": r["total_items"],
            "total_xe": r["total_xe"],
            "total_tons": r["total_tons"],
            "khos": {k: {
                "san_luong_tan": v["san_luong_tan"],
                "sl_items": v.get("sl_items", 0),
                "sl_xe": v.get("sl_xe", 0),
                "sl_sthi": v.get("sl_sthi", 0),
            } for k, v in r["khos"].items()},
        })
        added += 1

    HISTORY_LIMIT = 365
    history.sort(key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y"))
    if len(history) > HISTORY_LIMIT:
        dropped = history[:-HISTORY_LIMIT]
        dropped_dates = [h["date"] for h in dropped]
        print(f"  ⚠️  HISTORY LIMIT ({HISTORY_LIMIT}) exceeded! "
              f"Dropping {len(dropped)} oldest: {', '.join(dropped_dates)}")
        print(f"      → Backup history.json TRƯỚC khi mất data!")
        history = history[-HISTORY_LIMIT:]
    save_history(history)

    print(f"  Added/updated {added} entries. Total history: {len(history)} entries")

    # Show summary
    print(f"\n{'='*50}")
    print("  Summary of backfilled dates:")
    print(f"  {'Date':<12} {'Tan':>8} {'Xe':>5} {'ST':>5} {'Items':>10}")
    for r in results:
        print(f"  {r['date']:<12} {r['total_tons']:>8.2f} {r['total_xe']:>5} "
              f"{r['total_sthi']:>5} {r['total_items']:>10,.0f}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
