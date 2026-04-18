# Weekly Transport Plan — Agent Prompts

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

# ❌ SAI — datetime subclass date, isinstance trả True cho cả 2
isinstance(datetime(2026,4,22), date)  # → True (không phân biệt được!)

# ✅ ĐÚNG — luôn check datetime TRƯỚC date
if isinstance(val, datetime):
    dt = val.date()
elif isinstance(val, date):
    dt = val
```

**Rule**: Mọi nơi fetch ngày từ Google Sheets / Excel → `.date()` ngay lập tức. Mọi nơi so sánh ngày → normalize cả 2 vế về `date`.

Áp dụng cho:
- `script/dashboard/export_weekly_plan.py` → `fetch_inventory_schedule()`, `cross_check_inventory()`
- `script/compose/compose_mail.py` → `fetch_inventory_schedule()`, `get_inventory_flagged_stores()`
- Bất kỳ script nào đọc ngày từ openpyxl/Google Sheets

## Cấu trúc project liên quan

```
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

## Quy tắc khi thay đổi

### Thêm NSO store mới
1. Thêm vào **STORES** trong `script/domains/nso/generate.py`
2. Thêm vào **NSO_SCHEDULE** trong `script/dashboard/export_weekly_plan.py`
3. User cung cấp: code, tên, opening_date, schedule_chia, schedule_ve, shift

### Update lịch tuần
1. User đặt file Excel mới vào `output/artifacts/weekly transport plan/`
2. Chạy `python script/dashboard/export_weekly_plan.py`
3. Verify output: số stores, châm hàng, kiểm kê
4. Deploy: `python script/dashboard/deploy.py --domain weekly_plan`

### NSO dời lịch khai trương
1. Update `opening_date` trong STORES
2. Thêm `original_date` = ngày cũ
3. Re-export → stores dời sẽ bị loại khỏi tuần cũ

## Key Logic trong export_weekly_plan.py

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
- Excel export button (xlsx-js-style, format giống sheet gốc)

### CDN Dependencies
- Chart.js (charts cho tab khác)
- xlsx-js-style@1.2.0 (Excel export với cell styling)
- chartjs-plugin-annotation

## Formatting Rules (áp dụng toàn project)
- Số hàng nghìn: dùng dấu "," (toLocaleString)
- KHÔNG viết tắt bất kỳ ký tự nào trong report
- Vietnamese diacritics: giữ nguyên, không bỏ dấu
- Ngày tháng: dd/mm/yyyy (display), date object (internal comparison)
