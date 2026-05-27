# -*- coding: utf-8 -*-
"""
push_compose_plan.py — Extract planned delivery times from compose-mail state
==============================================================================
Reads auto_compose_state.json and outputs a simple lookup JSON for tracking.

Output: output/state/tracking_plan.json
Format: { "DD/MM/YYYY": { "kho_store": "HH:MM", ... } }

Usage:
    python script/domains/performance/push_compose_plan.py
"""
import os, sys, json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTPUT = os.path.join(BASE, "output")

# Kho name mapping from compose state keys
KHO_MAP = {
    "KRC": "KRC",
    "DRY_sang": "KSL-Sáng",
    "DRY_toi": "KSL-Tối",
    "ĐÔNG MÁT": "ĐÔNG MÁT",
    "THỊT CÁ": "THỊT CÁ",
}


def push():
    compose_path = os.path.join(OUTPUT, "state", "auto_compose_state.json")
    if not os.path.exists(compose_path):
        print("  ⚠ auto_compose_state.json not found")
        return {}

    with open(compose_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Build lookup: date → { "kho|store": "HH:MM" }
    lookup = {}
    total = 0

    for date_key, day_data in state.items():
        # date_key = "2026-05-26"
        if not isinstance(day_data, dict):
            continue

        for kho_key, kho_data in day_data.items():
            if not isinstance(kho_data, dict):
                continue
            if "_watch" in kho_key:
                continue

            # Map kho name
            display_kho = KHO_MAP.get(kho_key, kho_key)

            rows = kho_data.get("prev_rows_snapshot", [])
            for row in rows:
                if not isinstance(row, dict):
                    continue
                date_str = row.get("date", "")  # "DD/MM/YYYY"
                dest = row.get("diem_den", "")
                gio = row.get("gio_den", "")
                if date_str and dest and gio:
                    if date_str not in lookup:
                        lookup[date_str] = {}
                    # For ĐÔNG MÁT, we don't know sub-kho from compose → store under both
                    key = f"{display_kho}|{dest}"
                    lookup[date_str][key] = gio
                    total += 1

    # Save
    out_path = os.path.join(OUTPUT, "state", "tracking_plan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, indent=2)

    dates = sorted(lookup.keys())
    print(f"  📋 Tracking plan: {total} entries across {len(dates)} dates")
    if dates:
        print(f"    Dates: {dates[0]} → {dates[-1]}")

    return lookup


if __name__ == "__main__":
    push()
