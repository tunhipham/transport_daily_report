# -*- coding: utf-8 -*-
"""Fix NDT stores: update 1132 NDT date + add 902 NDT as new store"""
import json, sys, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "script"))

from domains.nso.nso_master import NsoMaster
master = NsoMaster()
master.load()
print(f"Master: {len(master.stores)} stores")

# 1. Fix 1132 NDT date: 28/08 → 27/06
for s in master.stores:
    if s.get("code") == "NDT":
        old_date = s["opening_date"]
        s["original_date"] = old_date
        s["opening_date"] = "27/06/2026"
        # Also fix name_mail to match actual store
        s["name_mail"] = "1132 Nguyễn Duy Trinh (67 NDT) - TDU"
        master.history.append({
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "code": "NDT", "name": "1132 Nguyễn Duy Trinh",
            "action": "Dời lịch", "old_value": old_date,
            "new_value": "27/06/2026", "source": "Manual",
        })
        print(f"  ✅ NDT: {old_date} → 27/06/2026")
        break

# 2. Add 902 Nguyễn Duy Trinh as new store
new_store = {
    "code": None, "name_system": None,
    "name_full": "902 Nguyễn Duy Trinh - TDU",
    "name_mail": "902 Nguyễn Duy Trinh - TDU",
    "opening_date": "28/08/2026",
    "version": None, "original_date": None,
}
master.stores.append(new_store)
master.history.append({
    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
    "code": "", "name": "902 Nguyễn Duy Trinh - TDU",
    "action": "Thêm mới", "old_value": "",
    "new_value": "28/08/2026", "source": "Manual",
})
print(f"  ✅ Added: 902 Nguyễn Duy Trinh - TDU | 28/08/2026")

master.save()
print(f"\nMaster after fix: {len(master.stores)} stores")
