import os, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Find the actual directory path (Unicode issues with PowerShell)
base = r'G:\My Drive\DOCS\DAILY'
for d in os.listdir(base):
    if 'GIAO' in d and 'HANG' in d:
        full = os.path.join(base, d)
        print(f'Found dir: {d}')
        print(f'Full path: {full}')
        for f in os.listdir(full):
            if f.endswith('.xlsx'):
                fpath = os.path.join(full, f)
                size = os.path.getsize(fpath)
                print(f'  {f} ({size:,} bytes)')
        break
