import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('output/state/auto_compose_state.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print(f"Dates in compose state: {sorted(d.keys())}")
print()

# Check which dates have plan data (prev_rows_snapshot with gio_den)
for date_key in sorted(d.keys()):
    day = d[date_key]
    khos_with_plan = []
    for k, v in day.items():
        if isinstance(v, dict) and v.get('prev_rows_snapshot'):
            rows = v['prev_rows_snapshot']
            has_gio = any(r.get('gio_den') for r in rows if isinstance(r, dict))
            if has_gio:
                khos_with_plan.append(f"{k}({len(rows)})")
    if khos_with_plan:
        print(f"  {date_key}: {', '.join(khos_with_plan)}")
    else:
        print(f"  {date_key}: (no plan data)")
