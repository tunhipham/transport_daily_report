---
description: Generate or update the weekly transport plan (Lịch về hàng siêu thị)
---

# Weekly Transport Plan Workflow

> Tạo và cập nhật Lịch Tuần giao hàng siêu thị.
> **Thứ 5 hàng tuần**: 12h check data → 13h generate + send review → user confirm → gửi team
> Dashboard tab: 📅 Lịch Tuần
> Context: [agents/prompts/weekly-plan.md](../../../agents/prompts/weekly-plan.md)

## ⚠ MANDATORY: Read roles & prompts FIRST
Before doing ANYTHING:
1. Read `agents/role.md` — nguyên tắc chung, phạm vi, quy ước output
2. Read `agents/prompts/weekly-plan.md` — NSO logic, Excel format, master schedule rules

## Rules

1. **Weekly cadence**: Làm vào thứ 5 hàng tuần, review lại thứ 6/7 cho tuần W+1
2. **Lịch cố định**: Lịch về/shift cố định trong `data/master_schedule.json`. Chỉ thay đổi khi user confirm
3. **NSO châm hàng**: Khai trương = 4 ngày liên tiếp châm hàng (D→D+3), sau đó về lịch daily
4. **NSO dời lịch**: Store có `original_date` → bỏ ra khỏi tuần cũ, chỉ tính tuần mới
5. **Kiểm kê**: Tự động fetch từ Google Sheets, đánh dấu D và D-1. Xóa kiểm kê sai từ Excel gốc
6. **Excel export**: File xuất format y chang sheet "Lịch về hàng" gốc
7. **Không viết tắt**: Tất cả label trên dashboard và report phải viết đầy đủ

## Workflow

### 1. Generate file Excel tuần mới

Script tự tạo file `Lịch đi hàng ST W{nn}.xlsx` từ `master_schedule.json` + kiểm kê + NSO:

// turbo
```powershell
python script/domains/weekly_plan/generate_excel.py --week {nn}
```

Output: `output/artifacts/weekly transport plan/Lịch đi hàng ST W{nn}.xlsx`

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
    "A999": {"schedule_ve": "Thứ 2-4-6", "shift": "Đêm",
             "name_full": "Tên Siêu Thị"},
}
```

**c. Master schedule** (data/master_schedule.json + .xlsx):
```json
{
  "code": "A999",
  "short": "A999",
  "name": "Tên Siêu Thị",
  "schedule_ve": "Thứ 2-4-6",
  "shift": "Đêm"
}
```

> [!NOTE]
> A112 Cô Giang có `schedule_ve: "Ngày chẵn"` — logic đặc biệt: về hàng vào ngày chẵn (2,4,6,8...). Script tự tính dynamic theo tuần.

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

---

## Thursday Finalize Automation (Thứ 5)

Script: `script/domains/weekly_plan/finalize.py`
Telegram: gửi vào **tin nhắn cá nhân** (`config/telegram.json` → key `weekly_plan`)

### Flow tự động

```
12:00 Thu  →  finalize.py --check
              ├─ Check master_schedule.json (stores đủ?)
              ├─ Check NSO châm hàng tuần tới
              ├─ Check kiểm kê (Google Sheets)
              ├─ Check Excel file đã tồn tại?
              └─ Gửi Telegram reminder (data status + issues)

13:00 Thu  →  finalize.py --send
              ├─ Run generate_excel.py --week {nn}
              ├─ Gửi file Excel qua Telegram review
              └─ Chờ user confirm → gửi team (--deliver)
```

### Commands

| Lệnh | Khi nào dùng |
|-------|-------------|
| `python script/domains/weekly_plan/finalize.py --check` | 12h: Check readiness + gửi reminder |
| `python script/domains/weekly_plan/finalize.py --send` | 13h: Generate Excel + gửi review |
| `python script/domains/weekly_plan/finalize.py --test` | Test: gửi file Excel mới nhất qua Telegram |

### Task Scheduler

| Task Name | Schedule | Command |
|-----------|----------|---------|
| `WeeklyPlan_12h_Check` | Thu 12:00 | `finalize.py --check` |
| `WeeklyPlan_13h_Send` | Thu 13:00 | `finalize.py --send` |

> [!TIP]
> Nếu cần chạy thủ công (không đợi scheduler):
> ```powershell
> python script/domains/weekly_plan/finalize.py --check   # kiểm tra data
> python script/domains/weekly_plan/finalize.py --send    # generate + gửi review
> ```

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

**Skip D+4**: Sau D+3, chỉ skip D+4 nếu D+4 là ngày delivery:
- D+4 IS delivery day → skip (giảm tải 1 ngày sau châm hàng)
- D+4 NOT delivery day → đã có gap tự nhiên → không skip
- VD: KT 25/04, daily 3-5-7 → D+4=T4→ NOT daily → T5 30/04 về bt

## Excel Export Format

- **Row 1**: Empty
- **Row 2**: "LỊCH VỀ HÀNG SIÊU THỊ" | count | week label (nền xanh đậm)
- **Row 3**: Date header (nền đỏ)
- **Row 4**: Column headers (nền vàng)
- **Row 5+**: Data — Châm hàng (cam), Kiểm kê (đỏ/hồng)
- **Không** xuất 4 cột: Lịch chia, Lịch về, Khai trương, Kiểm kê

---

## Auto-Watch Kiểm Kê (Thứ 2)

Hệ thống tự động giám sát lịch kiểm kê mỗi thứ 2. Script: `script/dashboard/auto_inventory_watch.py`

### Flow hoạt động

```
Task Scheduler (thứ 2 07:00) → auto_inventory_watch.py --watch
  └─ Mỗi 1h (07:00 → 17:30):
       ├─ Đọc weekly_plan.json → lấy danh sách kiểm kê tuần hiện tại (BEFORE)
       ├─ Chạy export_weekly_plan.py (fetch Google Sheets mới)
       ├─ Đọc weekly_plan.json mới → lấy danh sách kiểm kê (AFTER)
       ├─ So sánh BEFORE vs AFTER:
       │     ├─ 🆕 Store thêm kiểm kê trong tuần
       │     ├─ 🔄 Store đổi ngày kiểm kê
       │     ├─ 🗑️ Store hủy kiểm kê
       │     └─ ✅ Không thay đổi
       ├─ Deploy lên GitHub Pages
       └─ Gửi Telegram notify (xóa message cũ → gửi mới)
```

### So sánh gì?

Chỉ so sánh **stores có `inventory_date` rơi vào tuần hiện tại** (vd W17: 20/04–26/04).
Không quan tâm stores có kiểm kê tuần khác.

### Telegram message

Notify gửi vào **tin nhắn cá nhân** (không gửi vào group ILT).
Mỗi lần gửi message mới sẽ **xóa message trước** (luôn chỉ có 1 message).

**Không thay đổi:**
```
📋 Kiểm Kê W17 (20/04–26/04)
🕐 Cập nhật: 20/04/2026 09:36

✅ Lịch kiểm kê tuần này không thay đổi (10 stores)
🔗 https://tunhipham.github.io/transport_daily_report/
```

**Có thay đổi:**
```
📋 Kiểm Kê W17 (20/04–26/04)
🕐 Cập nhật: 20/04/2026 10:15

🔄 Đổi lịch (1):
  • A108 KFM_HCM_TDU - Cây Keo: 24/04 → 25/04

🆕 Thêm kiểm kê (1):
  • A999 KFM_HCM_XXX - Store Mới: 22/04

✅ Dashboard đã cập nhật
🔗 https://tunhipham.github.io/transport_daily_report/
```

### State & Logs

| File | Nội dung |
|------|----------|
| `output/state/inventory_watch_state.json` | `last_telegram_msg_id` (để xóa message cũ) |
| `config/telegram.json` → key `weekly_plan` | `chat_id: 5782090339` = personal chat (không phải group) |
| `output/state/inventory_watch.lock` | Lock file chống chạy trùng instance |
| `output/logs/inventory_watch.log` | Log chi tiết mỗi cycle |

### Register Task Scheduler (1 lần)
```powershell
schtasks /create /tn "KFM_InventoryWatch" /xml "config\auto_inventory_watch_task.xml"
```

### Commands

| Lệnh | Khi nào dùng |
|-------|-------------|
| `python script/dashboard/auto_inventory_watch.py --backup` | Fetch thủ công bất kỳ ngày nào |
| `python script/dashboard/auto_inventory_watch.py --backup --dry-run` | Xem thay đổi mà không deploy/notify |
| `python script/dashboard/auto_inventory_watch.py --watch` | Watch mode (chỉ chạy thứ 2) |
| `python script/dashboard/auto_inventory_watch.py --force` | Chạy 1 shot, bỏ qua check thứ 2 |

> [!TIP]
> `--backup` bỏ qua check thứ 2 và chạy 1 lần: đọc BEFORE → export → đọc AFTER → diff → deploy → notify.
> Thêm `--dry-run` để xem thay đổi mà không deploy/notify.

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| NSO không hiện châm hàng | Check code trong 3 nơi: NSO STORES + NSO_SCHEDULE + master_schedule.json |
| NSO ngày đầu sau châm bị skip sai | Check skip-first-day logic: `generate_excel.py` và `export_weekly_plan.py` |
| Kiểm kê sai/thiếu | Re-export (script fetch lại mới nhất). Check date normalization |
| Excel bị UUID filename | Dùng `XLSX.writeFile()` thay vì blob URL |
| Dashboard data cũ | Hard refresh — JSON fetch đã có cache-bust `?t=timestamp` |
| Số stores thiếu | So sánh danh sách active stores vs W{nn} Excel file |
| Watch không chạy | Check lock file `output/state/inventory_watch.lock` — xóa nếu stale |
| Telegram không gửi | Check `config/telegram.json` key `weekly_plan` |
| Telegram không xóa cũ | Check `output/state/inventory_watch_state.json` có `last_telegram_msg_id` |
| Finalize không chạy | Check Task Scheduler: `schtasks /query /tn "WeeklyPlan_12h_Check"` |
