---
description: Generate or update the weekly transport plan (Lịch về hàng siêu thị)
---

# Weekly Transport Plan Workflow

> Tạo và cập nhật Lịch Tuần giao hàng siêu thị. Làm mỗi thứ 5, review thứ 6/7 cho W+1.
> Dashboard tab: 📅 Lịch Tuần

## Rules (QUAN TRỌNG)

1. **Weekly cadence**: Làm vào thứ 5 hàng tuần, review lại thứ 6/7 cho tuần W+1
2. **Lịch cố định**: Lịch chia 3-5-7 / 2-4-6, về ST 2-4-6 / 3-5-7, giao Ngày/Đêm → cố định theo sheet CHIA. Chỉ thay đổi khi user confirm
3. **NSO châm hàng**: Khai trương = 4 ngày liên tiếp châm hàng (D→D+3), sau đó về lịch daily
4. **NSO dời lịch**: Store có `original_date` → bỏ ra khỏi tuần cũ, chỉ tính tuần mới
5. **Kiểm kê cross-check**: Tự động fetch từ Google Sheets, đánh dấu D và D-1
6. **Excel export**: File xuất phải format y chang sheet "Lịch về hàng" gốc (có màu, filter, title)
7. **Không viết tắt**: Tất cả label trên dashboard và report phải viết đầy đủ

## Data Sources

| Source | Mô tả | Vị trí |
|--------|--------|--------|
| Excel lịch tuần | `Lịch đi hàng ST W{nn}.xlsx` | `output/artifacts/weekly transport plan/` |
| Sheet "Lịch về hàng" | Bảng chính: tên ST, code, chia/về, giờ, 7 ngày | Trong Excel file |
| Sheet "CHIA" | Lịch chia/về cố định (master) | Trong Excel file |
| Google Sheets kiểm kê | Lịch kiểm kê tổng 2026 | `INVENTORY_SHEET_URL` (script/lib/sources.py) |
| NSO STORES | Danh sách NSO + ngày khai trương | `script/domains/nso/generate.py` |
| NSO_SCHEDULE | Lịch chia/về/shift cho NSO | `script/dashboard/export_weekly_plan.py` |

## Workflow

### 1. Chuẩn bị file Excel tuần mới

User tạo file `Lịch đi hàng ST W{nn}.xlsx` trong:
```
output/artifacts/weekly transport plan/
```

### 2. Cập nhật NSO stores (nếu có khai trương mới)

Thêm store mới vào **2 nơi**:

**a. NSO STORES** (script/domains/nso/generate.py):
```python
STORES = [
    ...
    {"code": "A999", "name_system": "KFM_HCM_XXX", 
     "name_full": "Tên Siêu Thị", "opening_date": "DD/MM/YYYY"},
]
```

**b. NSO_SCHEDULE** (script/dashboard/export_weekly_plan.py):
```python
NSO_SCHEDULE = {
    ...
    "A999": {"schedule_chia": "Thứ 3-5-7", "schedule_ve": "Thứ 2-4-6", "shift": "Đêm",
             "name_full": "Tên Siêu Thị"},
}
```

> [!IMPORTANT]
> Shift mặc định = Đêm. User sẽ confirm nếu store nào giao Ngày.

### 3. Export data + Deploy

// turbo
```powershell
python script/dashboard/export_weekly_plan.py
```

Hoặc deploy luôn lên live:

```powershell
python script/dashboard/deploy.py --domain weekly_plan
```

### 4. Verify trên dashboard

- Mở https://tunhipham.github.io/transport_daily_report/
- Tab "📅 Lịch Tuần" → chọn tuần mới
- Check: NSO châm hàng đúng ngày, kiểm kê cross-check đúng, stores đủ
- Test nút "Xuất Excel" → file .xlsx format đúng

## NSO Châm Hàng Logic

```
D     = ngày khai trương (opening_date)
D+1   = ngày 2 châm hàng
D+2   = ngày 3 châm hàng  
D+3   = ngày 4 châm hàng (cuối cùng)
D+4+  = về lịch daily theo schedule_ve
```

**Ví dụ**: Store mở 23/04 (Thứ 4), chia 3-5-7, về 2-4-6:
- Thứ 4 → Châm hàng (D)
- Thứ 5 → Châm hàng (D+1)
- Thứ 6 → Châm hàng (D+2)
- Thứ 7 → Châm hàng (D+3)
- Chủ nhật → (không giao — 2-4-6 = T2/T4/T6)
- Thứ 2 tuần sau → Đêm (lịch daily 2-4-6)

**NSO dời lịch**: Nếu `original_date` khác `opening_date`:
- Bỏ châm hàng khỏi tuần gốc
- Chỉ áp dụng châm hàng cho tuần mới (theo `opening_date`)

## Excel Export Format

File xuất `.xlsx` có format:
- **Row 1**: Empty
- **Row 2**: "LỊCH VỀ HÀNG SIÊU THỊ" | count | week label (nền xanh đậm)
- **Row 3**: Date header (nền đỏ)
- **Row 4**: Column headers — SIÊU THỊ, Viết tắt, Giờ nhận, Thứ 2→CN (nền vàng)
- **Row 5+**: Data
- **Châm hàng**: chữ cam, nền cam nhạt
- **Kiểm kê**: chữ đỏ, nền hồng
- Auto-filter trên header row

> [!NOTE]
> **Không** xuất 4 cột: Lịch chia, Lịch về, Khai trương, Kiểm kê

## Files

| File | Vai trò |
|------|---------|
| `script/dashboard/export_weekly_plan.py` | Parse Excel → JSON, cross-check kiểm kê, NSO châm hàng |
| `docs/data/weekly_plan.json` | Data layer cho dashboard tab |
| `docs/index.html` | Dashboard UI — tab "📅 Lịch Tuần" |
| `script/dashboard/deploy.py` | Deploy (domain: `weekly_plan`) |
| `output/artifacts/weekly transport plan/` | Source Excel files |
| `script/domains/nso/generate.py` | NSO STORES (opening dates) |
| `script/lib/sources.py` | INVENTORY_SHEET_URL |

## Troubleshooting

### NSO store không hiện châm hàng
- Check code có trong NSO STORES (`script/domains/nso/generate.py`)
- Check code + name_full có trong NSO_SCHEDULE (`export_weekly_plan.py`)
- Verify name matching: name_full phải xuất hiện trong tên store ở Excel

### Kiểm kê không hiện
- Verify INVENTORY_SHEET_URL có accessible
- Check store code/name match giữa Excel và Google Sheet

### Excel export lỗi
- Clear cache browser (Ctrl+Shift+R)
- Check console (F12) xem `xlsx-js-style` CDN có load không
- Fallback: nếu XLSX undefined → alert thông báo

### Duplicate code (A179 issue)
- Export script match bằng code + name verification
- Nếu 2 store trùng code, script chọn store có name match với NSO name_full
- Stores không match → châm hàng bị strip (cleanup logic)
