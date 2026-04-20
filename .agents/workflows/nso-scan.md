# /nso-scan — NSO Mail Scanner

> Quét email NSO trên Haraworks, merge dữ liệu vào master, deploy dashboard.

## Khi nào chạy
- **Tự động**: Task Scheduler chạy Mon/Tue khi logon
- **Thủ công**: Khi có mail NSO mới cần cập nhật

## Prerequisites
- `data/dsst_cache.json` — DSST store metadata (refresh bằng `_save_dsst.py`)
- Edge browser profile đã login Haraworks

---

## Steps

### Step 1: Run scanner
```powershell
# Dry run (xem trước, không ghi)
python -u script/domains/nso/fetch_nso_mail.py --force --dry-run

# Full run (ghi master + deploy)
python -u script/domains/nso/fetch_nso_mail.py --force
```

### Step 2: Review output
- `output/nso/scan_summary.txt` — Tóm tắt kết quả scan
- `output/nso/nso_master.xlsx` — Copy master Excel (Stores + History)
- `output/nso/nso.json` — Dashboard JSON data

### Step 3: Check master
- `data/nso/nso_master.xlsx` — Sheet "Stores": danh sách 30+ stores
- `data/nso/nso_master.xlsx` — Sheet "History": log mọi thay đổi

### Step 4: Verify dashboard
- https://tunhipham.github.io/transport_daily_report/ → Tab NSO
- Ctrl+Shift+R để hard refresh

---

## Manual Operations

### Update store date manually
```python
# Trong Python hoặc qua script
from nso_master import NsoMaster
master = NsoMaster()
master.load()
master.update_store("A185", opening_date="25/04/2026", source="Manual")
master.save()
```

### Refresh DSST cache
Khi DSST Google Sheet có thay đổi (thêm store mới, đổi version):
1. Mở DSST sheet trên browser
2. Chạy:
```powershell
python -u script/domains/nso/_save_dsst.py
```

### Re-deploy dashboard only
```powershell
python -u script/dashboard/deploy.py --domain nso
```

---

## Data Flow

```
_save_dsst.py ──→ data/dsst_cache.json (181 stores)
                        ↓
fetch_nso_mail.py ──→ Haraworks mail → parse stores
                        ↓
                  NsoMaster.merge_mail()
                        ↓
              data/nso/nso_master.xlsx (Stores + History)
                        ↓
              output/nso/ (nso.json, nso_master.xlsx, scan_summary.txt)
                        ↓
              export_data.py → docs/data/nso.json
                        ↓
              deploy.py → GitHub Pages
```

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Parsed 0 stores | Email format mới? Check selector + date regex |
| DSST cache empty | Chạy `_save_dsst.py` với DSST sheet mở |
| NSO tab trống | Check JS console cho null code errors |
| Date sai format | Check `22\n/05` pattern → text normalization |
