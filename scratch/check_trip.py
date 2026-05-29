# -*- coding: utf-8 -*-
"""Check tracking data for specific trips in performance.json"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERF = os.path.join(BASE, "docs", "data", "performance.json")

with open(PERF, "r", encoding="utf-8") as f:
    data = json.load(f)

tracking = data.get("tracking", {})
dates = tracking.get("dates", {})
today = "2026-05-29"

print(f"=== performance.json ===")
print(f"_updated: {data.get('_updated', '?')}")
print(f"tracking.latest_date: {tracking.get('latest_date', '?')}")
print(f"Available tracking dates: {sorted(dates.keys())[-5:]}")
print()

# Check all khos for today
print(f"=== Khos for {today} ===")
today_data = dates.get(today, {})
for kho, rows in today_data.items():
    trips = set(r.get("trip", "") for r in rows if r.get("trip"))
    print(f"  {kho}: {len(rows)} rows, {len(trips)} trips")
    for t in sorted(trips):
        print(f"    {t}")

# Target trips
target_trips = [
    "TRIP0000054004", "TRIP0000054005", "TRIP0000054006",
    "TRIP0000054007", "TRIP0000054008",
    "TRIP0000054020", "TRIP0000054025",
]

print()
print("=== Target trip check ===")
all_rows = []
for kho, rows in today_data.items():
    for r in rows:
        r["_kho"] = kho
        all_rows.append(r)

found_trips = {r.get("trip") for r in all_rows}

for tid in target_trips:
    if tid in found_trips:
        matching = [r for r in all_rows if r.get("trip") == tid]
        for r in matching:
            giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
            nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
            print(f"  ✅ {tid} | {r['_kho']} | {r.get('dest','-')} | giao={giao} nhận={nhan}")
    else:
        print(f"  ❌ {tid} — MISSING from tracking data")

# Also check if these trips exist in other dates
print()
print("=== Search in all dates ===")
for tid in target_trips:
    found_dates = []
    for dt, kho_data in dates.items():
        for kho, rows in kho_data.items():
            for r in rows:
                if r.get("trip") == tid:
                    found_dates.append(f"{dt}/{kho}/{r.get('dest','?')}")
    if found_dates:
        print(f"  {tid}: {found_dates}")
    else:
        print(f"  {tid}: NOT found in any date")
