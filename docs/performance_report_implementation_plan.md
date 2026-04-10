# Implementation Plan: Performance Report — On-time & Trip Completion

## Tổng quan

Script `generate_performance_report.py` tổng hợp dữ liệu vận chuyển theo tháng, tính toán 4 chỉ tiêu KPI cho từng kho, xuất HTML dashboard + Excel raw data.

**4 KPI chính:**
1. **On-time SLA** — Giao trong khung giờ cam kết của kho
2. **On-time Plan** — Giao đúng giờ kế hoạch từng điểm
3. **Route Compliance** — Giao đúng thứ tự tuyến
4. **Trip Completion** — Tỷ lệ hoàn thành chuyến

---

## Lịch Giao Hàng Theo Kho

| Kho | Lịch giao | Ghi chú |
|---|---|---|
| **THỊT CÁ** | DAILY (7/7) | Ngày nào cũng phải có trip, giờ actual, giờ planned |
| **KRC** | DAILY (7/7) | Ngày nào cũng phải có trip, giờ actual, giờ planned |
| **ĐÔNG MÁT** | 6/7 — **Không giao Thứ 2** | Thứ 2 sẽ không có trip |
| **KSL (DRY)** | 6/7 — **Không giao Chủ Nhật** (ngoại lệ bên dưới) | |

### KSL Chủ Nhật — Ngoại lệ khai trương:
- Bình thường CN không giao, nhưng **siêu thị khai trương cuối tuần vẫn giao**
- Tăng cường ~1-3 chuyến/CN (ít hơn ngày thường rất nhiều)
- Tầm 2-4 siêu thị khai trương/tuần
- Chủ yếu giao **ban đêm** → đa số thuộc **KSL-Tối**
- **VẪN CÓ PLAN** — dữ liệu KHÔNG được để trống

> [!IMPORTANT]
> Quy tắc: đã có trip trạng thái "Hoàn thành" thì **BẮT BUỘC** có giờ giao dự kiến (planned_time) và giờ đến (arrival_time).
> Nếu thiếu → retry mapping data → nếu vẫn không thấy → báo user check data nguồn.

### Cột "Giao Hàng" (Y / N)
- **Y** = arrival_time có giá trị (đã giao, có giờ đến)
- **N** = arrival_time rỗng (chưa giao / đã hủy / chưa cập nhật)
- **Nếu Giao = N → KHÔNG trả**: giờ đến, giờ kế hoạch, đúng tuyến, SLA
- Chỉ tính vào **Trip Completion** (đếm tổng để so hoàn thành vs chưa)

---

## Kiến trúc

```
┌──────────────────────────────────┐
│  DS chi tiết chuyến xe (*.xlsx)  │──→ trip data (KRC, ĐÔNG MÁT, KSL)
│  G:\DAILY\DS chi tiet chuyen xe │
└──────────────────────────────────┘
                 ↓
┌──────────────────────────────────┐
│  monthly_plan_T{mm}.json        │──→ plan data (planned_time, tuyến)
│  output/                        │    + thitca_actual
└──────────────────────────────────┘
                 ↓
        generate_performance_report.py
                 ↓
        ┌──────────────────────┐
        │ PERFORMANCE_REPORT   │ ← HTML dashboard (charts)
        │ RAW_DATA             │ ← Excel raw data
        └──────────────────────┘
```

---

## 1. Data Loading

### 1.1. Trip Data (KRC, ĐÔNG MÁT, KSL)

| Thông tin | Chi tiết |
|-----------|----------|
| **Nguồn** | `G:\My Drive\DOCS\DAILY\DS chi tiet chuyen xe\T{mm}.26\*.xlsx` |
| **Sheet** | "Sheet 1" |
| **Dedup key** | `(trip_id, dest, sub_kho)` → giữ row đầu tiên |

**Các cột dùng từ trip data:**

| Cột | Index | Ý nghĩa |
|-----|-------|---------|
| Mã trip | 0 | trip_id |
| Trạng thái trip | 1 | trip_status ("Hoàn thành" / ...) |
| Tài xế | 3 | driver |
| Ngày xuất phát | 5 | date |
| Giờ xuất phát | 6 | depart_time (fallback cho KSL session) |
| Nơi chuyển | 8 | noi_chuyen → kho mapping |
| Điểm đến | 9 | dest (store code) |
| Trạng thái điểm đến | 11 | dest_status ("Hoàn thành" / ...) |
| Giờ đến | 26 | arrival_time |
| Loại thùng/rổ | 18 | container_type → xác định sub_kho (ĐÔNG/MÁT) |

> [!IMPORTANT]
> **Dedup key bao gồm sub_kho.** Cùng 1 trip đến cùng 1 siêu thị nhưng giao ĐÔNG (Tote) và MÁT (Rổ) là **2 deliveries riêng biệt** với **2 planned time khác nhau** (từ KH HÀNG ĐÔNG vs KH HÀNG MÁT). Phải giữ cả 2 rows.
>
> Ví dụ: Trip 45831 → store EMR ngày 01/04:
> - ĐÔNG (Tote): planned 09:00 (tuyến HĐ1)
> - MÁT (Rổ): planned 09:30 (tuyến KF01)
> → 2 rows, 2 plan time, 2 on-time evaluations.

### 1.2. Phân loại Kho (Warehouse Mapping)

| noi_chuyen (col 8) | Kho |
|---|---|
| KRC | **KRC** |
| QCABA | **ĐÔNG MÁT** |
| KSL | **KSL-Sáng** hoặc **KSL-Tối** |

**KSL Session logic:**
```
ref_time = arrival_time (ưu tiên)
         → depart_time (fallback nếu arrival rỗng)
         → mặc định KSL-Sáng (nếu cả 2 rỗng)

if ref_time.hour < 15 → KSL-Sáng
else                   → KSL-Tối
```

> Hiện tại có ~62 rows (2%) KSL mặc định KSL-Sáng do cả arrival + depart đều rỗng (trip hủy).

> [!WARNING]
> **KHÔNG BAO GIỜ** có kho tên "DRY" trong output. DRY chỉ dùng nội bộ cho plan lookup.
> Trip bị "Đã Hủy" (arrival rỗng) vẫn phải xếp KSL-Sáng/Tối dựa trên depart_time.

### 1.3. THỊT CÁ Data

| Thông tin | Chi tiết |
|-----------|----------|
| **Nguồn** | `output/monthly_plan_T{mm}.json` → key `thitca_actual[]` |
| **Dedup key** | `(date, store, tuyen)` |
| **Đặc biệt** | Có sẵn cả `actual_time` + `planned_time` |
| **Fallback planned_time** | Nếu `planned_time` rỗng → tự động đọc `KH MEAT` folder (col "Du kien giao") |

> [!NOTE]
> **Fallback chain cho THỊT CÁ planned_time:**
> 1. Đọc từ file BÁO CÁO GIAO HÀNG MIỀN ĐÔNG (`thitca_actual`)
> 2. Nếu thiếu → fallback về folder `G:\My Drive\DOCS\DAILY\KH MEAT\` (col "Du kien giao", auto-detect)
> 3. Cả entry mới (chưa có trong plan_lookup) lẫn entry đã có nhưng `planned_time` rỗng đều được fill

### 1.4. Plan Data

| Thông tin | Chi tiết |
|-----------|----------|
| **Nguồn** | `output/monthly_plan_T{mm}.json` → key `plan[kho][]` |
| **Kho keys trong JSON** | KRC, DRY, ĐÔNG MÁT, THỊT CÁ |
| **Lookup key** | `(date, store, kho)` — thêm `(date, store, sub_kho)` cho ĐÔNG MÁT |

**Plan data fetch bằng `fetch_monthly_plan.py`:**

| Kho plan | Nguồn | Ghi chú |
|---|---|---|
| KRC | Google Sheet KRC (`1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII`) | Tab KRC |
| DRY | Google Sheet KFM (`1LkJFJhOQ8F2WEB3uCk7kA2Phvu8IskVi3YBfVr7pBx0`) | Tab DRY |
| ĐÔNG MÁT | 2 Google Drive folders (xem bên dưới) | |
| THỊT CÁ | Google Drive folder KH MEAT | |

**ĐÔNG MÁT plan = 2 folders:**
- `KH HÀNG ĐÔNG` (hàng đông, ~69-76 stores/ngày, 6 tuyến, tuyến số 1-6 → prefix "HĐ" thành HĐ1-HĐ6)
- `KH HÀNG MÁT` (hàng mát, ~150-157 stores/ngày, ~25-30 tuyến, tuyến chữ KF01/QC02...)

> [!NOTE]
> HÀNG ĐÔNG dùng tuyến **số** (1-6), script tự thêm prefix "HĐ" (→ HĐ1, HĐ2...) để phân biệt với tuyến HÀNG MÁT (KF01...).

**Forward-fill tuyến:**
- Google Sheets chỉ ghi tuyến ở row đầu mỗi nhóm → script fill xuống cho rows tiếp theo cùng ngày

**Plan lookup cho KSL:**
- Trip kho = KSL-Sáng/Tối → lookup trong plan kho = **"DRY"** (DRY plan lấy từ Google Sheet KFM, tab DRY)

> [!IMPORTANT]
> **KHÔNG fallback plan cross-kho.** Mỗi kho có khung window time riêng.
> Trip kho nào thì chỉ lookup plan kho đó.
>
> **ĐÔNG MÁT plan lookup order:**
> 1. Thử `(date, store, sub_kho)` trước — ĐÔNG hoặc MÁT riêng
> 2. Fallback `(date, store, "ĐÔNG MÁT")` nếu sub_kho ko match
>
> Sub_kho được xác định từ **tuyến prefix**: HĐ → ĐÔNG, KF/QC → MÁT.

---

## 2. Metric: On-time SLA

### SLA Windows:

| Kho | Start | End | Ghi chú |
|---|---|---|---|
| KRC | 03:00 | 05:30 | |
| THỊT CÁ | 03:00 | 06:00 | |
| ĐÔNG MÁT | 09:00 | 16:00 | |
| KSL-Sáng | 12:00 | 14:00 | |
| KSL-Tối | 22:00 | 00:30 | Overnight |

### Logic:
```
# Tất cả kho (trừ KSL-Tối):
if arrival_time <= sla_end → ON-TIME ✅
else                       → LATE ❌

# KSL-Tối (overnight):
if arrival.hour >= 15                          → ON-TIME ✅
if arrival.hour == 0 and arrival.minute <= 30  → ON-TIME ✅
else                                           → LATE ❌
```

> [!NOTE]
> **Giao SỚM = ĐÚNG GIỜ.** Chỉ tính TRỄ khi qua `sla_end`.
> Chỉ tính cho rows **có arrival_time** (Giao=Y).
> Đơn vị: **điểm giao** (destinations), không phải chuyến.

---

## 3. Metric: On-time Plan (Kế Hoạch)

### Logic:
```
planned_time = lấy từ trip data (THỊT CÁ có sẵn)
             → hoặc từ plan_lookup[(date, dest, sub_kho)]  (ưu tiên nếu có sub_kho)
             → hoặc từ plan_lookup[(date, dest, kho)]       (fallback)
             → KSL: lookup kho = "DRY"
             → THỊT CÁ fallback: nếu thiếu → **tự động** check KH MEAT Drive folder (col "Du kien giao")
             → KRC fallback: check store code typo (VD: LVYu → LVY)
             → ĐÔNG MÁT fallback: nếu Drive API ko thấy file → đọc local `G:\My Drive\DOCS\DAILY\{folder}`

if arrival_time <= planned_time → ĐÚNG ✅ (Sớm)
if arrival_time > planned_time  → TRỄ ❌
if thiếu planned_time           → KHÔNG TÍNH (bỏ qua, không đưa vào mẫu)
```

> [!WARNING]
> **On-time Plan ≠ Đúng tuyến (Route Compliance).** Đây là 2 metric KHÁC NHAU:
> - **On-time Plan** = giờ đến ≤ giờ KH? (đo **thời gian**)
> - **Route Compliance** = thứ tự giao == thứ tự KH? (đo **trình tự**)
>
> Một delivery có thể đúng giờ nhưng sai tuyến (TX đi tắt), hoặc đúng tuyến nhưng trễ giờ (do kẹt xe).
> Hai metric này cho kết quả rất khác nhau (~78% vs ~43%).

> [!IMPORTANT]
> **Quy tắc bắt buộc:** Trip trạng thái "Hoàn thành" → PHẢI có planned_time + arrival_time.
> Nếu thiếu planned_time → retry mapping data (re-fetch plan source hoặc KH Drive folder).
> Vẫn không thấy → báo user check lại data nguồn.
> **KHÔNG tự fill planned_time từ ngày khác** (giờ KH biến động 94-585 phút giữa các ngày).

---

## 4. Metric: Route Compliance (Đúng Tuyến)

### Logic:
```
1. Gom (arrival_time, dest) theo (date, tuyen, kho)
2. Sort actual theo arrival_time → thứ tự giao thực tế
3. Lấy planned_order từ route_order[(date, tuyen, kho)] (sort planned_time)
4. Lọc: chỉ so stores CÓ TRONG CẢ HAI (plan ∩ actual)
5. Nếu chỉ có 1 store → tuyến đó ĐÚNG mặc định (chỉ 1 điểm thì không có sai thứ tự)

So sánh:
   actual_filtered  == planned_filtered → TẤT CẢ = ĐÚNG ✅
   actual_filtered  != planned_filtered → TẤT CẢ = SAI ❌
```

> Lưu ý: DRY có ~23-25% route chỉ 1 store → tự động tính ĐÚNG.

> [!WARNING]
> **ALL-or-NOTHING per route:** 1 store sai thứ tự → cả tuyến tính SAI.
> Đơn vị: **điểm giao** (destinations).

---

## 5. Metric: Trip Completion

### Destination level:
```
Tổng: đếm tất cả rows
Hoàn thành: đếm rows có dest_status == "Hoàn thành"
Tỷ lệ = Hoàn thành / Tổng
```

### Trip level:
```
Dedup theo (trip_id, kho)
Hoàn thành: trip_status == "Hoàn thành"
```

---

## 6. Output Files

### HTML Report: `PERFORMANCE_REPORT_T{mm}+T{mm}_YYYY.html`
- Dashboard Chart.js: 4 chart (SLA, Plan, Route, Completion)
- Filter theo kho
- Dark theme

### Excel Raw Data: `RAW_DATA_T{mm}+T{mm}_YYYY.xlsx`

| Cột | Header | Ý nghĩa |
|-----|--------|---------|
| A | Tuần | W10, W11... |
| B | Ngày | DD/MM/YYYY |
| C | Thứ | Thứ 2-CN |
| D | Kho | KRC / THỊT CÁ / ĐÔNG MÁT / KSL-Sáng / KSL-Tối |
| E | Phân Loại | ĐÔNG / MÁT — chỉ cho kho ĐÔNG MÁT (theo loại rổ col S trip data) |
| F | Giao Hàng | Y (có arrival_time) / N (rỗng) — **N thì I~O trống** |
| G | Mã Trip / Tuyến | Trip ID hoặc tuyến (THỊT CÁ) |
| H | Điểm Đến | Store code |
| I | Giờ Đến | HH:MM (actual) — chỉ khi Giao=Y |
| J | Giờ Kế Hoạch | HH:MM (planned) — chỉ khi Giao=Y |
| K | Đúng Tuyến | Đúng / Sai — chỉ khi Giao=Y + có tuyến |
| L | Thứ Tự KH | Rank kế hoạch (1, 2, 3...) — vị trí store trong tuyến theo plan |
| M | Thứ Tự TT | Rank thực tế (1, 2, 3...) — vị trí store theo thứ tự giao thực tế |
| N | SLA | Sớm / Đúng / Trễ — chỉ khi Giao=Y |
| O | Kế Hoạch vs Thực Tế | Sớm / Đúng / Trễ — chỉ khi Giao=Y + có KH |

> [!NOTE]
> **Phân Loại ĐÔNG MÁT** (col E): dựa vào cột S ("loại rổ") trong DS chi tiết chuyến xe:
> - `Tote ABA đông mát` → **ĐÔNG**
> - `Rổ ABA đông mát` / `Thùng Carton, Bịch nguyên` → **MÁT** (Carton đi chung trip với MÁT)
>
> **Thứ Tự KH vs TT** (col L, M): so sánh rank để thấy store nào giao đúng/sai vị trí trong tuyến.
> VD: KH = A(1) B(2) C(3), TT giao B-C-A → rank A=3, B=1, C=2

**Route compliance coverage (tham khảo):**
| Kho | Coverage | Ghi chú |
|---|---|---|
| KRC | ~100% | |
| THỊT CÁ | ~100% | |
| KSL-Sáng | ~98% | Thiếu = không có plan |
| KSL-Tối | ~99% | Thiếu = không có plan |
| ĐÔNG MÁT | ~100% | HÀNG ĐÔNG: HĐ1-HĐ6, HÀNG MÁT: KF01-KF30 |

**HTML Dashboard:** có filter ĐÔNG + MÁT riêng, giữ ĐÔNG MÁT tổng.

### Weekly Summary Tables (Bảng Tổng Hợp Tuần)

4 bảng tuần breakdown theo ngày (Thứ 2-CN) + tổng tuần:

| Bảng | KHO key | % On Time logic | Rows |
|---|---|---|---|
| **THỊT CÁ** | `THỊT CÁ` | **SLA-based** (03:00-06:00) | 4 rows |
| **ĐÔNG MÁT** | `ĐÔNG MÁT` | Plan-based + extra **SLA row** | 5 rows |
| **HÀNG ĐÔNG** | `ĐÔNG` | Plan-based + extra **SLA row** | 5 rows |
| **HÀNG MÁT** | `MÁT` | Plan-based + extra **SLA row** | 5 rows |

**Rows per table:**
1. `Tổng Điểm Giao` — SLA total (on_time + late)
2. `Đúng & Sớm Kế Hoạch` — plan on_time count
3. `% On Time` — plan-based (THỊT CÁ dùng SLA thay vì plan)
4. `% On Time (SLA)` — **chỉ cho ĐÔNG MÁT/ĐÔNG/MÁT** (arrival trong window 09:00-16:00)
5. `Tổng Số Chuyến` — completion_trip total

> [!NOTE]
> **THỊT CÁ dùng SLA**: Sếp yêu cầu %ontime THỊT CÁ tính theo khung SLA (03:00-06:00), không theo planned_time từng siêu thị.
> **ĐÔNG/MÁT table format y chang ĐÔNG MÁT**: Đều có plan-based + extra SLA row.

**CSS Sticky:** 2 cột đầu (KHO + Chỉ Tiêu) freeze khi scroll ngang → `position: sticky; left: 0/60px`.

**Color gradient %:**

| % | Màu chữ | Background |
|---|---|---|
| ≥99% | `#4ADE80` (green) | `rgba(34,197,94,0.35)` |
| 95-99% | `#86EFAC` (light green) | `rgba(74,222,128,0.18)` |
| 90-95% | `#EAB308` (yellow) | `rgba(250,204,21,0.28)` |
| 85-90% | `#F97316` (orange) | `rgba(251,146,60,0.3)` |
| 80-85% | `#EF4444` (red) | `rgba(239,68,68,0.3)` |
| <80% | `#FCA5A5` (light red) | `rgba(220,38,38,0.4)` |

### Copy lên Drive:
```powershell
Copy-Item "output\RAW_DATA_*.xlsx" "G:\My Drive\DOCS\transport_daily_report\output\" -Force
```

---

## 7. Known Gotchas & Lưu Ý

| # | Vấn đề | Giải pháp |
|---|--------|-----------|
| 1 | HÀNG MÁT folder path có dấu tiếng Việt | Dùng unicode escape `KH H\u00c0NG M\u00c1T` khi đọc local |
| 2 | Drive API đôi khi không list file mới upload | Đọc local qua `G:\My Drive\` |
| 3 | KSL CN khai trương: vẫn giao 1-3 chuyến | **VẪN CÓ PLAN**, phải có data đầy đủ |
| 4 | ĐÔNG MÁT: Drive API không list file | Fallback: đọc local `G:\My Drive\DOCS\DAILY\{folder_name}\` (auto) |
| 5 | Giờ KH biến động rất lớn giữa các ngày | KHÔNG fill từ ngày khác |
| 6 | STS = Siêu Thị Sỉ | Có plan ở nhiều kho (KRC, DRY, ĐÔNG MÁT) |
| 7 | ĐÔNG MÁT không giao Thứ 2 | Thứ 2 không có trip → bình thường |
| 8 | Trip "Hoàn thành" thiếu planned_time | Retry mapping → báo user nếu vẫn thiếu |
| 9 | KRC store code typo (VD: LVYu thay vì LVY) | Người nhập typo → sửa thủ công + báo user |
| 10 | THỊT CÁ thiếu planned trên báo cáo | Fallback: tự động đọc KH MEAT Drive (col "Du kien giao", auto-detect) |
| 11 | ĐÔNG MÁT tuyến HÀNG ĐÔNG là số (1-6) | Script prefix "HĐ" (HĐ1-HĐ6) để phân biệt với HÀNG MÁT (KF01...) |

---

## 8. Backup & Revert

### TRƯỚC KHI sửa script:
```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"
Copy-Item "script\generate_performance_report.py" "G:\My Drive\DOCS\transport_daily_report\backups\generate_performance_report_$ts.py"
```

### Khi cần revert:
```powershell
Get-ChildItem "G:\My Drive\DOCS\transport_daily_report\backups\generate_performance*" | Sort LastWriteTime -Desc
Copy-Item "G:\My Drive\DOCS\transport_daily_report\backups\generate_performance_report_{ts}.py" "script\generate_performance_report.py"
```

---

## 9. Verification Checklist

Sau khi gen report, **BẮT BUỘC** kiểm tra:
- ✅ Không có kho "DRY" trong raw data
- ✅ ĐÔNG MÁT planned_time coverage > 95%
- ✅ SLA percentages hợp lý (KRC ~94%, ĐÔNG MÁT ~99%, KSL-Tối ~100%)
- ✅ Route compliance có data (không toàn 0%)
- ✅ **Trip "Hoàn thành" mà thiếu planned_time hoặc arrival_time → liệt kê và báo user**
- ✅ Thứ 2 không có trip ĐÔNG MÁT (đúng)
- ✅ Chủ nhật KSL nếu có trip thì phải có plan
- ✅ File Excel copy lên Drive thành công
