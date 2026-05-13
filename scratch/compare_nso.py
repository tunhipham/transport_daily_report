# -*- coding: utf-8 -*-
"""Compare current master with new mail data"""
import json, sys, re
from datetime import date, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Current master
stores = json.load(open('data/nso/nso_stores.json', 'r', encoding='utf-8'))

# New mail text (stores 176-205)
new_mail = """176. Đường M-KP Nhị Đồng -Dĩ An
    Ngày khai trương: 15/05/2026
177. Saigon Mia - L1-08
    Ngày khai trương: 15/05/2026
178. Golden Mansion - 119 Phổ Quang
    Ngày khai trương: 15/05/2026
179. Melody Residence-TPH
    Ngày khai trương: 16/05/2026
180. 52 Thoại Ngọc Hầu
    Ngày khai trương: 22/05/2026
181. Bàu Cát - TBI
    Ngày khai trương: 22/05/2026
182. Masterise Center Point - Vinhomes Grand Park
    Ngày khai trương: 23/05/2026
183. Homyland Riverside - TDU
    Ngày khai trương: 23/05/2026
184. Tân Thới Nhất 17 - Q12
    Ngày khai trương: 28/05/2026
185. Millennium - Q4
    Ngày khai trương: 28/05/2026
186. 299 Liên Phường - TDU
    Ngày khai trương: 29/05/2026
187. Đường A4 - TBI
    Ngày khai trương: 29/05/2026
188. 86C-88 Đường 339 - Phước Long B
    Ngày khai trương: 29/05/2026
189. Vinhomes Grand Park - S8.02
    Ngày khai trương: 05/06/2026
190. DS10 Bình Hưng
    Ngày khai trương: 05/06/2026
191. Sunrise Citiview - Q7
    Ngày khai trương: 19/06/2026
192. DS59 Gò Vấp
    Ngày khai trương: 19/06/2026
193. Lê Trọng Tấn - Dĩ An
    Ngày khai trương: 25/06/2026
194. KDC Thới An - Q12
    Ngày khai trương: 26/06/2026
195. Đường 20 - Sau lưng Giga Mall (Opal Garden)
    Ngày khai trương: 26/06/2026
196. Palm Resisdence - TDU
    Ngày khai trương: 27/06/2026
197. VHGP BS08 - TDU
    Ngày khai trương: 27/06/2026
198. 1132 Nguyễn Duy Trinh (67 NDT) - TDU
    Ngày khai trương: 27/06/2026
199. 173 Lê Văn Chí - Thủ Đức
    Ngày khai trương: 03/07/2026
200. DS1 An Hội Đông - GVA
    Ngày khai trương: 10/07/2026
201. VHGP S20.01 - TDU
    Ngày khai trương: 24/07/2026
202. Phú Hoàng Anh - NBE
    Ngày khai trương: 25/07/2026
203. 902 Nguyễn Duy Trinh - TDU
    Ngày khai trương: 28/08/2026
204. Empire City - Thủ Đức
    Ngày khai trương: 05/09/2026
205. 1652 Huỳnh Tấn Phát - Phú Xuân
    Ngày khai trương: 25/09/2026"""

def normalize(s):
    return re.sub(r'[\s\-–]+', ' ', s.lower().strip())

# Parse new stores
new_stores = []
for block in re.split(r'\n(?=\d{1,3}\.)', new_mail):
    block = block.strip()
    m = re.match(r'(\d+)\.\s+(.+)', block)
    if not m: continue
    stt = int(m.group(1))
    name = m.group(2).strip()
    dm = re.search(r'Ngày khai trương:\s*([\d/]+)', block)
    if not dm: continue
    new_stores.append({'stt': stt, 'name': name, 'date': dm.group(1)})

print(f"Master: {len(stores)} stores")
print(f"New mail: {len(new_stores)} stores (176-205)")

# Week analysis
today = date(2026, 5, 13)
print(f"\nToday: {today}")
for offset, label in [(0, "TUẦN NÀY (W20)"), (1, "TUẦN SAU (W21)")]:
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    print(f"\n{'='*60}")
    print(f"  {label}: {monday.strftime('%d/%m')} - {sunday.strftime('%d/%m')}")
    print(f"{'='*60}")
    
    # From current master
    print("  MASTER hiện tại:")
    for s in stores:
        od = s.get('opening_date', '')
        try:
            parts = od.split('/')
            d = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except: continue
        if monday <= d <= sunday:
            nm = s.get('name_mail') or s.get('name_full') or '?'
            print(f"    {nm[:50]:50s} | {od} | {s.get('code','--')}")
    
    # From new mail
    print("  MAIL MỚI:")
    for s in new_stores:
        try:
            parts = s['date'].split('/')
            d = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except: continue
        if monday <= d <= sunday:
            print(f"    #{s['stt']}: {s['name'][:50]:50s} | {s['date']}")

# Check stores in master but NOT in new mail (potential removals)
print(f"\n{'='*60}")
print("  STORES TRONG MASTER NHƯNG KHÔNG CÓ TRONG MAIL MỚI:")
print(f"{'='*60}")
new_names_norm = [normalize(s['name']) for s in new_stores]
for s in stores:
    nm = normalize(s.get('name_mail') or s.get('name_full') or '')
    od = s.get('opening_date', '')
    try:
        parts = od.split('/')
        d = date(int(parts[2]), int(parts[1]), int(parts[0]))
    except: continue
    if d < today: continue  # skip past stores
    found = any(n in nm or nm in n for n in new_names_norm)
    if not found:
        print(f"  ⚠ {(s.get('name_mail') or s.get('name_full'))[:50]:50s} | {od} | {s.get('code','--')}")

# Check date changes
print(f"\n{'='*60}")
print("  NGÀY THAY ĐỔI:")
print(f"{'='*60}")
for ns in new_stores:
    nn = normalize(ns['name'])
    for s in stores:
        nm = normalize(s.get('name_mail') or s.get('name_full') or '')
        if nn in nm or nm in nn:
            if s.get('opening_date') != ns['date']:
                print(f"  ~ {ns['name'][:45]:45s} | {s['opening_date']} → {ns['date']}")
            break

# New stores not in master
print(f"\n{'='*60}")
print("  STORES MỚI (CHƯA CÓ TRONG MASTER):")
print(f"{'='*60}")
master_names = [normalize(s.get('name_mail') or s.get('name_full') or '') for s in stores]
for ns in new_stores:
    nn = normalize(ns['name'])
    found = any(n in nn or nn in n for n in master_names)
    if not found:
        print(f"  + #{ns['stt']}: {ns['name'][:50]:50s} | {ns['date']}")
