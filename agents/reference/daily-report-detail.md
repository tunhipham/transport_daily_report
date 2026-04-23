# Daily Report — Chi Tiết Data Schema & Logic

> ⚠ File này chỉ cần đọc khi **debug hoặc sửa script**.
> Khi chạy report bình thường, chỉ cần đọc `agents/prompts/daily-report.md`.

---

## Data Sources

| Source | Method | Backup file (`data/`) |
|--------|--------|----------------------|
| KRC | Online (Google Sheets) | `krc_DDMMYYYY.xlsx` |
| KFM (KSL-Sáng/Tối) | Online (Google Sheets) | `kfm_DDMMYYYY.xlsx` |
| KH MEAT | Online (Google Drive) | `kh_meat_DDMMYYYY.xlsx` |
| KH HÀNG ĐÔNG | Online (Google Drive) | `kh_hàng_đông_DDMMYYYY.xlsx` |
| KH HÀNG MÁT | Online (Google Drive) | `kh_hàng_mát_DDMMYYYY.xlsx` |
| Master data | Online (Google Sheets) | `master_data.xlsx` |
| Transfer | Online (Google Drive) | `transfer_DDMMYYYY.xlsx` |
| Yêu cầu KSL | Online (Google Drive) | `yeu_cau_chuyen_hang_thuong_DDMMYYYY.xlsx` |

### Backup System

- **Auto-save**: Fetch online thành công → tự lưu vào `data/`
- **Auto-fallback**: Online lỗi → tự dùng backup nếu có
- **Dùng chung**: Các task khác (compose_mail, du_kien_giao...) đọc data từ `data/`

### Data Source Links

- KFM Google Sheets: https://docs.google.com/spreadsheets/d/1LkJFJhOQ8F2WEB3uCk7kA2Phvu8IskVi3YBfVr7pBx0/edit
- KRC Google Sheets: https://docs.google.com/spreadsheets/d/1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII/edit
- KH Google Drive: https://drive.google.com/drive/folders/1th0myHfLtdz3uTBFf2EuQ6G1GywjufYE
- Transfer Google Drive: https://drive.google.com/drive/folders/17Z_UPMDywWFplcg0fx3XSG87vSsG8LHb
- Yeu cau Google Drive: https://drive.google.com/drive/folders/1DpDon0QHhDRoX7_ZnEygwKlXsbcPGp-t

---

## History Data Management

- **File**: `output/history.json` — lưu tối đa 30 ngày snapshot
- **Cấu trúc per entry**: `date`, `total_sthi`, `total_items`, `total_xe`, `total_tons`, `khos.{kho}.{san_luong_tan, sl_items, sl_xe, sl_sthi}`

### ⚠️ Lock Policy

> **Data ngày D đã chạy → LOCKED.**
> Script `update_history()` chỉ thêm/update entry ngày hiện tại.
> Entries cũ trong `history.json` KHÔNG BAO GIỜ bị ghi đè.
>
> - Ngày hôm sau chạy report → chỉ **thêm entry mới** vào cuối array
> - Nếu chạy lại **cùng ngày** → **replace** entry cùng ngày (cho phép sửa data trong ngày)
> - Giới hạn tối đa **30 entries** → entries cũ nhất bị xóa khi vượt quá
> - Không có cơ chế backfill — data ngày cũ giữ nguyên trạng thái lúc chạy

### STHI Per Kho

- **Từ 16/04/2026 trở đi**: `sl_sthi` được lưu per kho
- **Trước 16/04/2026**: Entries cũ không có `sl_sthi` → auto-distribute `total_sthi` theo tỷ lệ `sl_xe`

---

## Dashboard & Biểu Đồ

### Interactive HTML Dashboard

- **Date Picker**: Dropdown chọn ngày từ history → Cards, Table, Donut cập nhật tự động
- **Chart.js Trend charts**: Sản lượng/Items/Xe theo kho — interactive tooltips
- **Range Filter**: Quick buttons 7/14/30 ngày + custom Từ/Đến
- **Weekly SVG charts**: Trend theo tuần, hiển thị song song
- **Embedded Data**: Toàn bộ history embed vào HTML → 1 file duy nhất

### PNG cho Telegram — Tỉ lệ biểu đồ

Gửi Telegram: **5 ảnh PNG** (Bảng KPI, Đóng góp, Trend Sản lượng, Trend Items, Trend Xe) + **1 tin nhắn text** thông báo dashboard đã cập nhật kèm link + note refresh 1-2p. Không gửi file HTML.

**Multi-group**: Gửi đồng thời tới tất cả `chat_ids` trong `config/telegram.json` → `daily.chat_ids[]`. Message IDs tracked per-group (key: `{date_tag}_{chat_id}`) để hỗ trợ xóa khi gửi lại.

| Thông số | Daily SVG | Weekly SVG |
|----------|-----------|------------|
| **viewBox** | `0 0 760 340` | `0 0 760 340` |
| **Padding** | L=65, R=25, T=25, B=70 | L=65, R=25, T=25, B=70 |
| **Data points** | **14 ngày** | **5 tuần** |
| **Responsive** | `width:100%; height:auto` | `width:100%; height:auto` |

Layout CSS: `align-items: stretch` + `.chart-box { flex: 1 }` → 2 khung luôn bằng nhau.

### HTML Dashboard Layout

- Daily trends: **Chart.js** (Canvas) — `.ccw { height: 300px }`
- Weekly trends: **SVG** responsive — `viewBox="0 0 760 340"`
- Layout: **CSS Grid** `grid-template-columns: 1fr 1fr` + `align-items: stretch`

---

## Chi Tiết Cách Lấy Data & Cách Tính

### Tổng quan 2 nhóm data

Script chia data thành **2 nhóm** xử lý riêng, rồi gộp lại tính KPI:

| Nhóm | Hàm | Nguồn | Output |
|---|---|---|---|
| **STHI + XE** | `read_sthi_data()` | KRC, KFM, KH MEAT, KH ĐÔNG, KH MÁT | Danh sách `{kho, diem_den, tuyen}` |
| **PT (Phiếu Tách)** | `read_pt_data()` | Transfer, Yêu cầu KSL + Master data | Danh sách `{kho, sl, tl_grams}` |

### Nhóm STHI + XE — Cách lấy data

#### KRC (Google Sheets → sheet "KRC")

| Cột | Index | Nội dung | Dùng để |
|---|---|---|---|
| A | 0 | Ngày (DD/MM/YYYY) | Lọc theo ngày |
| G | 6 | Điểm đến | → `diem_den` (đếm siêu thị) |
| H | 7 | Giờ đến | Phải có giá trị mới tính |
| K | 10 | Tuyến | → `tuyen` (đếm xe) |

- Kho: cố định = `"KRC"`
- Điều kiện: `ngày == date_str` AND `diem_den` NOT empty AND `gio_den` NOT empty

#### KFM — DRY Sheet (Google Sheets XLSX)

| Cột | Index | Nội dung |
|---|---|---|
| A | 0 | Ngày |
| E | 4 | Giờ đi |
| G | 6 | Điểm đến |
| H | 7 | Giờ đến |
| K | 10 | Tuyến |

**Phân loại Sáng/Tối:**

```
Nếu có Giờ đến:
  Giờ đến < 18h  →  KSL-SÁNG
  Giờ đến >= 18h →  KSL-TỐI

Nếu chỉ có Giờ đi (không có Giờ đến):
  Giờ đi < 15h   →  KSL-SÁNG
  Giờ đi >= 15h  →  KSL-TỐI
```

> Multi-stop: dòng không có giờ nhưng dòng trước cùng ngày có → kế thừa kho của dòng trước.

#### KH files (Google Drive → Excel)

| File | Kho gán | Cột Điểm đến | Cột Tuyến |
|---|---|---|---|
| KH MEAT | `THỊT CÁ` | C (2) | L (11) |
| KH HÀNG ĐÔNG | `ĐÔNG MÁT` | C (2) | J (9) |
| KH HÀNG MÁT | `ĐÔNG MÁT` | C (2) | J (9) |

- Tìm file theo tên chứa ngày format `DD.MM.YYYY`
- KH ĐÔNG + KH MÁT gộp chung vào kho `ĐÔNG MÁT`

### Nhóm PT — Cách lấy data

#### Master Data (Google Sheets)

- Col A = Barcode, Col Z (25) = Trọng lượng (grams/item)
- Load 1 lần → `master_tl[barcode] = grams`

#### Transfer (Local sync hoặc Google Drive)

| Cột | Index | Nội dung |
|---|---|---|
| A | 0 | Ngày → lọc theo ngày |
| C | 2 | Kho raw → map qua `KHO_MAP` |
| H | 7 | Mã hàng (barcode) |
| K | 10 | Số lượng → `sl` |
| O | 14 | Trọng lượng → `tl_grams` |

**Mapping kho raw → kho report:**

| Raw | → Report |
|---|---|
| KHO ABA MIỀN ĐÔNG | THỊT CÁ |
| KHO ABA QUÁ CẢNH | ĐÔNG MÁT |
| KHO RAU CỦ | KRC |
| Sáng / ĐI SÁNG / Socola | KSL-SÁNG |
| Tối / ĐI TỐI / Khách đặt | KSL-TỐI |

- Nếu cột TL = 0 → fallback dùng `master_tl[barcode]`
- Cũng xây `transfer_tl[barcode]` để dùng cho Yêu cầu KSL

#### Yêu cầu chuyển hàng (Google Drive)

| Cột (auto-detect header) | Nội dung |
|---|---|
| Barcode | Mã barcode |
| Tên sản phẩm | Fallback tính TL từ tên |
| Số lượng cần chuyển | → `sl` |
| PLO ghi chú | → Kho raw (map qua `KHO_MAP`) |

**Fallback trọng lượng** (3 cấp ưu tiên):
1. `master_tl[barcode]`
2. `transfer_tl[barcode]` (từ file transfer cùng ngày)
3. Regex tên SP: tìm `XXkg`, `XXg`, `XXml`, `XXL` trong tên

### Cách đếm Siêu Thị và Xe

```
SL Siêu thị = COUNT(DISTINCT diem_den) per kho
SL Xe        = COUNT(DISTINCT tuyen)    per kho
```

- Dùng `set()` → tự loại trùng
- `tuyen` rỗng → bỏ qua (không đếm xe, nhưng vẫn đếm siêu thị)
- KH ĐÔNG + KH MÁT gộp tuyến vào **chung 1 set** `ĐÔNG MÁT` → trùng tên tuyến chỉ tính 1

**Cột tuyến mỗi nguồn:**

| Nguồn | Cột Tuyến | Kho |
|---|---|---|
| KRC | K (10) | KRC |
| KFM DRY | K (10) | KSL-SÁNG / KSL-TỐI |
| KH MEAT | L (11) | THỊT CÁ |
| KH HÀNG ĐÔNG | J (9) | ĐÔNG MÁT |
| KH HÀNG MÁT | J (9) | ĐÔNG MÁT |

### Cách tính Items và Tấn

```
SL Items       = SUM(sl)                        per kho    ← từ PT data
Sản lượng Tấn  = SUM(sl × tl_grams) / 1,000,000 per kho   ← từ PT data
```

> `sl` = số lượng sản phẩm, `tl_grams` = trọng lượng mỗi item (grams)

### Công thức KPI

| KPI | Công thức | Ý nghĩa |
|---|---|---|
| **Tấn/Xe** | `Tấn ÷ SL Xe` | Tải trọng TB mỗi xe |
| **Items/ST** | `Items ÷ SL Siêu thị` | Items TB mỗi siêu thị |
| **ST/Xe** | `SL Siêu thị ÷ SL Xe` | Số điểm giao TB mỗi xe |
| **KG/ST** | `Tấn × 1000 ÷ SL Siêu thị` | KG TB mỗi siêu thị |

Dòng TOTAL = SUM tất cả 5 kho, KPI tính trên tổng (không phải TB các kho).

### So sánh tự động (Commentary)

- **vs Hôm qua**: so với ngày liền trước trong history
- **vs LFL**: so với cùng thứ tuần trước (-7 ngày)
- Hiển thị `▲ +X%` (xanh) hoặc `▼ -X%` (đỏ)
