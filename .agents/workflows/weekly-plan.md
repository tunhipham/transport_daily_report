---
description: Generate or update the weekly transport plan (Lịch về hàng siêu thị)
---

# Weekly Transport Plan Workflow

> Tạo và cập nhật Lịch Tuần giao hàng siêu thị. Làm mỗi thứ 5, review thứ 6/7 cho W+1.
> Dashboard tab: 📅 Lịch Tuần
> Context: [agents/prompts/weekly-plan.md](../../../agents/prompts/weekly-plan.md)

## ⚠ MANDATORY: Read roles & prompts FIRST
Before doing ANYTHING:
1. Read `agents/role.md` — nguyên tắc chung, phạm vi, quy ước output
2. Read `agents/prompts/weekly-plan.md` — NSO logic, Excel format, master schedule rules

## Rules

1. **Weekly cadence**: Làm vào thứ 5 hàng tuần, review lại thứ 6/7 cho tuần W+1
2. **Lịch cố định**: Lịch chia/về/shift cố định trong `data/master_schedule.json`. Chỉ thay đổi khi user confirm
3. **NSO châm hàng**: Khai trương = 4 ngày liên tiếp châm hàng (D→D+3), sau đó về lịch daily
4. **NSO dời lịch**: Store có `original_date` → bỏ ra khỏi tuần cũ, chỉ tính tuần mới
5. **Kiểm kê**: Tự động fetch từ Google Sheets, đánh dấu D và D-1. Xóa kiểm kê sai từ Excel gốc
6. **Excel export**: File xuất format y chang sheet "Lịch về hàng" gốc
7. **Không viết tắt**: Tất cả label trên dashboard và report phải viết đầy đủ

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

Deploy luôn lên live:

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

**NSO dời lịch**: Nếu `original_date` khác `opening_date`:
- Bỏ châm hàng khỏi tuần gốc
- Chỉ áp dụng châm hàng cho tuần mới

## Excel Export Format

- **Row 1**: Empty
- **Row 2**: "LỊCH VỀ HÀNG SIÊU THỊ" | count | week label (nền xanh đậm)
- **Row 3**: Date header (nền đỏ)
- **Row 4**: Column headers (nền vàng)
- **Row 5+**: Data — Châm hàng (cam), Kiểm kê (đỏ/hồng)
- **Không** xuất 4 cột: Lịch chia, Lịch về, Khai trương, Kiểm kê

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| NSO không hiện châm hàng | Check code trong 3 nơi: NSO STORES + NSO_SCHEDULE + master_schedule.json |
| Kiểm kê sai/thiếu | Re-export (script fetch lại mới nhất). Check date normalization |
| Excel bị UUID filename | Dùng `XLSX.writeFile()` thay vì blob URL |
| Dashboard data cũ | Hard refresh — JSON fetch đã có cache-bust `?t=timestamp` |
| Số stores thiếu | So sánh danh sách active stores vs W{nn} Excel file |
