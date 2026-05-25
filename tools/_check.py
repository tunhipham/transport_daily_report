# -*- coding: utf-8 -*-
"""Fix store A183 data + redeploy + send Telegram."""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "script"))

# Step 1: Fix store data
JSON_PATH = os.path.join(REPO_ROOT, "data", "nso", "nso_stores.json")
with open(JSON_PATH, "r", encoding="utf-8") as f:
    stores = json.load(f)

fixed = 0
for s in stores:
    nm = s.get("name_mail") or s.get("name_full") or ""
    if "339" in nm and "Phước Long" in nm and s.get("code") is None:
        print(f"  BEFORE: {json.dumps(s, ensure_ascii=False)}")
        s["code"] = "A183"
        s["name_system"] = "KFM_HCM_TDU"
        s["name_full"] = "86C Đường 339 Phước Long"
        s["version"] = 2000
        print(f"  AFTER:  {json.dumps(s, ensure_ascii=False)}")
        fixed += 1

print(f"  Fixed {fixed} store(s)")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(stores, f, ensure_ascii=False, indent=2)

# Step 2: Regenerate Excel
from domains.nso.nso_master import NsoMaster
master = NsoMaster()
master.load()
# Apply fix to master stores too
for s in master.stores:
    nm = s.get("name_mail") or s.get("name_full") or ""
    if "339" in nm and "Phước Long" in nm and (s.get("code") is None or s.get("code") == "A183"):
        s["code"] = "A183"
        s["name_system"] = "KFM_HCM_TDU"
        s["name_full"] = "86C Đường 339 Phước Long"
        s["version"] = 2000
master.save()
master.save_output()

print(f"  Master saved: {len(master.stores)} stores")
