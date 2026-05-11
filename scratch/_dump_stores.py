import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open('data/nso/nso_stores.json', 'r', encoding='utf-8'))
print(f"Current master: {len(d)} stores")
print(f"{'#':>2} {'Code':>6} | {'Name Mail':<40} | {'Name Full':<40} | Date")
print("-" * 110)
for i, s in enumerate(d):
    code = s.get("code") or "—"
    nm = (s.get("name_mail") or "")[:40]
    nf = (s.get("name_full") or "")[:40]
    od = s.get("opening_date", "")
    marker = " NEW" if i >= 30 else ""
    print(f"{i+1:>2} {code:>6} | {nm:<40} | {nf:<40} | {od}{marker}")
