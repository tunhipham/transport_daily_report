# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
cap = json.load(open(r'g:\My Drive\DOCS\transport_daily_report\docs\data\capacity_forecast.json', encoding='utf-8'))

krc = [d for d in cap['krc']['data'] if '05/2026' in d['date']]
print(f'KRC May 2026: {len(krc)} dates')
for d in krc[-7:]:
    marker = ' ← TODAY' if d['date'] == '20/05/2026' else ''
    print(f'  {d["date"]}: {d["tons"]:>6.2f} T  ({d["pct_capacity"]}%){marker}')

ksl = [d for d in cap['ksl']['data'] if '05/2026' in d['date']]
print(f'\nKSL May 2026: {len(ksl)} dates')
for d in ksl[-7:]:
    marker = ' ← TODAY' if d['date'] == '20/05/2026' else ''
    print(f'  {d["date"]}: {d["items"]:>8,} items  ({d["pct_capacity"]}%){marker}')

print(f'\nUpdated: {cap["_updated"]}')
print(f'Total KRC dates: {len(cap["krc"]["data"])} (was ~19, now from DB)')
