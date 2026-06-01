import json, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('docs/data/nso.json', 'r', encoding='utf-8'))

print(f"Total: {d['stats']['total']} stores\n")

# Check stores opening this week (01-07 June)
print("=== Stores opening 01-07 June ===")
for s in d['stores']:
    iso = s.get('iso_date', '')
    if iso >= '2026-06-01' and iso <= '2026-06-07':
        print(f"  {s['code']:>6} | {s['name'][:55]} | {iso}")

# Check all stores with/without codes
no_code = [s for s in d['stores'] if not s['code'] or s['code'] == 'None']
has_code = [s for s in d['stores'] if s['code'] and s['code'] != 'None']
print(f"\nWith code: {len(has_code)}")
print(f"Without code: {len(no_code)}")
if no_code:
    print("\nStores WITHOUT code:")
    for s in no_code[:15]:
        print(f"  {s['name'][:60]} | {s.get('opening_date','')}")

# Calendar events for June 5
print("\n=== Calendar June 5 ===")
for e in d['calendar_events']:
    if e.get('date') == '2026-06-05':
        print(f"  {(e['code'] or '—'):>6} | {e['label'][:55]}")
