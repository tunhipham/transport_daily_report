import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('docs/data/performance.json', 'r', encoding='utf-8') as f:
    p = json.load(f)

m = p['months']['2026-05']
idx = 24  # 25/05

charts = m['charts']
sla = charts['sla']

print(f"SLA keys: {list(sla.keys())}")
print(f"kho_bars type: {type(sla['kho_bars'])}")

# Show kho_bars structure  
kb = sla['kho_bars']
if isinstance(kb, dict):
    print("kho_bars is a dict:")
    for k, v in kb.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                if isinstance(sv, list):
                    print(f"  {k}.{sk}: [{sv[idx] if idx < len(sv) else 'N/A'}] (at idx {idx})")
        elif isinstance(v, list):
            print(f"  {k}: [{v[idx] if idx < len(v) else 'N/A'}] (at idx {idx})")
elif isinstance(kb, list):
    print(f"kho_bars is a list of {len(kb)} items")
    print(f"First item type: {type(kb[0])}")
    print(f"Content: {kb[:3]}")

print(f"\nSLA total at idx {idx}: on={sla['on_times'][idx]}, late={sla['lates'][idx]}")

# Check trends
print(f"\nSLA trends at idx {idx}:")
for t in sla['trends']:
    label = t['label']
    data = t['data']
    val = data[idx] if idx < len(data) else 'N/A'
    print(f"  {label}: {val}")

# Show what the dashboard tab shows
# The performance tab on dashboard uses kho_bars for the per-kho breakdown table
# It seems the dashboard is reading these values
print(f"\nkho_bars full:")
print(json.dumps(kb, ensure_ascii=False, indent=2)[:2000])
