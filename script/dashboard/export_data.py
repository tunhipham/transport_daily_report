"""
export_data.py — Export JSON data for the live dashboard
=========================================================
Reads existing state/cache files and generates JSON for each domain tab.
Output: docs/data/{daily,performance,inventory,nso}.json

Usage:
    python script/dashboard/export_data.py [--domain daily|performance|inventory|nso|all]
"""
import os, sys, json, math, argparse
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "script"))
OUTPUT = os.path.join(BASE, "output")
DOCS_DATA = os.path.join(BASE, "docs", "data")
os.makedirs(DOCS_DATA, exist_ok=True)

NOW_STR = datetime.now().strftime("%d/%m/%Y %H:%M")


# ══════════════════════════════════════════════════════════════
# DAILY
# ══════════════════════════════════════════════════════════════
def export_daily():
    """Export daily report data from history.json"""
    print("📦 Exporting Daily data...")
    history_file = os.path.join(OUTPUT, "state", "history.json")
    if not os.path.exists(history_file):
        print("  ⚠ history.json not found")
        return False

    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    if not history:
        print("  ⚠ Empty history")
        return False

    REPORT_KHOS = ["KRC", "THỊT CÁ", "ĐÔNG MÁT", "KSL-SÁNG", "KSL-TỐI"]
    KHO_COLORS = {"KRC": "#4caf50", "THỊT CÁ": "#e53935", "ĐÔNG MÁT": "#1e88e5",
                  "KSL-SÁNG": "#ff9800", "KSL-TỐI": "#9c27b0"}

    # Build current (latest entry)
    current = history[-1]

    # Ensure all entries have per-kho sl_sthi
    for entry in history:
        has_sthi = any(entry.get("khos", {}).get(k, {}).get("sl_sthi", 0) > 0 for k in REPORT_KHOS)
        if not has_sthi and entry.get("total_sthi", 0) > 0:
            total_xe = sum(entry.get("khos", {}).get(k, {}).get("sl_xe", 0) for k in REPORT_KHOS)
            if total_xe > 0:
                for kho in REPORT_KHOS:
                    kd = entry.get("khos", {}).get(kho, {})
                    kd["sl_sthi"] = round(entry["total_sthi"] * kd.get("sl_xe", 0) / total_xe)

    # Round values
    for entry in history:
        entry["total_items"] = round(entry.get("total_items", 0), 1)
        entry["total_tons"] = round(entry.get("total_tons", 0), 4)
        for kho in REPORT_KHOS:
            kd = entry.get("khos", {}).get(kho, {})
            kd["san_luong_tan"] = round(kd.get("san_luong_tan", 0), 4)
            kd["sl_items"] = round(kd.get("sl_items", 0), 1)

    data = {
        "_updated": NOW_STR,
        "current": current,
        "history": history,
        "kho_list": REPORT_KHOS,
        "kho_colors": KHO_COLORS,
    }

    out_path = os.path.join(DOCS_DATA, "daily.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✅ {out_path} ({len(history)} entries, {os.path.getsize(out_path):,} bytes)")
    return True


# ══════════════════════════════════════════════════════════════
# PERFORMANCE
# ══════════════════════════════════════════════════════════════
def export_performance():
    """Export performance data by running metrics calculation from cached trip data."""
    print("🚛 Exporting Performance data...")

    # Import the performance generate module
    perf_dir = os.path.join(BASE, "script", "domains", "performance")
    sys.path.insert(0, perf_dir)

    try:
        from generate import (
            load_trip_data, load_thitca_data, load_plan_data,
            calc_metrics, prepare_chart_data, generate_summary_cards,
            generate_weekly_tables, KHO_COLORS
        )
    except ImportError as e:
        print(f"  ⚠ Cannot import performance generate: {e}")
        return False

    # Determine current month
    now = datetime.now()
    month = now.month
    year = now.year

    # Check if we're early in month (might need previous month data too)
    months = [month]
    if now.day <= 5 and month > 1:
        months = [month - 1, month]

    print(f"  → Processing months: {months}")

    # Load data
    all_rows = []
    for m in months:
        rows = load_trip_data(m, year)
        all_rows.extend(rows)

    # Load THỊT CÁ data
    tc_rows = load_thitca_data(months)
    all_rows.extend(tc_rows)

    if not all_rows:
        print("  ⚠ No trip data found")
        return False

    # Load plan
    plan_lookup, route_order = load_plan_data(months)

    # Filter to current month
    from datetime import date as ddate
    month_dates = set()
    for r in all_rows:
        if r.get("date") and r["date"].month == month and r["date"].year == year:
            month_dates.add(r["date"])

    dates = sorted(month_dates)
    if not dates:
        print("  ⚠ No dates found for current month")
        return False

    # Calculate metrics
    month_rows = [r for r in all_rows if r.get("date") and r["date"].month == month and r["date"].year == year]
    metrics = calc_metrics(month_rows, plan_lookup, route_order)

    # Prepare chart data
    labels, charts, iso_dates = prepare_chart_data(metrics, dates, month, year)

    # Generate cards
    cards = generate_summary_cards(metrics, month_rows)

    # Generate weekly tables HTML
    weekly_html = generate_weekly_tables(metrics, dates)

    # Serialize
    kho_names = list(KHO_COLORS.keys())

    data = {
        "_updated": NOW_STR,
        "month": month,
        "year": year,
        "labels": labels,
        "charts": charts,
        "cards": cards,
        "kho_names": kho_names,
        "kho_colors": KHO_COLORS,
        "iso_dates": iso_dates,
        "weekly_tables_html": weekly_html,
    }

    out_path = os.path.join(DOCS_DATA, "performance.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✅ {out_path} ({len(dates)} dates, {os.path.getsize(out_path):,} bytes)")
    return True


# ══════════════════════════════════════════════════════════════
# INVENTORY
# ══════════════════════════════════════════════════════════════
def export_inventory():
    """Export inventory reconciliation data."""
    print("📋 Exporting Inventory data...")

    inv_dir = os.path.join(BASE, "script", "domains", "inventory")
    sys.path.insert(0, inv_dir)

    try:
        from generate import load_master_data, load_weight_data, load_doi_soat_files, compute_stats, acc_precise
    except ImportError as e:
        print(f"  ⚠ Cannot import inventory generate: {e}")
        return False

    try:
        category_map = load_master_data()
        weight_map = load_weight_data()
        all_days = load_doi_soat_files()

        if not all_days:
            print("  ⚠ No reconciliation data found")
            return False

        daily_stats, _, _ = compute_stats(all_days, category_map, weight_map)
    except Exception as e:
        print(f"  ⚠ Error loading inventory data: {e}")
        return False

    if not daily_stats:
        print("  ⚠ No daily stats computed")
        return False

    target = daily_stats[-1]
    cats = ['ĐÔNG', 'MÁT', 'TCNK']

    # Compute trend data
    trend_dates = []
    trend_item_kfm, trend_item_aba, trend_item_acc = [], [], []
    trend_sku_kfm, trend_sku_aba, trend_sku_acc = [], [], []
    trend_kg_kfm, trend_kg_aba, trend_kg_acc = [], [], []

    for ds in daily_stats:
        trend_dates.append(ds['date_str'])
        t_item_kfm = sum(ds['categories'][c]['item_KFM'] for c in cats)
        t_item_lech = sum(ds['categories'][c]['item_lech'] for c in cats)
        t_sku_total = sum(ds['categories'][c]['sku'] for c in cats)
        t_sku_lech = sum(ds['categories'][c]['sku_lech'] for c in cats)
        t_kg_kfm = sum(ds['categories'][c]['kg_KFM'] for c in cats)
        t_kg_lech = sum(ds['categories'][c]['kg_lech'] for c in cats)

        trend_item_kfm.append(t_item_kfm)
        trend_item_aba.append(t_item_kfm - t_item_lech)
        trend_item_acc.append(acc_precise(t_item_lech, t_item_kfm))
        trend_sku_kfm.append(t_sku_total)
        trend_sku_aba.append(t_sku_total - t_sku_lech)
        trend_sku_acc.append(acc_precise(t_sku_lech, t_sku_total))
        trend_kg_kfm.append(round(t_kg_kfm, 2))
        trend_kg_aba.append(round(t_kg_kfm - t_kg_lech, 2))
        trend_kg_acc.append(acc_precise(t_kg_lech, t_kg_kfm))

    # Overall accuracy for target day
    t_totals = target['totals']
    overall_acc = {
        'item': acc_precise(t_totals['item_lech'], t_totals['item_KFM']),
        'sku': acc_precise(t_totals['sku_lech'], t_totals['sku']),
        'kg': acc_precise(t_totals['kg_lech'], t_totals['kg_KFM']),
    }

    # Serialize target day (remove datetime objects)
    target_serial = {
        'date_str': target['date_str'],
        'total_sku': t_totals['sku'],
        'categories': {},
    }
    for cat in cats:
        cs = target['categories'][cat]
        target_serial['categories'][cat] = {
            'sku': cs['sku'],
            'item_KFM': cs['item_KFM'],
            'item_ABA': cs['item_ABA'],
            'kg_KFM': round(cs['kg_KFM'], 2),
            'kg_ABA': round(cs['kg_ABA'], 2),
        }

    data = {
        "_updated": NOW_STR,
        "target_day": target_serial,
        "overall_accuracy": overall_acc,
        "trend": {
            "dates": trend_dates,
            "item_kfm": trend_item_kfm,
            "item_aba": trend_item_aba,
            "item_acc": trend_item_acc,
            "sku_kfm": trend_sku_kfm,
            "sku_aba": trend_sku_aba,
            "sku_acc": trend_sku_acc,
            "kg_kfm": trend_kg_kfm,
            "kg_aba": trend_kg_aba,
            "kg_acc": trend_kg_acc,
        },
    }

    out_path = os.path.join(DOCS_DATA, "inventory.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✅ {out_path} ({len(daily_stats)} days, {os.path.getsize(out_path):,} bytes)")
    return True


# ══════════════════════════════════════════════════════════════
# NSO
# ══════════════════════════════════════════════════════════════
def export_nso():
    """Export NSO dashboard data."""
    print("🏪 Exporting NSO data...")

    nso_dir = os.path.join(BASE, "script", "domains", "nso")
    sys.path.insert(0, nso_dir)

    try:
        from generate import (
            STORES, VERSION_RULES, DONG_MAT_KG,
            get_status, get_display_name, get_short_label,
            parse_date, fmt_ddmm, day_name, week_range,
            replenishment_stores, build_schedule
        )
    except ImportError as e:
        print(f"  ⚠ Cannot import NSO generate: {e}")
        return False

    today = date.today()
    mon, sun = week_range(today)

    # Active stores
    active = []
    for s in STORES:
        st = get_status(s, today)
        if st:
            active.append((s, st))

    # Stats
    n_total = len(active)
    n_upcoming = sum(1 for _, st in active if st["type"] == "upcoming")
    n_opening = sum(1 for _, st in active if st["type"] == "opening")
    n_resched = sum(1 for _, st in active if st["type"] == "reschedule")

    # Store list for table
    stores_list = []
    for s, st in active:
        d = parse_date(s["opening_date"])
        stores_list.append({
            "name": get_display_name(s),
            "code": s["code"],
            "opening_date": s["opening_date"],
            "iso_date": d.isoformat(),
            "status_type": st["type"],
            "status_text": st["text"],
        })

    # Calendar events
    cal_events = []
    for s, st in active:
        d = parse_date(s["opening_date"])
        cal_events.append({
            "date": d.isoformat(),
            "label": get_short_label(s),
            "code": s["code"],
            "type": st["type"],
        })

    # Replenishment schedules
    rep_stores = replenishment_stores(STORES, today)
    schedules_data = []
    for s in rep_stores:
        sched = build_schedule(s)
        if not sched:
            continue
        days_data = []
        for d in sched["days"]:
            days_data.append({
                "date": fmt_ddmm(d["date"]),
                "day_name": day_name(d["date"]),
                "label": d["label"],
                "ksl": d["ksl"],
                "dm": d["dm"],
            })
        from generate import get_display_name_code
        schedules_data.append({
            "label": get_display_name_code(s),
            "version": s["version"],
            "days": days_data,
            "total_ksl": sched["total_ksl"],
            "total_dm": sched["total_dm"],
        })

    # Version rules (serializable)
    version_rules_data = {}
    for ver, rules in VERSION_RULES.items():
        version_rules_data[str(ver)] = rules

    data = {
        "_updated": NOW_STR,
        "stats": {
            "total": n_total,
            "upcoming": n_upcoming,
            "opening": n_opening,
            "reschedule": n_resched,
        },
        "stores": stores_list,
        "calendar_events": cal_events,
        "schedules": schedules_data,
        "version_rules": version_rules_data,
        "week_range": f"{fmt_ddmm(mon)} → {fmt_ddmm(sun)}",
    }

    # Write to output/nso/ first
    nso_output_dir = os.path.join(BASE, "output", "nso")
    os.makedirs(nso_output_dir, exist_ok=True)
    nso_output_path = os.path.join(nso_output_dir, "nso.json")
    with open(nso_output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  📁 {nso_output_path} ({n_total} stores, {os.path.getsize(nso_output_path):,} bytes)")

    # Copy to docs/data/ for dashboard
    out_path = os.path.join(DOCS_DATA, "nso.json")
    import shutil
    shutil.copy2(nso_output_path, out_path)
    print(f"  ✅ {out_path} ({os.path.getsize(out_path):,} bytes)")
    return True


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Export dashboard JSON data")
    parser.add_argument("--domain", default="all",
                        choices=["all", "daily", "performance", "inventory", "nso"],
                        help="Which domain to export (default: all)")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  📊 Dashboard Data Export — {NOW_STR}")
    print(f"  Output: {DOCS_DATA}")
    print(f"{'='*60}")

    exporters = {
        "daily": export_daily,
        "performance": export_performance,
        "inventory": export_inventory,
        "nso": export_nso,
    }

    if args.domain == "all":
        results = {}
        for name, fn in exporters.items():
            try:
                results[name] = fn()
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                results[name] = False
        ok = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"\n{'='*60}")
        print(f"  ✅ {ok}/{total} domains exported successfully")
        for name, success in results.items():
            print(f"    {'✅' if success else '❌'} {name}")
        print(f"{'='*60}")
    else:
        fn = exporters[args.domain]
        try:
            fn()
        except Exception as e:
            print(f"  ❌ {args.domain}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
