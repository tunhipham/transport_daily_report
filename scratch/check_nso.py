import json
data = json.load(open('docs/data/nso.json', 'r', encoding='utf-8'))

# Check Vinhomes stores
print("=== Stores with Vinhom/Grand Park ===")
for s in data['stores']:
    if 'Vinhom' in s['name'] or 'Grand Park' in s['name'] or 'S8' in s.get('code',''):
        print(f"  {s['code']:>6} | {s['name'][:55]} | {s['opening_date']} | {s['status_type']}")

# Check calendar events
print("\n=== Calendar events with Vinhom/Grand Park ===")
for e in data['calendar_events']:
    if 'Vinhom' in e['label'] or 'Grand Park' in e['label'] or 'VH2' in e.get('code',''):
        print(f"  {e['code']:>6} | {e['label'][:55]} | {e['date']} | {e['type']}")

# Confirm VH2 gone
print("\n=== VH2 check ===")
vh2_stores = [s for s in data['stores'] if s.get('code') == 'VH2']
vh2_events = [e for e in data['calendar_events'] if e.get('code') == 'VH2']
print(f"  VH2 in stores: {len(vh2_stores)}")
print(f"  VH2 in calendar: {len(vh2_events)}")
print(f"  Total stores: {data['stats']['total']}")
