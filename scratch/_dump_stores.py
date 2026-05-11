import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open('data/nso_stores.json', 'r', encoding='utf-8'))
print(f"Old master: {len(d)} stores")
print(f"{'Code':>6} | {'Name Mail':<40} | {'Name Full':<40} | Date")
print("-" * 105)
for s in d:
    code = s.get("code") or "—"
    nm = (s.get("name_mail") or "")[:40]
    nf = (s.get("name_full") or "")[:40]
    od = s.get("opening_date", "")
    print(f"{code:>6} | {nm:<40} | {nf:<40} | {od}")
