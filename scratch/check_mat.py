# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

d = json.load(open("docs/data/performance.json", "r", encoding="utf-8"))
t = d.get("tracking", {})
dates = t.get("dates", {})
today = "2026-05-29"

print("=== MAT rows breakdown ===")
mat = dates.get(today, {}).get("MÁT", [])
print(f"Total MAT rows: {len(mat)}")

target = ["TRIP0000054004", "TRIP0000054005", "TRIP0000054006",
          "TRIP0000054007", "TRIP0000054008"]

print("\n=== These trips' MAT entries ===")
for r in mat:
    tid = r.get("trip", "")
    if tid in target:
        giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
        nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
        print(f"  {tid} | {r.get('dest', '-')} | giao={giao} nhận={nhan} | tote_t={r.get('tote_t')} carton_t={r.get('carton_t')} tote_r={r.get('tote_r')} carton_r={r.get('carton_r')}")

# Check report HTML output
import os
delivery_dir = os.path.join("docs", "delivery")
if os.path.isdir(delivery_dir):
    files = sorted(os.listdir(delivery_dir))
    print(f"\n=== Delivery HTML files ===")
    for f in files:
        if "2026-05-29" in f:
            print(f"  {f} ({os.path.getsize(os.path.join(delivery_dir, f)):,} bytes)")

# Now check the DONG report — user says Đông trips 54005/54020/54025 should show
print("\n=== ĐÔNG Report — user target trips ===")
dong = dates.get(today, {}).get("ĐÔNG", [])
user_dong_trips = ["TRIP0000054005", "TRIP0000054020", "TRIP0000054025"]
for r in dong:
    tid = r.get("trip", "")
    if tid in user_dong_trips:
        giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
        nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
        d = nhan - giao
        if d == 0 and giao > 0:
            st = "Đủ"
        elif d < 0:
            st = f"Thiếu {abs(d)}"
        elif d > 0:
            st = f"Dư {d}"
        else:
            st = "—"
        print(f"  {tid} | {r.get('dest', '-')} | giao={giao} nhận={nhan} | {st}")
