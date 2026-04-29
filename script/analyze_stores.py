# -*- coding: utf-8 -*-
import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

md = pd.read_excel(r'g:\My Drive\DOCS\transport_daily_report\data\shared\master_data.xlsx', nrows=20)
for _, r in md.iterrows():
    nw = r.get('Net weight')
    tv = r.get('Giá trị trọng lượng/ thể tích')
    tu = r.get('Đơn vị trọng lượng/ thể tích')
    name = str(r['Tên sản phẩm'])[:60]
    print(f"BC={r['Barcode']}: NW={nw}, TL={tv} {tu}, {name}")

# Check: NW value range
md_full = pd.read_excel(r'g:\My Drive\DOCS\transport_daily_report\data\shared\master_data.xlsx',
                        usecols=['Net weight', 'Giá trị trọng lượng/ thể tích', 'Đơn vị trọng lượng/ thể tích'])
print()
print('Net weight stats:')
print(md_full['Net weight'].describe())
print()
print('Sample high Net weight:')
print(md_full[md_full['Net weight'] > 10].head(10))
