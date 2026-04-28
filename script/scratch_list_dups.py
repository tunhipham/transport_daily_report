"""List all 62 stores delivered twice on 22/04 (ĐÔNG)."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter

cache_path = r'G:\My Drive\DOCS\transport_daily_report\output\state\trip_cache_T04.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)
rows = cache['rows']

target_date = '2026-04-22'
dong_rows = [r for r in rows if r.get('date') == target_date and r.get('kho') == 'ĐÔNG MÁT' and r.get('sub_kho') == 'ĐÔNG']

dest_counter = Counter(r['dest'] for r in dong_rows)
dups = {k:v for k,v in dest_counter.items() if v > 1}

print(f'| STT | Store | Chuyến 1 | Giờ đến 1 | Chuyến 2 | Giờ đến 2 |')
print(f'|-----|-------|----------|-----------|----------|-----------|')
i = 0
for dest in sorted(dups.keys()):
    details = sorted([r for r in dong_rows if r['dest'] == dest], key=lambda r: r.get('arrival_raw', ''))
    i += 1
    t1 = details[0]['trip_id']
    a1 = details[0].get('arrival_raw', '').replace('22/04/2026 ', '')
    t2 = details[1]['trip_id']
    a2 = details[1].get('arrival_raw', '').replace('22/04/2026 ', '').replace('23/04/2026 ', '23/04 ')
    print(f'| {i} | {dest} | {t1} | {a1} | {t2} | {a2} |')

print(f'\nTổng: {i} stores giao 2 chuyến')
