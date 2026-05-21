# Session 20/05/2026 — Daily Report Hotfixes + Performance Investigation

## Mục tiêu
- Fix daily report realtime pipeline (thiếu capacity KRC, scheduler fail)
- Investigate performance dashboard realtime sync

---

## Fixes Applied

### Fix #1 — Task Scheduler Python Path
- **Vấn đề**: `SyncRealtime` dùng `python` → fail trong non-interactive context
- **Fix**: XML import với full path `C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe`
- **Kết quả**: `Last Result = 0` ✅ (lần đầu chạy thành công lúc 17:00)

### Fix #2 — Schedule Fingerprint Date Format
- **Vấn đề**: `sync_realtime.py` query `ngay` column dùng ISO `2026-05-20` nhưng DB lưu VN `20/05/2026`
- **Fix**: Convert format trong `check_schedule_fingerprint()` → 742 rows matched
- **File**: `script/data_pipeline/sync_realtime.py`

### Fix #3 — KRC Capacity DB Fallback
- **Vấn đề**: KRC capacity chỉ đọc local Excel files → thiếu data hôm nay
- **Fix**: Thêm `read_po_krc_from_db()` query ClickHouse (`kf_purchase_order` + `kf_receipt_items`)
- **Kết quả**: KRC 0 → **24.65 tấn** (1249 dates từ DB) ✅
- **File**: `script/domains/daily/capacity_forecast.py`

### Fix #4 — Lock chỉ block Telegram, không block Dashboard
- **Vấn đề**: Sau 8AM → lock → dashboard không update cả ngày
- **Fix**: Lock giờ chỉ ngăn gửi lại Telegram, dashboard tiếp tục update realtime
- **Kết quả**: dry-run sau lock → phát hiện data changed (81938→82769) → sẵn sàng deploy ✅
- **File**: `script/data_pipeline/sync_realtime.py`

### Barcode Classification
- 26 mã barcode thiếu → thêm vào ABA Master Data (2 ĐÔNG, 24 MÁT)
- Hàng MÁT tăng từ 11.9T → **24.5T** ✅

---

## New Files

| File | Mô tả |
|------|--------|
| `script/data_pipeline/sync_monitor.py` | 1 command xem full pipeline status |

**Usage**: `python script/data_pipeline/sync_monitor.py --days 3`

---

## Investigation: Performance Dashboard Realtime

### Scheduled Tasks

| Task | Schedule | Python Path | Trạng thái |
|------|----------|-------------|------------|
| `SyncRealtime` | 15 phút | ✅ Fixed | Running |
| `TripCutoff` | T3 09:00 | ❌ `python` (no path) | Never run |
| `TripReminder` | CN 08:00 | ❌ `python` (no path) | Never run |

### DB Trip Data — Kết quả điều tra

StarRocks **THIẾU** 2 fields quan trọng cho performance report:

| Cần | Có trên DB? | Ghi chú |
|-----|-------------|---------|
| `arrival_time` per store | ❌ | Chỉ có `completed_at` trip-level |
| Tên siêu thị (store name) | ❌ | Chỉ có MongoDB ObjectIDs |
| Nơi chuyển (warehouse) | ❌ | Chỉ có `t_from_location_id` |
| Container type (tote/rổ) | ✅ | Bảng `trips_locations_items` |

→ **Realtime qua DB không khả thi** → phải dùng file-watch trên xlsx folder

### User Requirements cho Performance

| # | Yêu cầu | Trigger |
|---|---------|---------|
| 1 | Trip hoàn thành → auto update dashboard | Realtime (file watch) |
| 2 | Thứ 2 8AM: summary incomplete trips qua Telegram | Weekly |
| 3 | Thứ 3 8AM: cutoff generate báo cáo tuần trước | Weekly |

### Pending Decision
- **Q1**: `arrival_time` per store có ở source khác không? (ClickHouse khác, API KFM?)
- Nếu có → realtime hoàn toàn qua DB
- Nếu không → file-watch (monitor xlsx folder)

---

## Next Steps
1. Fix python path cho `TripCutoff` + `TripReminder`
2. User trả lời Q1 → chọn hướng realtime
3. Build `sync_performance.py` (file watch hoặc DB)
4. Monday Telegram summary script
