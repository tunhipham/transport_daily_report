# -*- coding: utf-8 -*-
"""Re-enrich NSO master with fresh DSST data (fill missing codes)."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "script"))

from domains.nso.nso_master import NsoMaster
from domains.nso.fetch_nso_mail import read_dsst, _normalize, _lcs_length, _is_name_match

# Load fresh DSST
dsst = read_dsst()

# Load master
master = NsoMaster()
master.load()
print(f"\nMaster: {len(master.stores)} stores")

# Re-enrich stores without code
enriched = []
for store in master.stores:
    if store.get("code"):
        # Already has code — just fill missing fields
        code = store["code"]
        dsst_info = dsst.get(code, {})
        if dsst_info.get("name_system") and not store.get("name_system"):
            store["name_system"] = dsst_info["name_system"]
        if dsst_info.get("version") and not store.get("version"):
            store["version"] = dsst_info["version"]
        continue

    # No code — fuzzy match
    mail_name = _normalize(store.get("name_mail") or store.get("name_full") or "")
    if not mail_name:
        continue

    best_match, best_lcs = None, 0
    for dsst_code, dsst_info in dsst.items():
        dsst_name = _normalize(dsst_info.get("name_full") or "")
        if not dsst_name:
            continue
        if not _is_name_match(mail_name, dsst_name):
            continue
        lcs = _lcs_length(mail_name, dsst_name)
        if lcs > best_lcs:
            best_lcs = lcs
            best_match = (dsst_code, dsst_info)

    if best_match:
        dsst_code, dsst_info = best_match
        store["code"] = dsst_code
        store["name_system"] = dsst_info.get("name_system")
        store["name_full"] = dsst_info.get("name_full")
        store["version"] = dsst_info.get("version")
        enriched.append(f"  ✅ {store.get('name_mail','?')[:40]} → {dsst_code} ({dsst_info.get('name_full','')})")
    else:
        print(f"  ❌ No match: {store.get('name_mail','?')[:50]}")

if enriched:
    print(f"\n  Enriched {len(enriched)} stores:")
    for e in enriched:
        print(e)

master.save()
print(f"\nDone! Master: {len(master.stores)} stores")
