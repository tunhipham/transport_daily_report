import json
from datetime import datetime, date

with open("data/nso/nso_stores.json", encoding="utf-8") as f:
    stores = json.load(f)

with open("data/nso/nso_schedule.json", encoding="utf-8") as f:
    sched = json.load(f)

with open("data/master_schedule.json", encoding="utf-8") as f:
    ms = json.load(f)
ms_codes = {s["code"] for s in ms["stores"]}

print("=== All NSO opening May-Jun 2026 ===")
for s in stores:
    od = s.get("opening_date", "")
    code = s.get("code", "?")
    if not od:
        continue
    try:
        d = datetime.strptime(od, "%d/%m/%Y").date()
        if date(2026, 5, 20) <= d <= date(2026, 6, 10):
            w = d.isocalendar()[1]
            in_sched = "sched:YES" if code in sched else "sched:NO"
            in_ms = "ms:YES" if code in ms_codes else "ms:NO"
            print(f"  {code:6s} | W{w} | {od} | {in_sched} | {in_ms} | {s['name_full']}")
    except:
        pass
