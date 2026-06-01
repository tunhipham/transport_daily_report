import json, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('docs/data/nso.json', 'r', encoding='utf-8'))
j5 = [s for s in d['stores'] if s.get('iso_date') == '2026-06-05']
print(f"June 5 stores: {len(j5)}")
for s in j5:
    print(f"  {s['code']:>6} | {s['name'][:55]}")

j5e = [e for e in d['calendar_events'] if e.get('date') == '2026-06-05']
print(f"\nJune 5 calendar events: {len(j5e)}")
for e in j5e:
    print(f"  {e['code']:>6} | {e['label'][:55]}")

print(f"\nTotal: {d['stats']['total']} stores")
