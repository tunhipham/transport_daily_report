"""Check which xlsx files contributed to the duplicates on 22/04."""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter, defaultdict

# List all xlsx files for T04
data_dir = r'G:\My Drive\DOCS\DAILY\DS chi tiet chuyen xe\T04.26'
files = sorted([f for f in os.listdir(data_dir) if f.endswith('.xlsx') and not f.startswith('~')])
print(f'Files in T04.26: {len(files)}')
for f in files:
    print(f'  {f}')

# The dedup key is (trip_id, dest, sub_kho)
# Same store in different trips = NOT a duplicate in current logic
# But for counting "Tổng Điểm Giao", that means same store counted twice

# Let's check: does a single xlsx file already contain both trips for the same store?
# Or does the duplication come from merging multiple files?

sys.path.insert(0, os.path.dirname(os.path.dirname(data_dir)))
sys.path.insert(0, r'G:\My Drive\DOCS\transport_daily_report')
from script.domains.performance.generate import _load_single_file

# Check each file for 22/04 ĐÔNG rows
for fname in files:
    fpath = os.path.join(data_dir, fname)
    try:
        seen, total_raw = _load_single_file(fpath)
    except Exception as e:
        print(f'\n⚠ Error reading {fname}: {e}')
        continue
    
    # Filter for 22/04, ĐÔNG MÁT, sub_kho ĐÔNG
    dong_rows = [r for k, r in seen.items() if r.get('date') and str(r['date']) == '2026-04-22' 
                 and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG']
    if not dong_rows:
        continue
    
    unique_dests = set(r['dest'] for r in dong_rows)
    dest_counter = Counter(r['dest'] for r in dong_rows)
    dups_in_file = {k:v for k,v in dest_counter.items() if v > 1}
    
    print(f'\n📄 {fname}:')
    print(f'  ĐÔNG rows for 22/04: {len(dong_rows)}, unique dests: {len(unique_dests)}')
    if dups_in_file:
        print(f'  ⚠ DUPLICATES WITHIN FILE: {len(dups_in_file)} stores')
        for d, cnt in sorted(dups_in_file.items()):
            details = [r for r in dong_rows if r['dest'] == d]
            trips = [r['trip_id'] for r in details]
            print(f'    {d}: {cnt}x, trips={trips}')
    else:
        print(f'  ✅ No duplicates within this file')

# Now check: are duplicates caused by MERGING files?
# Accumulate across files
print(f'\n{"="*60}')
print(f'  CROSS-FILE MERGE ANALYSIS')
print(f'{"="*60}')
all_keys_per_file = defaultdict(set)  # key -> set of files
for fname in files:
    fpath = os.path.join(data_dir, fname)
    try:
        seen, _ = _load_single_file(fpath)
    except:
        continue
    for k, r in seen.items():
        if r.get('date') and str(r['date']) == '2026-04-22' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG':
            all_keys_per_file[k].add(fname)

# Keys appearing in multiple files
multi_file_keys = {k:v for k,v in all_keys_per_file.items() if len(v) > 1}
print(f'Keys (trip_id,dest,sub_kho) appearing in multiple files: {len(multi_file_keys)}')
if multi_file_keys:
    for k, fset in list(multi_file_keys.items())[:5]:
        print(f'  {k}: {fset}')
