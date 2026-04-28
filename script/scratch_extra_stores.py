"""Check 83 extra ĐÔNG stores on 22/04 vs KH of other days."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import date, timedelta

plan_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\monthly_plan_T04.json'
with open(plan_path, 'r', encoding='utf-8') as f:
    plan_data = json.load(f)
dm_plan = plan_data['plan'].get('ĐÔNG MÁT', [])

cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)
rows = cache['rows']

# KH ĐÔNG ngày 22/04
target = '22/04/2026'
plan_22_dong = set(r['store'] for r in dm_plan if target in str(r.get('date','')) and str(r.get('tuyen','')).startswith('HĐ'))

# Actual ĐÔNG ngày 22/04
dong_actual = [r for r in rows if r.get('date') == '2026-04-22' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG']
dong_actual_stores = set(r['dest'] for r in dong_actual)

# 83 extra stores
extra_stores = sorted(dong_actual_stores - plan_22_dong)

# Build KH lookup: for each day, which stores are in HĐ plan?
kh_by_day = {}
for offset in range(-7, 8):
    d = date(2026, 4, 22) + timedelta(days=offset)
    d_str = d.strftime('%d/%m/%Y')
    d_stores = set(r['store'] for r in dm_plan if d_str in str(r.get('date','')) and str(r.get('tuyen','')).startswith('HĐ'))
    if d_stores:
        kh_by_day[d] = d_stores

# Also build actual lookup per day
actual_by_day = {}
for offset in range(-7, 8):
    d = date(2026, 4, 22) + timedelta(days=offset)
    d_actual = set(r['dest'] for r in rows if r.get('date') == d.isoformat() and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG')
    if d_actual:
        actual_by_day[d] = d_actual

# For each extra store, find which day(s) it appears in KH
print(f'| STT | Store | KH ngày nào? | Actual giao ngày nào? |')
print(f'|-----|-------|-------------|----------------------|')

for i, store in enumerate(extra_stores, 1):
    # Find in KH
    kh_days = []
    for d, stores in sorted(kh_by_day.items()):
        if store in stores:
            day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
            kh_days.append(f'{d.strftime("%d/%m")}({day_name})')
    
    # Find in actual
    act_days = []
    for d, stores in sorted(actual_by_day.items()):
        if store in stores:
            day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
            act_days.append(f'{d.strftime("%d/%m")}({day_name})')
    
    kh_str = ', '.join(kh_days) if kh_days else '—'
    act_str = ', '.join(act_days)
    print(f'| {i} | {store} | {kh_str} | {act_str} |')

# Summary: how many belong to 21/04 vs 23/04 vs other
print(f'\n=== SUMMARY ===')
d21 = date(2026, 4, 21)
d23 = date(2026, 4, 23)
from_21 = [s for s in extra_stores if s in kh_by_day.get(d21, set())]
from_23 = [s for s in extra_stores if s in kh_by_day.get(d23, set())]
from_other = [s for s in extra_stores if s not in kh_by_day.get(d21, set()) and s not in kh_by_day.get(d23, set())]

# Check all days
per_day_count = {}
for s in extra_stores:
    for d, stores in kh_by_day.items():
        if s in stores:
            per_day_count.setdefault(d, []).append(s)

print(f'83 stores dư thuộc KH ngày:')
for d in sorted(per_day_count.keys()):
    day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
    print(f'  {d.strftime("%d/%m")} ({day_name}): {len(per_day_count[d])} stores')

not_in_any = [s for s in extra_stores if not any(s in stores for stores in kh_by_day.values())]
print(f'  Không có trong KH ngày nào: {len(not_in_any)} stores')
if not_in_any:
    print(f'    {not_in_any}')
