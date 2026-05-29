import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('docs/data/performance.json', 'r', encoding='utf-8') as f:
    p = json.load(f)

m = p['months']['2026-05']
iso = m['iso_dates']
sla = m['charts']['sla']

# Find 25/05 and 29/05
for target in ['2026-05-25', '2026-05-28', '2026-05-29']:
    idx = iso.index(target) if target in iso else None
    if idx is None:
        print(f"{target}: NOT FOUND")
        continue
    print(f"\n=== {target} (idx={idx}) ===")
    print(f"SLA total: on={sla['on_times'][idx]}, late={sla['lates'][idx]}")
    kb = sla['kho_bars']
    for kho, data in kb.items():
        on = data['on'][idx]
        late = data['late'][idx]
        total = on + late
        pct = round(on/total*100, 1) if total > 0 else 0
        print(f"  {kho}: {total} trips ({pct}% SLA)")
