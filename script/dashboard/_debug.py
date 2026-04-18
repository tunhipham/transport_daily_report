import json, sys
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('docs/data/weekly_plan.json', 'r', encoding='utf-8'))

# Check W16 duplicates
w16 = d['weeks']['W16']
seen = {}
for s in w16['stores']:
    if s['code'] in seen:
        print(f"W16 DUPLICATE: {s['code']}")
        print(f"  1st: {seen[s['code']]['name']}")
        print(f"  2nd: {s['name']}")
    seen[s['code']] = s

# Also check: is A176 (Sunrise Riverside) in W16?
a176 = [s for s in w16['stores'] if s['code'] == 'A176' or 'Sunrise Riverside' in s.get('name','')]
print(f"\nA176/Sunrise in W16: {len(a176)}")
for s in a176:
    print(f"  code={s['code']} name={s['name']}")
