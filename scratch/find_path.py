import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check all path variants from fetch_monthly.py
paths = [
    r'G:\My Drive\DOCS\DAILY\BÁO CÁO GIAO HÀNG MIỀN ĐÔNG\2026.04 BÁO CÁO GIAO HÀNG KINGFOOD.xlsx',
    r'G:\My Drive\DOCS\DAILY\BÁO CÁO GIAO HÀNG MIỀN ĐÔNG\04.2026 BAO CAO GIAO HANG KINGFOOD.xlsx',
    r'G:\My Drive\DOCS\DAILY\BÁO CÁO GIAO HÀNG MIỀN ĐÔNG\2026.04 BAO CAO GIAO HANG KINGFOOD.xlsx',
    r'G:\My Drive\DOCS\DAILY\BÁO CÁO GIAO HÀNG MIỀN ĐÔNG\04.2026 BÁO CÁO GIAO HÀNG KINGFOOD.xlsx',
]

for p in paths:
    exists = os.path.exists(p)
    print(f'  {"✅" if exists else "❌"} {os.path.basename(p)} (exists={exists})')

# Try finding by listing the directory
parent = r'G:\My Drive\DOCS\DAILY\BÁO CÁO GIAO HÀNG MIỀN ĐÔNG'
parent_exists = os.path.exists(parent)
print(f'\nParent dir exists: {parent_exists}')
if parent_exists:
    for f in os.listdir(parent):
        print(f'  {f}')
else:
    # Try without diacritics
    parent2 = r'G:\My Drive\DOCS\DAILY\BAO CAO GIAO HANG MIEN DONG'
    parent2_exists = os.path.exists(parent2)
    print(f'Without diacritics exists: {parent2_exists}')
    
    # Try listing parent and find match
    daily = r'G:\My Drive\DOCS\DAILY'
    print(f'\nAll dirs in DAILY:')
    for d in os.listdir(daily):
        if 'GIAO' in d.upper() or 'BAO' in d.upper():
            full = os.path.join(daily, d)
            print(f'  {d} (is_dir={os.path.isdir(full)})')
            if os.path.isdir(full):
                for f in os.listdir(full):
                    if f.endswith('.xlsx'):
                        print(f'    {f} ({os.path.getsize(os.path.join(full,f)):,} bytes)')
