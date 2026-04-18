---
description: Generate or update the weekly transport plan (Lịch về hàng siêu thị)
---

# Weekly Transport Plan Workflow

> Tạo và cập nhật Lịch Tuần giao hàng siêu thị. Làm mỗi thứ 5, review thứ 6/7 cho W+1.
> Dashboard tab: 📅 Lịch Tuần

## 🔴 BẮT BUỘC

1. **Fetch lại kiểm kê mới nhất** — Script tự fetch mỗi lần chạy. KHÔNG BAO GIỜ dùng data kiểm kê cũ.
2. **Normalize dates** — Mọi ngày từ Excel/Google Sheets → `.date()` ngay lập tức (KHÔNG dùng `datetime`).

## Rules

1. **Weekly cadence**: Làm vào thứ 5 hàng tuần, review lại thứ 6/7 cho tuần W+1
2. **Lịch cố định**: Lịch chia/về/shift cố định trong `data/master_schedule.json` (từ sheet CHIA). Chỉ thay đổi khi user confirm
3. **NSO châm hàng**: Khai trương = 4 ngày liên tiếp châm hàng (D→D+3), sau đó về lịch daily
4. **NSO dời lịch**: Store có `original_date` → bỏ ra khỏi tuần cũ, chỉ tính tuần mới
5. **Kiểm kê cross-check**: Tự động fetch từ Google Sheets, đánh dấu D và D-1. Nếu Excel gốc có ghi sai kiểm kê (nhầm ngày) → script tự xóa
6. **Excel export**: File xuất phải format y chang sheet "Lịch về hàng" gốc (có màu, filter, title)
7. **Không viết tắt**: Tất cả label trên dashboard và report phải viết đầy đủ

## Data Sources

| Source | Tính chất | Vị trí |
|--------|-----------|--------|
| Master schedule (CHIA) | 🔒 **CỐ ĐỊNH** — lịch chia/về/shift | `data/master_schedule.json` + `.xlsx` |
| Lịch kiểm kê | 🔄 **DYNAMIC** — fetch mỗi lần chạy | Google Sheets (`INVENTORY_SHEET_URL`) |
| Lịch về hàng (days) | 🔄 **DYNAMIC** — thay đổi mỗi tuần | `output/artifacts/weekly transport plan/` |
| NSO opening dates | ➕ Thêm khi có store mới | `script/domains/nso/generate.py` |
| NSO delivery schedule | ➕ Thêm khi có store mới | `script/dashboard/export_weekly_plan.py` NSO_SCHEDULE |

## ⚠️ Date Normalization

Ngày do người input nên format không chuẩn. LUÔN normalize:

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

---

## Workflow

### 1. Chuẩn bị file Excel tuần mới

User tạo file `Lịch đi hàng ST W{nn}.xlsx` trong:
```
output/artifacts/weekly transport plan/
```

### 2. Cập nhật NSO stores (nếu có khai trương mới)

Thêm store mới vào **3 nơi**:

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

**c. Master schedule** (data/master_schedule.json + .xlsx):
```json
{
  "code": "A999",
  "short": "A999",
  "name": "Tên Siêu Thị",
  "schedule_chia": "Ngày chia 3-5-7",
  "schedule_ve": "Thứ 2-4-6",
  "shift": "Đêm"
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

---

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

---

## Key Logic trong export_weekly_plan.py

### Kiểm kê Cross-Check
- Step 1: **Xóa** kiểm kê sai từ Excel gốc (ngày không phải D hoặc D-1)
- Step 2: **Đánh dấu** D và D-1 đúng từ Google Sheets

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

---

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

---

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

---

## Files

| File | Vai trò |
|------|---------|
| `data/master_schedule.json` | 🔒 Master data: lịch chia/về/shift cố định |
| `data/master_schedule.xlsx` | 🔒 Backup Excel (review/edit bằng tay) |
| `script/dashboard/export_weekly_plan.py` | Parse Excel → JSON, cross-check kiểm kê, NSO châm hàng |
| `docs/data/weekly_plan.json` | Data layer cho dashboard tab |
| `docs/index.html` | Dashboard UI — tab "📅 Lịch Tuần" |
| `script/dashboard/deploy.py` | Deploy (domain: `weekly_plan`) |
| `output/artifacts/weekly transport plan/` | Source Excel files |
| `script/domains/nso/generate.py` | NSO STORES (opening dates) |
| `script/lib/sources.py` | INVENTORY_SHEET_URL |

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| NSO store không hiện châm hàng | Check code trong NSO STORES + NSO_SCHEDULE + master_schedule.json |
| Kiểm kê không hiện hoặc hiện sai | Re-export (script fetch lại kiểm kê mới nhất). Check date normalization |
| Excel export bị UUID filename | Dùng `XLSX.writeFile()` thay vì blob URL |
| Excel export lỗi format | Check console (F12), `xlsx-js-style` CDN load |
| Dashboard data cũ | Hard refresh (Ctrl+Shift+R) — JSON fetch đã có cache-bust `?t=timestamp` |
| Duplicate code (A179) | Script match bằng code + name. Stores không match → cleanup |

## Formatting Rules (áp dụng toàn project)
- Số hàng nghìn: dùng dấu "," (toLocaleString)
- KHÔNG viết tắt bất kỳ ký tự nào trong report
- Vietnamese diacritics: giữ nguyên, không bỏ dấu
- Ngày tháng: dd/mm/yyyy (display), date object (internal comparison)
