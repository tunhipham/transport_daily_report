"""Cross-check ĐÔNG actual vs KH hàng đông plan on 22/04."""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter
from datetime import date, timedelta

# Load monthly plan
plan_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\monthly_plan_T04.json'
with open(plan_path, 'r', encoding='utf-8') as f:
    plan_data = json.load(f)

# Check what kho keys exist in plan
print('Plan kho keys:', list(plan_data['plan'].keys()))

# Get ĐÔNG MÁT plan for 22/04
dm_plan = plan_data['plan'].get('ĐÔNG MÁT', [])
print(f'\nĐÔNG MÁT plan total entries: {len(dm_plan)}')

# Filter for 22/04
target = '22/04/2026'
target_alt = '2026-04-22'
plan_22 = [r for r in dm_plan if r.get('date', '') in (target, target_alt, '22/04')]

# Try different date formats
if not plan_22:
    # Check what date formats exist
    sample_dates = set(r.get('date', '')[:15] for r in dm_plan[:20])
    print(f'Sample plan dates: {sample_dates}')
    # Try matching just 22/04
    plan_22 = [r for r in dm_plan if '22/04' in str(r.get('date', ''))]

print(f'\nKH ĐÔNG MÁT ngày 22/04: {len(plan_22)} entries')

# Separate ĐÔNG vs MÁT by tuyến prefix (HĐ = hàng đông, KF = hàng mát)
dong_plan = [r for r in plan_22 if str(r.get('tuyen', '')).startswith('HĐ')]
mat_plan = [r for r in plan_22 if not str(r.get('tuyen', '')).startswith('HĐ') and r.get('tuyen', '')]
no_tuyen = [r for r in plan_22 if not r.get('tuyen', '')]

print(f'  HĐ (Hàng Đông): {len(dong_plan)} stores')
print(f'  KF (Hàng Mát): {len(mat_plan)} stores')
print(f'  No tuyến: {len(no_tuyen)} stores')

# Unique stores in plan
dong_plan_stores = set(r['store'] for r in dong_plan)
mat_plan_stores = set(r['store'] for r in mat_plan)
print(f'\n  HĐ unique stores: {len(dong_plan_stores)}')
print(f'  KF unique stores: {len(mat_plan_stores)}')

# Now load actual data
cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)
rows = cache['rows']

dong_actual = [r for r in rows if r.get('date') == '2026-04-22' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG']
dong_actual_stores = set(r['dest'] for r in dong_actual)

print(f'\n{"="*60}')
print(f'  CROSSCHECK: KH vs Thực tế ngày 22/04 (ĐÔNG)')
print(f'{"="*60}')
print(f'  KH hàng đông (plan):   {len(dong_plan_stores)} stores')
print(f'  Thực tế unique stores: {len(dong_actual_stores)} stores')
print(f'  Thực tế total rows:    {len(dong_actual)} (có trùng)')

# Stores in actual but NOT in plan
extra = dong_actual_stores - dong_plan_stores
missing = dong_plan_stores - dong_actual_stores
matched = dong_actual_stores & dong_plan_stores
print(f'\n  Khớp (cả plan & actual): {len(matched)}')
print(f'  Có trong actual nhưng KHÔNG có plan: {len(extra)}')
if extra:
    for s in sorted(extra):
        print(f'    {s}')
print(f'  Có trong plan nhưng KHÔNG giao: {len(missing)}')
if missing:
    for s in sorted(missing):
        print(f'    {s}')

# Compare with nearby days to see the "cách ngày" pattern
print(f'\n{"="*60}')
print(f'  KH ĐÔNG - so sánh các ngày (cách ngày pattern)')
print(f'{"="*60}')
for offset in range(-5, 6):
    d = date(2026, 4, 22) + timedelta(days=offset)
    d_str = d.strftime('%d/%m/%Y')
    d_plan = [r for r in dm_plan if d_str in str(r.get('date', '')) and str(r.get('tuyen', '')).startswith('HĐ')]
    d_stores = set(r['store'] for r in d_plan)
    
    d_actual = [r for r in rows if r.get('date') == d.isoformat() and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG']
    d_actual_unique = set(r['dest'] for r in d_actual)
    
    day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
    marker = ' <<<<' if offset == 0 else ''
    print(f'  {d.strftime("%d/%m")} ({day_name}): KH={len(d_stores):3d} stores, Actual={len(d_actual_unique):3d} unique / {len(d_actual):3d} rows{marker}')

# List the tuyến (routes) for ĐÔNG on 22/04
print(f'\n{"="*60}')
print(f'  TUYẾN HĐ ngày 22/04 (Plan)')
print(f'{"="*60}')
tuyen_counter = Counter(r.get('tuyen', '') for r in dong_plan)
for t, cnt in sorted(tuyen_counter.items()):
    print(f'  {t}: {cnt} stores')
