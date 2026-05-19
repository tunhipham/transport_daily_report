# Data Source Reference — Pipeline V2
# =====================================
# Confirmed mappings from DB investigation session 2026-05-19.
# This is the SINGLE SOURCE OF TRUTH for all DB → domain mappings.
# Future realtime pipelines MUST read from these exact sources.
#
# Machine-readable config: config/data_sources.json
# Pipeline code MUST import data_sources.json for table/column/filter info.
#
# Last updated: 2026-05-19

---

## 1. Transfer (Phiếu chuyển hàng)

**DB**: ClickHouse (`kdb`)  
**Table**: `kf_transfer_mart`  
**Rows**: ~52M total, ~88K/day  
**Used by**: Daily report (`generate.py`)

### Query template
```sql
SELECT 
    code,
    product_id,
    from_branch_id,
    to_branch_id,
    transfer_quantity,     -- SL chuyển (chỉ dùng cột này, KHÔNG dùng received_quantity)
    transfer_date          -- DateTime, filter chính
FROM kf_transfer_mart
WHERE toDate(transfer_date) = '{DATE}'
  AND deleted = 0
  AND status != 6          -- Bỏ phiếu HỦY
```

### Branch mapping (kho xuất)
```python
BRANCH_MAP = {
    "5fdc170ebd89c10006f15b7c": "KHO RAU CỦ",          # KRC  — ~29K rows/ngày
    "61d4ffa72997ae0007f5ad19": "KHO ABA QUÁ CẢNH",    # ĐÔNG/MÁT — ~26K
    "639d80531a37c70007cbb7bf": "KHO ABA MIỀN ĐÔNG",   # THỊT CÁ — ~21K
    "6234219eb35d1d00073793ab": "KHO DRY",              # DRY — ~9K
}
# 192+ other branch IDs = chuyển liên siêu thị → BỎ QUA
```

### Product lookup (tên SP, barcode, trọng lượng)
```sql
-- JOIN: kf_transfer_mart.product_id = kf_product_static.id
SELECT p.name, p.base_barcode, p.barcodes, p.unit_name, p.base_net_weight
FROM kf_product_static p
WHERE p.id = '{product_id}'
```
- `base_barcode`: barcode chính (string: EAN 13 số, số ngắn, hoặc mã nội bộ)
- `base_net_weight`: trọng lượng (grams), VD: 1000 = 1kg
- **Coverage**: 100% product_ids đều có trong product_static

### Status values
| Status | Meaning | Include? |
|--------|---------|----------|
| 1 | Tạo mới | Tùy context |
| 2 | Đang pick | Tùy context |
| 3 | Đã pick / chờ giao | ✅ |
| 5 | Đã nhận | ✅ |
| 6 | HỦY | ❌ BỎ |

---

## 2. Delivery Schedule (Lịch giao hàng)

**DB**: StarRocks (`kfm_scm`)  
**Table**: `krc_dashboard_delivery_schedule`  
**Rows**: ~4.9M total, ~750/day  
**Used by**: Daily report (`generate.py`)

### Query template
```sql
SELECT source, ngay, diem_den, gio_den_dk, tuyen
FROM krc_dashboard_delivery_schedule
WHERE ngay = '{DD/MM/YYYY}'
ORDER BY source, tuyen
```

### Source values
| Source | Meaning | Kho |
|--------|---------|-----|
| `KRC` | Kho rau củ | KRC |
| `DRY` | Kho dry | DRY |
| `THIT_CA` | Thịt cá | ABA MIỀN ĐÔNG |
| `DONG_MAT` | **Hàng mát** | ABA QUÁ CẢNH |
| `DONG_LANH` | **Hàng đông** | ABA QUÁ CẢNH |

### Field format
- `ngay`: VARCHAR, format `DD/MM/YYYY`
- `diem_den`: VARCHAR, mã siêu thị (VD: `A121`, `HNN`, `PKD`)
- `gio_den_dk`: VARCHAR, giờ đến dự kiến (VD: `11:00`, `9:20`)
- `tuyen`: VARCHAR, tuyến đường (VD: `CN1-A131-HNN`, hoặc số `1`)

---

## 3. Trips (Chuyến xe — Performance)

**DB**: ClickHouse (`kdb`)  
**Table**: `kf_trip_locations_items`  
**Rows**: ~990K total, ~4.7K/day  
**Used by**: Performance report (`generate.py`)

### Query template (completed trips only)
```sql
SELECT 
    t_code,                              -- Mã chuyến
    t_license_number,                    -- Biển số xe
    t_driver_name,                       -- Tên tài xế
    t_departure,                         -- Giờ xuất phát (DateTime)
    t_from_location_name_abbreviates,    -- Tên kho viết tắt (Array)
    tl_branch_id,                        -- Branch ID điểm đến
    toTimeString(tl_arrival) AS actual_time  -- Giờ đến thực tế (CHỈ LẤY GIỜ, ko lấy ngày)
FROM kf_trip_locations_items
WHERE toYear(t_departure) BETWEEN 2023 AND 2027    -- Filter data lỗi (0.01%)
  AND toDate(t_departure) BETWEEN '{START}' AND '{END}'
  AND t_status = 3                                   -- CHỈ trip hoàn thành
```

### Status values
| Status | Meaning | Rows (30 days) | Include? |
|--------|---------|----------------|----------|
| 1 | Tạo mới | 1,226 | ❌ |
| 2 | Đang giao | 39,445 | ❌ |
| **3** | **Hoàn thành** | **79,202** | **✅** |
| 4 | ? (legacy) | 1,091 | ❌ |

### Actual time rule
- **actual_time** = `tl_arrival` (giờ đến cửa hàng)
- **CHỈ lấy TIME** (HH:MM), KHÔNG lấy ngày
- **Ngày** vẫn dựa vào `t_departure` (ngày xuất phát)

### Data quality
- `t_departure` có 0.01% data lỗi (năm 1970, 2105...) → filter `toYear BETWEEN 2023 AND 2027`
- `tl_arrival` coverage (status=3): 99.8% có giá trị

---

## 4. Yêu cầu chuyển hàng (KSL — Capacity Forecast)

**Source**: FILE LOCAL (không dùng DB)  
**Path**: `G:\My Drive\DOCS\DAILY\yeu_cau_chuyen_hang_thuong\yeu_cau_chuyen_hang_thuong_DDMMYYYY.xlsx`  
**Used by**: `capacity_forecast.py`

> ⚠ Quyết định giữ file local vì DB timing không kịp cutoff 8:00.
> DB equivalent: `kf_req_transfer_items` (ClickHouse, kdb) — 33K rows/day, 278K items

---

## 5. Product Master

**DB**: ClickHouse (`kdb`)  
**Table**: `kf_product_static`  
**Rows**: ~29K  
**Used by**: Transfer lookup, barcode → weight

### Key fields
| Field | Type | Example |
|-------|------|---------|
| `id` | String | `5f0c31f55dfec1000669a95d` |
| `name` | String | `CÁ THU ĐAO NC RĐ 8-10CON/KG` |
| `base_barcode` | String | `1101257` |
| `barcodes` | String | `1101257,1101344` (comma-separated) |
| `unit_name` | String | `KG`, `HỘP`, `TÚI` |
| `base_net_weight` | Float64 | `1000` (grams) |

---

## 6. Monday 8AM Reminder — Incomplete Trips

**Trigger**: Scheduler, 8:00 sáng thứ Hai  
**Channel**: Telegram bot cá nhân  
**Data**: Trips chưa hoàn thành tuần trước

### Query
```sql
SELECT DISTINCT
    t_code,                              -- Mã chuyến
    t_from_location_name_abbreviates,    -- Tên kho
    tl_branch_id,                        -- → cần map sang tên siêu thị
    toDate(t_departure) AS departure_date
FROM kf_trip_locations_items
WHERE toYear(t_departure) BETWEEN 2023 AND 2027
  AND toDate(t_departure) BETWEEN '{MONDAY_LAST_WEEK}' AND '{SUNDAY_LAST_WEEK}'
  AND t_status IN (1, 2)                 -- Chưa hoàn thành
ORDER BY t_departure
```

### Message format
```
🔴 Trips chưa hoàn thành tuần {W}:

TRIP0000052526 | QCABA → [tên ST] | 19/05/2026
TRIP0000052496 | QCABA → [tên ST] | 19/05/2026
...

Tổng: {N} trips
```

---

## DB Connections

| DB | Host | Port | User | Database |
|---|---|---|---|---|
| StarRocks | 103.147.122.56 | 9030 | kfm_scm_lam_nguyen | kfm_scm |
| ClickHouse | 103.140.248.114 | 32015 | scm_lam | kdb |

Config files: `config/mcp_starrocks.json`, `config/mcp_clickhouse.json`
