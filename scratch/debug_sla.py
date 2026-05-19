import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = r'G:\My Drive\DOCS\transport_daily_report'
sys.path.insert(0, BASE)

from script.domains.performance.generate import load_trip_data, load_thitca_data, calc_metrics, load_plan_data
from datetime import date, timedelta
from collections import Counter

# Reload T05 data (cache cleared)
rows = load_trip_data(5, 2026)
tc_rows = load_thitca_data([5])
all_rows = rows + tc_rows

w20_start = date(2026, 5, 11)
w20_end = date(2026, 5, 17)
w20_rows = [r for r in all_rows if r.get('date') and w20_start <= r['date'] <= w20_end]

# Count ĐÔNG MÁT with/without arrival
dm_rows = [r for r in w20_rows if r['kho'] == 'ĐÔNG MÁT']
dm_with_arrival = [r for r in dm_rows if r['arrival_time'] is not None]
print(f'ĐÔNG MÁT W20: {len(dm_rows)} total, {len(dm_with_arrival)} with arrival time')

# Calc metrics
plan_lookup, route_order = load_plan_data([3, 4, 5])
metrics = calc_metrics(all_rows, plan_lookup, route_order)

print('\n=== SLA Metrics for W20 (after fix) ===')
for kho in ['ĐÔNG MÁT', 'ĐÔNG', 'MÁT', 'THỊT CÁ']:
    print(f'\n{kho}:')
    for d in [w20_start + timedelta(days=i) for i in range(7)]:
        sla = metrics['sla'].get(kho, {}).get(d, {})
        trips = len(metrics['trips_per_day'].get(kho, {}).get(d, set()))
        trong = sla.get('trong', 0)
        som = sla.get('som', 0)
        tre = sla.get('tre', 0)
        total = trong + som + tre
        print(f"  {d}: total={total} trong={trong} som={som} tre={tre} trips={trips}")
