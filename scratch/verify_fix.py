# -*- coding: utf-8 -*-
"""Verify fix #2: fingerprint stability test + end-to-end dry run."""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = r'g:\My Drive\DOCS\transport_daily_report'
sys.path.insert(0, os.path.join(BASE, 'script'))

from data_pipeline.sync_realtime import (
    check_transfer_fingerprint,
    check_schedule_fingerprint,
    get_today_iso,
)

today_iso = get_today_iso()
print(f'=== FINGERPRINT STABILITY TEST — {today_iso} ===')
print()

# Run 1
print('--- Run 1 ---')
t1 = time.time()
fp_t1 = check_transfer_fingerprint(today_iso)
fp_s1 = check_schedule_fingerprint(today_iso)
d1 = time.time() - t1
print(f'  Transfer: {fp_t1}')
print(f'  Schedule: {fp_s1}')
print(f'  Time: {d1:.1f}s')

# Run 2 (immediate)
print()
print('--- Run 2 (immediate) ---')
t2 = time.time()
fp_t2 = check_transfer_fingerprint(today_iso)
fp_s2 = check_schedule_fingerprint(today_iso)
d2 = time.time() - t2
print(f'  Transfer: {fp_t2}')
print(f'  Schedule: {fp_s2}')
print(f'  Time: {d2:.1f}s')

# Compare
print()
print('=== RESULT ===')
t_match = fp_t1 == fp_t2
s_match = fp_s1 == fp_s2
print(f'  Transfer stable? {t_match} {"✅" if t_match else "❌"}')
print(f'  Schedule stable? {s_match} {"✅" if s_match else "❌"}')

# Check schedule is actually returning data (not 0|None)
s_parts = fp_s1.split('|')
s_count = int(s_parts[0]) if s_parts[0].isdigit() else 0
print(f'  Schedule rows: {s_count} {"✅" if s_count > 0 else "❌ STILL BROKEN"}')

if t_match and s_match and s_count > 0:
    print()
    print('  ✅ ALL GOOD — fingerprints stable and returning real data')
    print('  → sync_realtime.py will correctly SKIP when data unchanged')
else:
    print()
    print('  ❌ ISSUES REMAIN')

# Full dry-run
print()
print()
print('=== FULL DRY RUN ===')
os.system(f'"{sys.executable}" script/data_pipeline/sync_realtime.py --dry-run')
