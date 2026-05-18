# -*- coding: utf-8 -*-
"""
Orchestrator Pipeline — Scan HTML reports and generate unified dashboard.

Usage:
    python script/orchestrator/pipeline.py              # one-shot
    python script/orchestrator/pipeline.py --watch      # re-generate every 30s
"""
import os, sys, io, glob, time, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS = os.path.join(REPO_ROOT, "output", "artifacts")
DASH_DIR = os.path.join(REPO_ROOT, "output", "dashboard")
TEMPLATE = os.path.join(DASH_DIR, "index.html")
OUTPUT = os.path.join(DASH_DIR, "dashboard.html")


def find_latest(pattern):
    """Find latest file matching glob pattern (by name, descending)."""
    files = sorted(glob.glob(pattern), reverse=True)
    return files[0] if files else None


def build_iframe(filepath):
    """Build iframe tag or empty state."""
    if not filepath or not os.path.exists(filepath):
        return '<div class="empty"><div class="icon">⏳</div><div>No reports yet</div></div>'
    rel = os.path.relpath(filepath, DASH_DIR).replace("\\", "/")
    return f'<iframe src="{rel}"></iframe>'


def generate_dashboard():
    """Read template, inject latest reports, write dashboard.html."""
    if not os.path.exists(TEMPLATE):
        print("  ⚠️  Template not found:", TEMPLATE)
        return

    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now()

    # Find latest report per domain
    # Daily: prefer BAO_CAO_DDMMYYYY.html (daily, has built-in date+period filters)
    daily_files = glob.glob(os.path.join(ARTIFACTS, "daily", "BAO_CAO_[0-9]*.html"))
    daily_latest = max(daily_files, key=os.path.getmtime) if daily_files else None
    
    perf_latest = find_latest(os.path.join(ARTIFACTS, "performance", "PERFORMANCE_REPORT_*.html"))
    
    # Inventory: prefer daily (has built-in date filters) over weekly
    inv_files = glob.glob(os.path.join(ARTIFACTS, "inventory", "report_doi_soat_[0-9]*.html"))
    inv_latest = max(inv_files, key=os.path.getmtime) if inv_files else find_latest(os.path.join(ARTIFACTS, "inventory", "report_doi_soat_*.html"))
    
    nso_latest = os.path.join(ARTIFACTS, "nso", "nso_dashboard.html")
    if not os.path.exists(nso_latest):
        nso_latest = None

    # Status dots
    html = html.replace("__PERF_DOT__", "ok" if perf_latest else "warn")
    html = html.replace("__INV_DOT__", "ok" if inv_latest else "warn")
    html = html.replace("__NSO_DOT__", "ok" if nso_latest else "warn")
    html = html.replace("__GENERATED_TIME__", now.strftime("%H:%M %d/%m/%Y"))

    # Iframes — direct to latest reports (reports have their own built-in filters)
    html = html.replace("__DAILY_IFRAME__", build_iframe(daily_latest))
    html = html.replace("__PERF_IFRAME__", build_iframe(perf_latest))
    html = html.replace("__INV_IFRAME__", build_iframe(inv_latest))
    html = html.replace("__NSO_IFRAME__", build_iframe(nso_latest))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Dashboard — {now.strftime('%H:%M:%S %d/%m/%Y')}")
    print(f"{'='*50}")
    for name, path in [("daily", daily_latest), ("performance", perf_latest), ("inventory", inv_latest), ("nso", nso_latest)]:
        if path:
            print(f"  {name:12s} ✅ {os.path.basename(path)}")
        else:
            print(f"  {name:12s} ⚠️  no reports")
    print(f"\n  📦 → {OUTPUT}")


def watch_mode(interval=30):
    print(f"  👁️  Watch mode — every {interval}s (Ctrl+C to stop)")
    try:
        while True:
            generate_dashboard()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  ⏹️  Stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dashboard Pipeline")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    if args.watch:
        generate_dashboard()
        watch_mode(args.interval)
    else:
        generate_dashboard()
