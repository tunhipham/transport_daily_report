import json, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

f = r'g:\My Drive\DOCS\transport_daily_report\docs\data\daily.json'
d = json.load(open(f, 'r', encoding='utf-8'))

print(f"File size: {os.path.getsize(f):,} bytes")
print(f"kho_list: {d['kho_list']}")
print(f"kho_colors: {d['kho_colors']}")
print(f"History entries: {len(d['history'])}")
print(f"Current khos: {list(d['current']['khos'].keys())}")
print(f"First hist khos: {list(d['history'][0]['khos'].keys())}")
print(f"Last hist khos: {list(d['history'][-1]['khos'].keys())}")
print()
# Check a few entries
for i, h in enumerate(d['history']):
    keys = sorted(h['khos'].keys())
    has_dm = 'ĐÔNG MÁT' in keys
    has_d = 'ĐÔNG' in keys
    has_m = 'MÁT' in keys
    if has_dm:
        print(f"  [{i}] {h['date']}: STILL has 'ĐÔNG MÁT'!")
    if not has_d or not has_m:
        print(f"  [{i}] {h['date']}: Missing ĐÔNG={has_d} MÁT={has_m}")
print("All entries validated.")
