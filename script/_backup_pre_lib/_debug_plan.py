import sys, io, openpyxl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import defaultdict

wb = openpyxl.load_workbook('output/RAW_DATA_T03+T04_2026.xlsx', read_only=True)
ws = wb.active

# Count by (kho, date): total with arrival, missing plan
stats = defaultdict(lambda: {"total": 0, "has_plan": 0, "no_plan": 0})

for row in ws.iter_rows(min_row=2, values_only=True):
    tuyen, ngay, thu, kho, giao, trip, diem, gio_den, gio_kh, dung_tuyen, sla, plan = row[:12]
    if giao != "Y":
        continue  # Only count delivered rows
    key = (kho, ngay)
    stats[key]["total"] += 1
    if gio_kh:
        stats[key]["has_plan"] += 1
    else:
        stats[key]["no_plan"] += 1

wb.close()

# Group by kho, show dates with missing plan
print("=" * 80)
print("MISSING PLANNED TIME ANALYSIS")
print("=" * 80)

kho_dates = defaultdict(list)
for (kho, ngay), s in stats.items():
    if s["no_plan"] > 0:
        kho_dates[kho].append((ngay, s["total"], s["has_plan"], s["no_plan"]))

if not kho_dates:
    print("\n✅ ALL rows with delivery have planned time!")
else:
    total_missing = 0
    for kho in sorted(kho_dates.keys()):
        dates = sorted(kho_dates[kho], key=lambda x: x[0].split('/')[::-1])
        total_kho = sum(d[3] for d in dates)
        total_missing += total_kho
        print(f"\n{'─' * 60}")
        print(f"❌ {kho}: {len(dates)} ngày thiếu, tổng {total_kho} rows thiếu")
        print(f"{'─' * 60}")
        print(f"  {'Ngày':<14} {'Tổng':>6} {'Có KH':>6} {'Thiếu':>6} {'%Thiếu':>8}")
        for ngay, total, has, no in dates:
            pct = no / total * 100
            print(f"  {ngay:<14} {total:>6} {has:>6} {no:>6} {pct:>7.1f}%")
    
    # Summary
    total_all = sum(s["total"] for s in stats.values())
    total_has = sum(s["has_plan"] for s in stats.values())
    print(f"\n{'=' * 60}")
    print(f"TỔNG: {total_has}/{total_all} có KH ({total_has/total_all*100:.1f}%), thiếu {total_missing} rows")
    print(f"{'=' * 60}")
