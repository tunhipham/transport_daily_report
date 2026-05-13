# -*- coding: utf-8 -*-
import requests, io, sys, openpyxl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Try with gid first, then without
for label, url in [
    ("with gid", "https://docs.google.com/spreadsheets/d/1byEE8KterdcRr10IydIjbPcJcQwhX2HtGBzd0VZ5N1k/export?format=xlsx&gid=1655867479"),
    ("no gid", "https://docs.google.com/spreadsheets/d/1byEE8KterdcRr10IydIjbPcJcQwhX2HtGBzd0VZ5N1k/export?format=xlsx"),
]:
    print(f"\n=== {label} ===")
    r = requests.get(url, timeout=30)
    print(f"Status: {r.status_code}, Size: {len(r.content)}")
    if r.status_code != 200:
        continue
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    print(f"Sheets: {wb.sheetnames}")
    for ws_name in wb.sheetnames:
        ws = wb[ws_name]
        print(f"\n  Sheet '{ws_name}':")
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=3), 1):
            vals = []
            for c in row[:10]:
                v = str(c.value)[:35] if c.value else ""
                vals.append(v)
            print(f"    Row {i}: {vals}")
    wb.close()
