# Weekly Transport Plan — Agent Context

## Bối cảnh

Dashboard logistics KFM có 5 tabs. Tab "📅 Lịch Tuần" hiển thị lịch giao hàng siêu thị theo tuần.

**Flow**: `master_schedule.json` → `generate_excel.py` → Excel W{nn} → `export_weekly_plan.py` → JSON → deploy

**Thursday Cadence**: 12h check data → 13h generate + send review → user confirm → gửi team

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
| Lịch về/shift | `data/master_schedule.json` | 🔒 **CỐ ĐỊNH** — chỉ thay đổi khi NSO mới hoặc đổi tuyến |
| Lịch kiểm kê | Google Sheets (INVENTORY_SHEET_URL) | 🔄 **DYNAMIC** — fetch mỗi lần chạy |
| Lịch về hàng (days) | 🤖 Auto-generate từ master_schedule | Script `generate_excel.py` tự tạo Excel |
| NSO opening dates | `script/domains/nso/generate.py` | ➕ Thêm khi có store mới |

## Auto-Watch Kiểm Kê

### Tổng quan

Mỗi **thứ 2**, Task Scheduler tự chạy `auto_inventory_watch.py --watch`:
- Poll mỗi **1 giờ** từ 07:00 → 17:30
- So sánh lịch kiểm kê **trên dashboard** (BEFORE) vs **Google Sheets mới** (AFTER)
- Chỉ quan tâm stores có kiểm kê **trong tuần hiện tại** (vd: W17 = 20/04–26/04)
- Nếu có thay đổi → re-export → deploy → Telegram notify
- Telegram: gửi vào **tin nhắn cá nhân** (không gửi group), xóa message cũ → gửi message mới (luôn chỉ 1 message)

### Scripts & Config

| File | Mô tả |
|------|-------|
| `script/dashboard/auto_inventory_watch.py` | Script chính — fetch, diff, export, deploy, notify |
| `script/dashboard/auto_inventory_watch.bat` | Batch launcher cho Task Scheduler |
| `config/auto_inventory_watch_task.xml` | Task Scheduler config (Monday only, 07:00→17:30) |
| `config/telegram.json` → key `"weekly_plan"` | Bot token + chat_id = **personal** (không phải group) |
| `output/state/inventory_watch_state.json` | Lưu `last_telegram_msg_id` (xóa message cũ) |
| `output/state/inventory_watch.lock` | Lock chống chạy trùng instance |
| `output/logs/inventory_watch.log` | Log chi tiết mỗi cycle |

### Commands

```bash
# Watch mode (auto - chỉ thứ 2)
python script/dashboard/auto_inventory_watch.py --watch

# Backup — chạy thủ công bất kỳ ngày nào
python script/dashboard/auto_inventory_watch.py --backup

# Dry run — xem thay đổi, không deploy/notify
python script/dashboard/auto_inventory_watch.py --backup --dry-run

# Force — chạy 1 shot, bỏ qua check thứ 2
python script/dashboard/auto_inventory_watch.py --force
```

### Week Anchor

Script dùng cùng anchor với `auto_compose.py`:
```python
ANCHOR_WEEK = 14
ANCHOR_START = datetime(2026, 3, 30)  # Monday W14
```

## Cấu trúc project liên quan

```
data/
  master_schedule.json     # 🔒 CỐ ĐỊNH — lịch về/shift (từ sheet CHIA)
script/
  domains/
    weekly_plan/
      generate_excel.py    # 🤖 Generate Excel W{nn} từ master_schedule + kiểm kê + NSO
      finalize.py          # 📋 Thu automation: --check (12h) / --send (13h) / --test
    nso/generate.py          # NSO STORES list (opening dates)
  dashboard/
    export_weekly_plan.py    # Parse Excel → JSON (main logic)
    auto_inventory_watch.py  # 🔄 Auto-watch kiểm kê (thứ 2, mỗi 1h)
    deploy.py                # Git push (supports --domain weekly_plan)
  compose/
    compose_mail.py          # Email composition (cũng fetch kiểm kê)
  lib/
    sources.py               # INVENTORY_SHEET_URL
    telegram.py              # send_telegram_text, delete_telegram_message
output/
  artifacts/
    weekly transport plan/   # Generated Excel files (W14, W15, ...)
docs/
  data/weekly_plan.json      # Output JSON cho dashboard
```

## Key Logic trong export_weekly_plan.py

### A112 Cô Giang — Even-Date Logic
- `schedule_ve: "Ngày chẵn"` → script tự tính dynamic theo tuần
- Về hàng vào ngày chẵn (2,4,6,8...) trong tuần, **trừ Chủ Nhật** (kho không giao)
- Hàm `compute_even_date_schedule()` tính ra "Thứ X-Y-Z" tương ứng

### Đếm Ngày/Đêm (Stats Cards)
- Đếm **Ngày/Đêm** theo field `shift` (độc lập)
- Đếm **Châm hàng/Kiểm kê** theo `days[]` (độc lập)
- Một store có thể vừa Đêm vừa Châm hàng → đếm cả hai

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

### Skip D+4 Rule (NSO)
- Sau D+3, chỉ skip **D+4** nếu D+4 là ngày delivery (giảm tải 1 ngày)
- Nếu D+4 **không phải** ngày delivery → đã có gap tự nhiên → không skip
- VD1: A164 KT 23/04, daily 2-4-6 → D+4=T2 27/04 IS daily → **skip** → bắt đầu T4
- VD2: A163 KT 25/04, daily 3-5-7 → D+4=T4 29/04 NOT daily → **ko skip** → T5 30/04 về bt

### Cleanup false châm hàng  
- Sau khi apply NSO, script strip "Châm hàng" từ stores KHÔNG phải NSO hợp lệ

### Inject missing stores
- NSO stores có opening trong tuần nhưng KHÔNG có trong Excel → inject row mới

## Thursday Finalize Automation

Script: `script/domains/weekly_plan/finalize.py`

| Mode | Lệnh | Schedule |
|------|-------|----------|
| `--check` | Check data readiness + gửi Telegram reminder | Thu 12:00 |
| `--send` | Generate Excel + gửi file review qua Telegram | Thu 13:00 |
| `--test` | Test gửi file Excel mới nhất | Manual |

### Readiness Check (12h)
- Kiểm tra `master_schedule.json` (stores đủ?)
- Kiểm tra NSO châm hàng tuần tới (có store nào khai trương?)
- Fetch kiểm kê từ Google Sheets (entries đủ?)
- Kiểm tra Excel file đã tồn tại chưa
- Gửi summary + issues qua Telegram cá nhân

### Generate & Send (13h)
- Chạy `generate_excel.py --week {nn}` (auto-detect next week)
- Gửi file Excel qua Telegram cá nhân để review
- User confirm → `--deliver` gửi team group

### Task Scheduler
- `WeeklyPlan_12h_Check` — Thu 12:00
- `WeeklyPlan_13h_Send` — Thu 13:00
- Config: `config/telegram.json` → key `weekly_plan` → `chat_id: 5782090339` (personal)
- Tự tính post-châm delivery days theo schedule_ve + shift (áp dụng skip-first-day)

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
