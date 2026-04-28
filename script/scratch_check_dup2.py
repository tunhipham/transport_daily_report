"""Summary check: duplicates on 22/04 for ĐÔNG MÁT."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter
from datetime import date, timedelta

# Load cache for month 4
cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)

rows = cache['rows']
print(f'Total cached rows T04: {len(rows)}')
pf = cache.get("processed_files", [])
print(f'Processed files ({len(pf)}):')
for f in pf:
    print(f'  {f}')

# Also load T03 cache
cache_path3 = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T03.json'
try:
    with open(cache_path3, 'r', encoding='utf-8') as f:
        cache3 = json.load(f)
    rows3 = cache3['rows']
    print(f'\nTotal cached rows T03: {len(rows3)}')
except:
    rows3 = []

all_rows = rows3 + rows

target_date = '2026-04-22'
dm_rows = [r for r in all_rows if r.get('date') == target_date and r.get('kho') == 'ĐÔNG MÁT']

dong_rows = [r for r in dm_rows if r.get('sub_kho') == 'ĐÔNG']
mat_rows = [r for r in dm_rows if r.get('sub_kho') == 'MÁT']

print(f'\n{"="*60}')
print(f'  ĐÔNG MÁT ngày 22/04/2026')
print(f'{"="*60}')
print(f'  Tổng ĐÔNG MÁT: {len(dm_rows)} điểm')
print(f'  ĐÔNG:           {len(dong_rows)} điểm')
print(f'  MÁT:            {len(mat_rows)} điểm')

# Check dest appearing in BOTH ĐÔNG and MÁT
dong_dests = set(r['dest'] for r in dong_rows)
mat_dests = set(r['dest'] for r in mat_rows)
overlap = dong_dests & mat_dests
print(f'\n  Stores in BOTH ĐÔNG and MÁT: {len(overlap)}')
if overlap:
    for d in sorted(overlap):
        # Find the details
        dong_detail = [r for r in dong_rows if r['dest'] == d]
        mat_detail = [r for r in mat_rows if r['dest'] == d]
        print(f'    {d}:')
        for r in dong_detail:
            print(f'      ĐÔNG trip={r["trip_id"]}, container={r.get("container_type","")}, arrival={r.get("arrival_raw","")}')
        for r in mat_detail:
            print(f'      MÁT  trip={r["trip_id"]}, container={r.get("container_type","")}, arrival={r.get("arrival_raw","")}')

# Check within ĐÔNG for dest duplicates  
print(f'\n  Dest appearing >1 time in ĐÔNG:')
dong_dest_counter = Counter(r['dest'] for r in dong_rows)
dong_dups = {k:v for k,v in dong_dest_counter.items() if v > 1}
if dong_dups:
    for d, cnt in sorted(dong_dups.items(), key=lambda x: -x[1]):
        detail = [r for r in dong_rows if r['dest'] == d]
        print(f'    {d}: {cnt} times')
        for r in detail:
            print(f'      trip={r["trip_id"]}, container={r.get("container_type","")}, sub_kho={r.get("sub_kho","")}, arrival={r.get("arrival_raw","")}')
else:
    print(f'    (none)')

# Compare with other days
print(f'\n{"="*60}')
print(f'  So sánh các ngày lân cận')
print(f'{"="*60}')
for offset in range(-5, 6):
    d = date(2026, 4, 22) + timedelta(days=offset)
    d_str = d.isoformat()
    d_rows = [r for r in all_rows if r.get('date') == d_str and r.get('kho') == 'ĐÔNG MÁT']
    d_dong = [r for r in d_rows if r.get('sub_kho') == 'ĐÔNG']
    d_mat = [r for r in d_rows if r.get('sub_kho') == 'MÁT']
    day_name = ['T2','T3','T4','T5','T6','T7','CN'][d.weekday()]
    marker = ' <<<<' if offset == 0 else ''
    print(f'  {d.strftime("%d/%m")} ({day_name}): ĐÔNG MÁT={len(d_rows):3d}  |  ĐÔNG={len(d_dong):3d}, MÁT={len(d_mat):3d}{marker}')

# Unique trips count
print(f'\n{"="*60}')
print(f'  TRIPS on 22/04')
print(f'{"="*60}')
dong_trips = Counter(r['trip_id'] for r in dong_rows)
mat_trips = Counter(r['trip_id'] for r in mat_rows)
print(f'  ĐÔNG unique trips: {len(dong_trips)}')
print(f'  MÁT unique trips: {len(mat_trips)}')

# Same trip appearing in both ĐÔNG and MÁT?
shared_trips = set(dong_trips.keys()) & set(mat_trips.keys())
print(f'  Trips in BOTH ĐÔNG and MÁT: {len(shared_trips)}')
if shared_trips:
    for tid in sorted(shared_trips):
        print(f'    {tid}: ĐÔNG={dong_trips[tid]} dests, MÁT={mat_trips[tid]} dests')

# Check dedup key: (trip_id, dest, sub_kho) - are there actual dupes?
print(f'\n{"="*60}')
print(f'  DEDUP KEY CHECK (trip_id, dest, sub_kho)')
print(f'{"="*60}')
key_counter = Counter((r['trip_id'], r['dest'], r.get('sub_kho','')) for r in dm_rows)
key_dups = {k:v for k,v in key_counter.items() if v > 1}
print(f'  Duplicate keys: {len(key_dups)}')
for k,v in key_dups.items():
    print(f'    {k}: {v} times')
