"""Focus: ĐÔNG sub_kho duplicate destinations on 22/04."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter

cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)
rows = cache['rows']

target_date = '2026-04-22'
dm_rows = [r for r in rows if r.get('date') == target_date and r.get('kho') == 'ĐÔNG MÁT']
dong_rows = [r for r in dm_rows if r.get('sub_kho') == 'ĐÔNG']

# Count unique destinations
dong_unique_dests = set(r['dest'] for r in dong_rows)
print(f'ĐÔNG on 22/04: {len(dong_rows)} total rows, {len(dong_unique_dests)} unique destinations')

# How many stores appear exactly once vs more
dong_dest_counter = Counter(r['dest'] for r in dong_rows)
single = sum(1 for v in dong_dest_counter.values() if v == 1)
double = sum(1 for v in dong_dest_counter.values() if v == 2)
triple = sum(1 for v in dong_dest_counter.values() if v >= 3)
print(f'  Appear 1 time: {single} stores')
print(f'  Appear 2 times: {double} stores')
print(f'  Appear 3+ times: {triple} stores')
print(f'  Total rows = {single*1 + double*2 + triple*3}')
print(f'  If no dupes, should be: {len(dong_unique_dests)} stores')
print(f'  Excess rows from duplicates: {len(dong_rows) - len(dong_unique_dests)}')

# For comparison, check another day like 21/04
d21_rows = [r for r in rows if r.get('date') == '2026-04-21' and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG']
d21_unique = set(r['dest'] for r in d21_rows)
d21_counter = Counter(r['dest'] for r in d21_rows)
d21_dups = sum(1 for v in d21_counter.values() if v > 1)
print(f'\nĐÔNG on 21/04: {len(d21_rows)} total rows, {len(d21_unique)} unique destinations, {d21_dups} stores duplicated')

# The dedup key is (trip_id, dest, sub_kho)
# So a store can appear twice if it's in different trips
# This is the root cause: the same store gets delivered by 2 different trips
# Let's show the pattern

print(f'\n=== ROOT CAUSE ===')
print(f'The dedup key is (trip_id, dest, sub_kho)')
print(f'So same store delivered by 2 DIFFERENT trips counts as 2 separate delivery points')
print(f'On 22/04, {double} stores were delivered by 2 different trips (ĐÔNG)')
print(f'This added {double} extra points, total = {len(dong_unique_dests)} unique + {double} extra = {len(dong_rows)}')

# What are these extra trips? They seem like batch 2 / afternoon deliveries
# Group by time: first delivery vs second delivery
print(f'\n=== DOUBLE-DELIVERED STORES (ĐÔNG) ===')
for dest, cnt in sorted(dong_dest_counter.items()):
    if cnt <= 1:
        continue
    details = [r for r in dong_rows if r['dest'] == dest]
    details.sort(key=lambda r: r.get('arrival_raw', ''))
    trips = [r['trip_id'] for r in details]
    times = [r.get('arrival_raw', '') for r in details]
    print(f'  {dest}: trip1={trips[0]} ({times[0]}), trip2={trips[1]} ({times[1]})')

# Check if the second trip batch follows a pattern (higher trip IDs)
print(f'\n=== TRIP ID PATTERN ===')
batch1_trips = set()
batch2_trips = set()
for dest, cnt in dong_dest_counter.items():
    if cnt != 2:
        continue
    details = sorted([r for r in dong_rows if r['dest'] == dest], key=lambda r: r.get('arrival_raw', ''))
    batch1_trips.add(details[0]['trip_id'])
    batch2_trips.add(details[1]['trip_id'])
print(f'Batch 1 trips (first delivery): {sorted(batch1_trips)}')
print(f'Batch 2 trips (second delivery): {sorted(batch2_trips)}')
only_batch2 = batch2_trips - batch1_trips
print(f'Trips ONLY in batch 2: {sorted(only_batch2)}')
