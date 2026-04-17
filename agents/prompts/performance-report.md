# Performance Report — Prompt & Context

## Role
Tạo báo cáo hiệu suất vận chuyển hàng tháng: on-time SLA, route compliance, trip completion.

---

## 5 KPI chính

1. **On-time SLA** — Giao trong khung giờ cam kết của kho
2. **On-time Per Destination** — Giao đúng giờ kế hoạch từng điểm
3. **Route Compliance (Đúng Tuyến)** — Giao đúng thứ tự tuyến (all-or-nothing per route)
4. **Plan Compliance (Đúng Kế Hoạch)** — Thứ tự giao thực tế khớp kế hoạch per-destination
5. **Trip Completion** — Tỷ lệ hoàn thành chuyến

### Interactive Features
- **Kho filter**: Mỗi chart có filter buttons (Tổng / KRC / THỊT CÁ / ...)
- **Date range filter**: Chọn ngày Từ/Đến → charts + cards tự cập nhật

---

## Lịch Giao Hàng Theo Kho

| Kho | Lịch giao | Ghi chú |
|---|---|---|
| **THỊT CÁ** | DAILY (7/7) | |
| **KRC** | DAILY (7/7) | |
| **ĐÔNG MÁT** | 6/7 — **Không giao Thứ 2** | |
| **KSL (DRY)** | 6/7 — **Không giao CN** | Ngoại lệ: CN khai trương vẫn giao |

---

## Kiến trúc Data

```
DS chi tiết chuyến xe (*.xlsx)  →  trip data (KRC, ĐÔNG MÁT, KSL)
         ↓
monthly_plan_T{mm}.json         →  plan data + thitca_actual
         ↓
generate_performance_report.py
         ↓
PERFORMANCE_REPORT (HTML) + RAW_DATA (Excel)
```

### Incremental Trip Cache
- Cache: `output/trip_cache_T{mm}.json` (per month)
- First run: reads all files, builds cache
- Subsequent runs: **skips cached files**, only reads new ones
- Reset: `Remove-Item "output\trip_cache_T*.json"`

---

### Kho Mapping (NOI_CHUYEN_MAP)

| noi_chuyen (col 8) | Kho |
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

### Sub-kho classification (ĐÔNG MÁT → ĐÔNG / MÁT)
Based on "Loại rổ" (col S):
- `Tote ABA đông mát` → **ĐÔNG**
- `Rổ ABA đông mát` / `Thùng Carton, Bịch nguyên` → **MÁT**

> **Dedup key bao gồm sub_kho.** Cùng 1 trip giao ĐÔNG và MÁT = 2 deliveries riêng.

### Trip Data Columns

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

### THỊT CÁ Data
- **Actual**: `monthly_plan_T{mm}.json` → `thitca_actual[]`
- **Dedup key**: `(date, store, tuyen)`
- T04 đổi cấu trúc: Script auto-detect sheet name + column layout

### Plan Data

| Kho plan | Nguồn |
|---|---|
| KRC | Google Sheet KRC |
| DRY | Google Sheet KFM, tab DRY |
| ĐÔNG MÁT | 2 Google Drive folders (KH HÀNG ĐÔNG + KH HÀNG MÁT) |
| THỊT CÁ | Google Sheet KFM + BÁO CÁO GIAO HÀNG external |

---

## SLA Windows

| Kho | Start | End |
|---|---|---|
| KRC | 03:00 | 05:30 |
| THỊT CÁ | 03:00 | 06:00 |
| ĐÔNG MÁT | 09:00 | 16:00 |
| KSL-Sáng | 12:00 | 14:00 |
| KSL-Tối | 22:00 | 00:30 (overnight) |

> **Giao SỚM = ĐÚNG GIỜ.** Chỉ tính TRỄ khi qua sla_end.

## On-time Plan
```
arrival_time ≤ planned_time → ĐÚNG ✅
arrival_time > planned_time → TRỄ ❌
thiếu planned_time          → KHÔNG TÍNH
```

> **KHÔNG tự fill planned_time từ ngày khác** (giờ KH biến động 94-585 phút giữa các ngày).

## Route Compliance
```
ALL-or-NOTHING per route: 1 store sai thứ tự → cả tuyến tính SAI.
1-store route → ĐÚNG mặc định.
```

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
