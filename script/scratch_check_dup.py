"""Quick script to check duplicate points on 22/04 for ĐÔNG MÁT."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter

# Load cache for month 4
cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)

rows = cache['rows']
print(f'Total cached rows: {len(rows)}')
pf = cache.get("processed_files", [])
print(f'Processed files ({len(pf)}): {pf}')

# Filter for 2026-04-22 and kho ĐÔNG MÁT
target_date = '2026-04-22'
dm_rows = [r for r in rows if r.get('date') == target_date and r.get('kho') == 'ĐÔNG MÁT']
print(f'\n=== ĐÔNG MÁT on 22/04 ===')
print(f'Total rows: {len(dm_rows)}')

dong_rows = [r for r in dm_rows if r.get('sub_kho') == 'ĐÔNG']
mat_rows = [r for r in dm_rows if r.get('sub_kho') == 'MÁT']
print(f'  ĐÔNG: {len(dong_rows)}')
print(f'  MÁT: {len(mat_rows)}')

# Check for dest duplicates
print(f'\n--- Dest duplicates (ĐÔNG MÁT combined) ---')
dest_counter = Counter(r['dest'] for r in dm_rows)
dups = {k:v for k,v in dest_counter.items() if v > 1}
print(f'Destinations appearing >1 time: {len(dups)}')
for d, cnt in sorted(dups.items(), key=lambda x: -x[1])[:30]:
    print(f'  {d}: {cnt} times')

# ĐÔNG sub_kho
print(f'\n--- Dest duplicates (ĐÔNG only) ---')
dong_dest_counter = Counter(r['dest'] for r in dong_rows)
dong_dups = {k:v for k,v in dong_dest_counter.items() if v > 1}
print(f'ĐÔNG destinations appearing >1 time: {len(dong_dups)}')
for d, cnt in sorted(dong_dups.items(), key=lambda x: -x[1])[:30]:
    print(f'  {d}: {cnt} times')

# Unique trips for ĐÔNG
print(f'\n--- ĐÔNG trips on 22/04 ---')
dong_trips = Counter(r['trip_id'] for r in dong_rows)
print(f'Unique trip IDs: {len(dong_trips)}')
for tid, cnt in sorted(dong_trips.items(), key=lambda x: -x[1]):
    print(f'  {tid}: {cnt} dests')

# Compare with nearby dates
print(f'\n=== Compare across dates (ĐÔNG MÁT) ===')
from datetime import date, timedelta
for offset in range(-3, 4):
    d = date(2026, 4, 22) + timedelta(days=offset)
    d_str = d.isoformat()
    d_rows = [r for r in rows if r.get('date') == d_str and r.get('kho') == 'ĐÔNG MÁT']
    d_dong = [r for r in d_rows if r.get('sub_kho') == 'ĐÔNG']
    d_mat = [r for r in d_rows if r.get('sub_kho') == 'MÁT']
    day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
    print(f'  {d.strftime("%d/%m")} ({day_name}): ĐÔNG MÁT={len(d_rows)}, ĐÔNG={len(d_dong)}, MÁT={len(d_mat)}')

# Now check: same dest + same trip_id in ĐÔNG
print(f'\n--- Detail: all ĐÔNG dests on 22/04 ---')
for r in sorted(dong_rows, key=lambda x: (x['trip_id'], x['dest'])):
    print(f"  trip={r['trip_id']}, dest={r['dest']}, container={r.get('container_type','')}, arrival={r.get('arrival_raw','')}")
