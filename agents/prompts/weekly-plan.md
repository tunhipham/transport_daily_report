# Weekly Transport Plan — Agent Context

## Bối cảnh

Dashboard logistics KFM có 5 tabs. Tab "📅 Lịch Tuần" hiển thị lịch giao hàng siêu thị theo tuần.
Mỗi tuần tạo 1 file Excel `Lịch đi hàng ST W{nn}.xlsx`, export thành JSON, deploy lên GitHub Pages.

## 🔴 BẮT BUỘC: Fetch lại lịch kiểm kê mới nhất

**Trước khi chạy BẤT KỲ task nào liên quan**, PHẢI fetch lại data kiểm kê từ nguồn Google Sheets:
- **Compose mail** (`compose_mail.py`) → script tự fetch mỗi lần chạy ✅
- **Lịch tuần** (`export_weekly_plan.py`) → script tự fetch mỗi lần chạy ✅

Lịch kiểm kê thay đổi liên tục (người input update bất kỳ lúc nào). Data cũ = sai.
Source: `INVENTORY_SHEET_URL` trong `script/lib/sources.py`

## ⚠️ CRITICAL: Date Normalization

**Ngày do người input** nên format không chuẩn. LUÔN normalize tất cả date về `date` object (KHÔNG phải `datetime`) trước khi so sánh.

```python
# ❌ SAI — datetime != date dù cùng ngày
datetime(2026, 4, 22) == date(2026, 4, 22)  # → False!

# ❌ SAI — datetime is subclass of date
isinstance(datetime(2026,4,22), date)  # → True (không phân biệt được!)

# ✅ ĐÚNG — check datetime TRƯỚC date
if isinstance(val, datetime):
    dt = val.date()
elif isinstance(val, date):
    dt = val
```

Áp dụng cho: `export_weekly_plan.py`, `compose_mail.py`, mọi script đọc ngày từ openpyxl/Google Sheets.

## Data Source Rules

| Data | Nguồn | Tính chất |
|------|-------|-----------|
| Lịch chia/về/shift | `data/master_schedule.json` + `.xlsx` | 🔒 **CỐ ĐỊNH** — chỉ thay đổi khi NSO mới hoặc đổi tuyến |
| Lịch kiểm kê | Google Sheets (INVENTORY_SHEET_URL) | 🔄 **DYNAMIC** — fetch mỗi lần chạy |
| Lịch về hàng (days) | Excel file W{nn} | 🔄 **DYNAMIC** — có thể thay đổi mỗi tuần |
| NSO opening dates | `script/domains/nso/generate.py` | ➕ Thêm khi có store mới |

## Cấu trúc project liên quan

```
data/
  master_schedule.json     # 🔒 CỐ ĐỊNH — lịch chia/về/shift (từ sheet CHIA)
  master_schedule.xlsx     # 🔒 Backup Excel (review/edit bằng tay)
script/
  dashboard/
    export_weekly_plan.py    # Parse Excel → JSON (main logic)
    export_data.py           # Export daily/performance/inventory/nso
    deploy.py                # Git push (supports --domain weekly_plan)
  compose/
    compose_mail.py          # Email composition (cũng fetch kiểm kê)
  domains/
    nso/generate.py          # NSO STORES list (opening dates)
  lib/sources.py             # INVENTORY_SHEET_URL
output/
  artifacts/
    weekly transport plan/   # Source Excel files (W14, W15, W16, W17...)
docs/
  data/weekly_plan.json      # Output JSON cho dashboard
  index.html                 # Dashboard SPA
```

## Key Logic trong export_weekly_plan.py

### Kiểm kê Cross-Check (2 steps)
1. **Xóa** kiểm kê sai từ Excel gốc (ngày không phải D hoặc D-1)
2. **Đánh dấu** D và D-1 đúng từ Google Sheets

### Code Corrections
- `CODE_CORRECTIONS` dict sửa code sai từ Excel gốc (vd: A179 Sunrise Riverside → A176)
- Extend dict khi phát hiện thêm trường hợp sai

### Code + Name Matching
- NSO store match bằng code VÀ name verification
- Tránh false positive khi 2 stores trùng code (vd: A179)
- `_name_matches()` check ít nhất 50% từ có nghĩa khớp

### Cleanup false châm hàng  
- Sau khi apply NSO, script strip "Châm hàng" từ stores KHÔNG phải NSO hợp lệ
- Xử lý case Excel gốc có châm hàng nhầm (user quên bỏ)

### Inject missing stores
- NSO stores có opening trong tuần nhưng KHÔNG có trong Excel → inject row mới
- Tự tính post-châm delivery days theo schedule_ve + shift

## Dashboard UI (index.html)

### Tab "📅 Lịch Tuần"
- Week selector dropdown
- Stats cards: Tổng ST, Lượt Giao Ngày, Lượt Giao Đêm, Châm Hàng, Kiểm Kê
- Inline store search filter
- Color-coded schedule table (frozen header, max-height 75vh scroll)
- Legend: Ngày (vàng), Đêm (tím), Kiểm kê (tím nhạt), Châm hàng (cam)
- Excel export button (xlsx-js-style@1.2.0, format giống sheet gốc, dùng `XLSX.writeFile()`)
- JSON fetch có cache-bust `?t=timestamp`

### CDN Dependencies
- Chart.js (charts cho tab khác)
- xlsx-js-style@1.2.0 (Excel export với cell styling)
- chartjs-plugin-annotation

## Formatting Rules (áp dụng toàn project)
- Số hàng nghìn: dùng dấu "," (toLocaleString)
- KHÔNG viết tắt bất kỳ ký tự nào trong report
- Vietnamese diacritics: giữ nguyên, không bỏ dấu
- Ngày tháng: dd/mm/yyyy (display), date object (internal comparison)
