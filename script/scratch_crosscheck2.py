"""Check: 83 extra stores on 22/04 — did they ALSO deliver on 21/04 and 23/04?"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import date, timedelta

cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)
rows = cache['rows']

plan_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\monthly_plan_T04.json'
with open(plan_path, 'r', encoding='utf-8') as f:
    plan_data = json.load(f)
dm_plan = plan_data['plan'].get('ĐÔNG MÁT', [])

# KH ĐÔNG 22/04
plan_22_dong = set(r['store'] for r in dm_plan if '22/04/2026' in str(r.get('date','')) and str(r.get('tuyen','')).startswith('HĐ'))

# Actual ĐÔNG 22/04
dong_actual_22 = set(r['dest'] for r in rows if r.get('date') == '2026-04-22' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG')
extra_stores = sorted(dong_actual_22 - plan_22_dong)

# Check each nearby day: did these 83 stores ALSO deliver?
print(f'83 stores dư ngày 22/04 — kiểm tra actual giao các ngày lân cận:')
print(f'{"="*70}')

for offset in [-3, -2, -1, 0, 1, 2, 3]:
    d = date(2026, 4, 22) + timedelta(days=offset)
    d_str = d.isoformat()
    day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
    
    # Actual ĐÔNG on this day
    dong_day = set(r['dest'] for r in rows if r.get('date') == d_str and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG')
    
    # How many of the 83 extras also appear on this day?
    overlap = set(extra_stores) & dong_day
    
    marker = ' <<<< (ngày bị dư)' if offset == 0 else ''
    print(f'  {d.strftime("%d/%m")} ({day_name}): Tổng ĐÔNG={len(dong_day):3d} stores | 83 stores dư có giao: {len(overlap):3d}/{len(extra_stores)}{marker}')

# So: on 21/04, how many of the 83 were delivered?
dong_21 = set(r['dest'] for r in rows if r.get('date') == '2026-04-21' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG')
dong_23 = set(r['dest'] for r in rows if r.get('date') == '2026-04-23' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG')

overlap_21 = set(extra_stores) & dong_21
overlap_23 = set(extra_stores) & dong_23

print(f'\n{"="*70}')
print(f'KẾT LUẬN:')
print(f'  83 stores dư ngày 22/04:')
print(f'    - Cũng giao ngày 21/04: {len(overlap_21)} stores')
print(f'    - Cũng giao ngày 23/04: {len(overlap_23)} stores')
print(f'    - Chỉ giao 22/04 (không giao 21 và 23): {len(set(extra_stores) - dong_21 - dong_23)} stores')

# Detail: stores NOT on 21 and NOT on 23
only_22 = sorted(set(extra_stores) - dong_21 - dong_23)
if only_22:
    print(f'\n  Stores CHỈ giao 22/04 (không có 21 và 23):')
    for s in only_22:
        print(f'    {s}')

# Ngày 21 có hụt gì không?
plan_21_dong = set(r['store'] for r in dm_plan if '21/04/2026' in str(r.get('date','')) and str(r.get('tuyen','')).startswith('HĐ'))
print(f'\n{"="*70}')
print(f'Ngày 21/04:')
print(f'  KH hàng đông: {len(plan_21_dong)} stores')
print(f'  Actual: {len(dong_21)} stores')
print(f'  KH nhưng không giao: {len(plan_21_dong - dong_21)}')
if plan_21_dong - dong_21:
    print(f'    {sorted(plan_21_dong - dong_21)}')
print(f'  Giao nhưng không có KH: {len(dong_21 - plan_21_dong)}')
if dong_21 - plan_21_dong:
    print(f'    {sorted(dong_21 - plan_21_dong)}')
