# -*- coding: utf-8 -*-
"""One-time script: export STORES from generate.py to data/nso_stores.json"""
import json, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "script"))

from domains.nso.generate import STORES

out_path = os.path.join(REPO, "data", "nso_stores.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(STORES, f, ensure_ascii=False, indent=2)

print(f"Exported {len(STORES)} stores to {out_path}")
for s in STORES[:3]:
    print(f"  {s['code']} - {s['name_mail']} - {s['opening_date']}")
print("  ...")
