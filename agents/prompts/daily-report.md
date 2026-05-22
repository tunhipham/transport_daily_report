# Daily Report — Prompt

## Role

AI assistant cho báo cáo vận chuyển hàng ngày hệ thống logistics ABA.
Nhiệm vụ: chạy generate.py, validate output, gửi Telegram.

---

## 5 Kho

KRC (rau củ), THỊT CÁ, ĐÔNG MÁT, KSL-SÁNG (DRY sáng), KSL-TỐI (DRY tối)

## KPI Definition

```
SL Siêu thị = COUNT(DISTINCT diem_den) per kho
SL Xe       = COUNT(DISTINCT tuyen)    per kho
Items       = SUM(sl)                  per kho
Tấn         = SUM(sl × tl_grams) / 1,000,000 per kho
```

| KPI | Công thức |
|---|---|
| Tấn/Xe | Tấn ÷ SL Xe |
| Items/ST | Items ÷ SL Siêu thị |
| ST/Xe | SL Siêu thị ÷ SL Xe |
| KG/ST | Tấn × 1000 ÷ SL Siêu thị |

TOTAL = SUM tất cả 5 kho, KPI tính trên tổng (không phải TB các kho).

---

## Lịch Giao Hàng (Validation Rules)

| Kho | Lịch | Ghi chú |
|---|---|---|
| THỊT CÁ | 7/7 | Luôn có trip |
| KRC | 7/7 | Luôn có trip |
| ĐÔNG MÁT | 6/7 | **Không giao Thứ 2** |
| KSL (DRY) | 6/7 | **Không giao CN** (ngoại lệ: 1-3 chuyến khai trương) |

→ Ngày thường mà thiếu kho = **warning**, check lại nguồn.

---

## Output

- Dashboard HTML interactive (1 file self-contained)
- 5 PNG gửi Telegram: Bảng KPI, Đóng góp, Trend Sản lượng, Trend Items, Trend Xe
- 1 tin nhắn text: thông báo dashboard đã cập nhật + link + note refresh 1-2p
- **Gửi tất cả groups** cấu hình trong `config/telegram.json` → `daily.chat_ids[]`
- History: `output/state/history.json` (tối đa 30 ngày)
- So sánh: vs hôm qua + vs cùng thứ tuần trước → `▲ +X%` / `▼ -X%`

---

## Khi lỗi

Nếu script lỗi hoặc output bất thường (data = 0, thiếu kho, KPI sai...) →
đọc `agents/reference/daily-report-detail.md` để hiểu data schema, column mapping,
và business logic trước khi debug.

---

## Capacity Forecast — PO KRC Realtime (ClickHouse)

Script: `script/domains/daily/capacity_forecast.py` → `read_po_krc_from_db()`

### Data flow

```
kf_purchase_order (PO header)
  ├── delivery_date_vendor_confirm → ngày NCC xác nhận giao hàng
  ├── code → mã PO
  ├── deleted = 0
  └── NOT has(list_sub_status, 11) → bỏ PO Hủy
        │
        JOIN ON purchase_code
        ▼
kf_receipt_items (chi tiết SP)
  ├── product_barcode → map master data lấy weight
  ├── po_qty → số lượng đặt
  └── net_weight → weight (grams), nhiều item = 0
        │
        GROUP BY purchase_code + barcode (dedup)
        ▼
  po_qty × weight_grams / 1,000,000 = TONS
```

### Weight fallback (cùng logic với transfer PT)

| Priority | Source | Ghi chú |
|----------|--------|---------|
| 1 | `ri.net_weight` | grams, từ DB |
| 2 | Google Sheets master data | `MASTER_SHEET_URL` Col A=barcode, Col Z=weight (grams) |
| 3 | `extract_weight_from_name()` | Parse từ tên SP (VD: "500G" → 500) |

> [!IMPORTANT]
> Cả **transfer (PT)** và **PO KRC** dùng cùng 1 source master data:
> `MASTER_SHEET_URL` trong `lib/sources.py` — ~26,651 barcodes.

### DB status → App status

| `list_sub_status` | App | Tính tonnage? |
|-------------------|-----|:---:|
| **Chứa 11** | **● Hủy** | ❌ |
| Không chứa 11 | Hoàn tất / Đã duyệt | ✅ |

> [!WARNING]
> "Hủy" trên app **KHÔNG** dùng `status` hay `deleted` — mà dùng `list_sub_status` chứa `11`.
> DB chỉ có status 1/3/5/7, không có status 6. `deleted` luôn = false.

### Dedup

Cùng PO + barcode có thể xuất hiện 2+ lần trên `kf_receipt_items` (PO ảo do cutoff).
→ `GROUP BY ri.purchase_code, ri.product_barcode` + dùng `any()` cho các cột khác.

### Benchmark

- KRC trung bình: **40-65 tấn/ngày**
- Ngưỡng alert: **65T** (vượt 5%+)
- Ngày gần (chưa NCC xác nhận hết): số có thể thấp hơn thực tế
