# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
f = open(r'g:\My Drive\DOCS\transport_daily_report\docs\data\capacity_forecast.json', 'r', encoding='utf-8')
d = json.load(f)
krc = d['krc']['data']
print("May 2026 KRC tonnage on dashboard:")
for x in krc:
    if '05/2026' in x['date']:
        tons = x.get('value', x.get('tons', x.get('total', '?')))
        print(f"  {x['date']}: {tons}")
# Show first entry keys
if krc:
    print(f"\nKeys: {list(krc[0].keys())}")
    print(f"Sample: {krc[0]}")
