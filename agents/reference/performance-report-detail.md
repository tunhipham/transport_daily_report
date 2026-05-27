# Performance Report — Detail Reference

> Chỉ đọc file này khi debug hoặc sửa code. Không đọc khi chạy report bình thường.

---

## Kiến trúc Data

### Mode Realtime (`--realtime`)

```
ClickHouse (kf_trip_locations_items)  →  trip data (KRC, ĐÔNG MÁT, KSL)
          ↓
fetch_plan_incremental.py             →  today's plan merged into cache
          ↓
monthly_plan_T{mm}.json               →  plan data + thitca_actual
          ↓
generate.py --realtime
          ↓
PERFORMANCE_REPORT (HTML) + RAW_DATA (Excel) + performance.json
          ↓
deploy.py --domain performance        →  GitHub Pages
```

### Mode Manual (default)

```
DS chi tiết chuyến xe (*.xlsx)  →  trip data (KRC, ĐÔNG MÁT, KSL)
         ↓
monthly_plan_T{mm}.json         →  plan data + thitca_actual
         ↓
generate.py
         ↓
PERFORMANCE_REPORT (HTML) + RAW_DATA (Excel)
```

### Incremental Trip Cache (Manual mode only)
- Cache: `output/state/trip_cache_T{mm}.json` (per month)
- First run: reads all files, builds cache
- Subsequent runs: skips cached files, only reads new ones
- Reset: `Remove-Item "output\state\trip_cache_T*.json"`

### Incremental Plan Cache (Realtime mode)
- `fetch_plan_incremental.py` chỉ fetch plan cho ngày hôm nay (~30s)
- Merge vào `monthly_plan_T{mm}.json` — thay rows cũ cho ngày đó
- Google Sheet KRC + KFM download ~15s mỗi cái
- KH ĐÔNG MÁT đọc local file (instant)

---

## ClickHouse DB Schema (Realtime)

### `kf_trip_locations_items`

| DB Column | Mapped to | Notes |
|---|---|---|
| `t_code` | trip_id | |
| `t_status` | trip_status | 1=pending, 2=delivering, 3=completed, 4=cancelled |
| `t_license_number` | vehicle_number | |
| `t_driver_name` | driver | |
| `t_driver_phone` | phone | |
| `t_departure` | date, depart_time | |
| `t_from_location_name_abbreviates` | noi_chuyen | Array, dùng `arrayJoin()` |
| `tl_branch_id` | dest (via JOIN) | JOIN `kf_branch_location.id` |
| `tl_arrival` | arrival_time | NULL/empty = chưa đến |
| `barrel_basket_name` | container_type | "tote" → ĐÔNG, else → MÁT |

### `kf_branch_location` (lookup)

| Column | Use |
|---|---|
| `branch_name_abbreviate` | dest (viết tắt: A103, LVY, VH2...) |
| `branch_code` | Same as abbreviate |
| `branch_name` | Full name (không dùng cho matching) |

---

## Completion Logic

```
# Destination level
complete = dest_status == "Hoàn thành" OR arrival_time IS NOT NULL

# Trip level
complete = trip_status == "Hoàn thành" OR trip has ≥1 dest with arrival_time

# Driver level
Same as destination level
```

> Trips có status=2 (đang giao) nhưng tài xế đã đến cửa hàng → tính hoàn thành.

---

## Kho Mapping (NOI_CHUYEN_MAP)

| noi_chuyen | Kho |
|---|---|
| KRC | **KRC** |
| QCABA | **ĐÔNG MÁT** |
| KSL | **KSL-Sáng** hoặc **KSL-Tối** (theo giờ) |
| SLKT | **KSL-Tối** (luôn là tối) |

**KSL Session logic:**
```
ref_time = arrival_time → depart_time → mặc định KSL-Sáng
if ref_time.hour < 15 → KSL-Sáng
else                   → KSL-Tối
```

---

## Sub-kho Classification (ĐÔNG MÁT → ĐÔNG / MÁT)

Based on `barrel_basket_name`:
- `Tote ABA đông mát` → **ĐÔNG**
- `Rổ ABA đông mát` / `Thùng Carton, Bịch nguyên` → **MÁT**

> **Dedup key bao gồm sub_kho.** Cùng 1 trip giao ĐÔNG và MÁT = 2 deliveries riêng.

---

## Trip Data Columns (Excel — Manual mode)

| Cột | Index | Ý nghĩa |
|-----|-------|---------|
| Mã trip | 0 | trip_id |
| Trạng thái trip | 1 | trip_status |
| Tài xế | 3 | driver |
| Ngày xuất phát | 5 | date |
| Giờ xuất phát | 6 | depart_time |
| Nơi chuyển | 8 | noi_chuyen → kho mapping |
| Điểm đến | 9 | dest |
| Trạng thái điểm đến | 11 | dest_status |
| Loại thùng/rổ | 18 | container_type → sub_kho |
| Giờ đến | 26 | arrival_time |

---

## THỊT CÁ Data

- **Actual**: `monthly_plan_T{mm}.json` → `thitca_actual[]`
- **Source**: File BÁO CÁO GIAO HÀNG (manual update)
- **Dedup key**: `(date, store, tuyen)`
- T04 đổi cấu trúc: Script auto-detect sheet name + column layout
- **Không có trên ClickHouse** — luôn từ file

---

## Plan Data Sources

| Kho plan | Nguồn | Fetch |
|---|---|---|
| KRC | Google Sheet KRC | `fetch_krc_today()` |
| DRY | Google Sheet KFM, tab DRY | `fetch_dry_today()` |
| ĐÔNG MÁT | Local `KH HÀNG ĐÔNG` + `KH HÀNG MÁT` | `fetch_dongmat_today()` |
| THỊT CÁ | Google Sheet KFM + BÁO CÁO GIAO HÀNG | Manual via `fetch_monthly.py` |

---

## Automation Scripts

| Script | Location | Purpose |
|---|---|---|
| `fetch_db_realtime.py` | `script/domains/performance/` | ClickHouse trip fetch |
| `fetch_plan_incremental.py` | `script/domains/performance/` | Today's plan → merge cache |
| `trip_reminder.py` | `script/telegram/` | T2+T3 Telegram incomplete trips |
| `trip_cutoff_export.py` | `script/telegram/` | T3 9h Excel + Telegram |
| `run-realtime-performance.bat` | `tools/` | Batch runner |
| `check-realtime-status.bat` | `tools/` | Status check |
| `run-trip-cutoff.bat` | `tools/` | Manual cutoff |

---

## Known Gotchas

| # | Vấn đề | Giải pháp |
|---|--------|-----------|
| 1 | HÀNG MÁT folder path có dấu tiếng Việt | Unicode escape |
| 2 | Drive API không list file mới | Fallback: đọc local `G:\My Drive\` |
| 3 | KSL CN khai trương vẫn giao | VẪN CÓ PLAN |
| 4 | Giờ KH biến động lớn giữa các ngày | KHÔNG fill từ ngày khác |
| 5 | SLKT = KSL-Tối | Đã thêm NOI_CHUYEN_MAP |
| 6 | T04 BÁO CÁO GIAO HÀNG đổi layout | Auto-detect |
| 7 | HÀNG ĐÔNG tuyến là số (1-6) | Script prefix "HĐ" |
| 8 | tl_arrival NULL vs empty string | Check cả 2: `""` và `"0001-01-01T00:00:00Z"` |
| 9 | THỊT CÁ không có trên ClickHouse | Chỉ từ file BÁO CÁO GIAO HÀNG |
| 10 | `t_from_location_name_abbreviates` là Array | Dùng `arrayJoin()` trong SQL |
