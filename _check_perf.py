import json

with open('docs/data/performance.json', 'r', encoding='utf-8') as f:
    p = json.load(f)

m = p['months']['2026-05']
charts = m['charts']

print(f"Dates: {len(m['iso_dates'])}, last={m['iso_dates'][-1]}")
print()

for kho, data in charts.items():
    sla = data.get('sla', {})
    on_time = sla.get('on_time', [])
    late = sla.get('late', [])
    total = [a+b for a,b in zip(on_time, late)] if on_time and late else []
    last5_total = total[-5:] if total else []
    last5_ot = on_time[-5:] if on_time else []
    print(f"{kho}: last 5 SLA total={last5_total}, on_time={last5_ot}")

# Check tracking for today
tracking = p.get('tracking', {})
dates = tracking.get('dates', {})
today = '2026-05-29'
if today in dates:
    for kho, rows in dates[today].items():
        print(f"\nTracking {today} {kho}: {len(rows)} rows")
        if rows:
            print(f"  first: {rows[0]}")
else:
    print(f"\nNo tracking for {today}")
    print(f"Available tracking dates: {sorted(dates.keys())[-5:]}")
