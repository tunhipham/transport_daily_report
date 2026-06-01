import json
d = json.load(open('data/nso/nso_stores.json', 'r', encoding='utf-8'))
print(f"nso_stores.json: {len(d)} entries")

# S8.02 duplicates
vhgp = [s for s in d if 'S8.02' in (s.get('name_full','') + s.get('name_mail',''))]
print(f"\nS8.02 entries: {len(vhgp)}")
for s in vhgp:
    print(f"  {s.get('name_mail','')[:55]} | date={s.get('opening_date')}")

# A202 duplicates  
a202 = [s for s in d if 'A202' in ((s.get('code') or '') + (s.get('name_mail') or ''))]
print(f"\nA202 entries: {len(a202)}")
for s in a202:
    print(f"  code={s.get('code',''):>5} | {s.get('name_mail','')[:55]} | date={s.get('opening_date')}")

# nso.json output
nso = json.load(open('docs/data/nso.json', 'r', encoding='utf-8'))
print(f"\nnso.json: {nso['stats']['total']} stores")
june5 = [s for s in nso['stores'] if s.get('iso_date') == '2026-06-05']
print(f"June 5 stores: {len(june5)}")
for s in june5:
    print(f"  {s['code']:>6} | {s['name'][:55]} | {s['status_type']}")
