# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
stores = json.load(open('data/nso/nso_stores.json', 'r', encoding='utf-8'))
print(f"Total stores in master: {len(stores)}")
print("-" * 80)
for i, s in enumerate(stores):
    nm = (s.get('name_mail') or s.get('name_full') or '?')[:45]
    od = s.get('opening_date', '?')
    code = s.get('code') or '--'
    print(f"  {i+1:3d}. {nm:45s} | {od:12s} | {code}")
