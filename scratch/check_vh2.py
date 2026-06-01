import json
stores = json.load(open('data/nso/nso_stores.json', 'r', encoding='utf-8'))
for i, s in enumerate(stores):
    code = s.get('code') or ''
    nm = s.get('name_mail') or ''
    nf = s.get('name_full') or ''
    od = s.get('opening_date') or 'null'
    if 'VH2' == code or 'Vinhom' in nm or 'Grand Park' in nm or 'S10.02' in nf or 'S8.02' in nf:
        print(f"  [{i}] code={code:>5} | name_mail={nm[:55]} | name_full={nf[:40]} | date={od}")
