# Session 22/05/2026 — Fix PO KRC Capacity Forecast

## Tóm tắt
Fix cách tính tonnage PO KRC từ ClickHouse DB cho dashboard capacity forecast.
Số cũ sai hoàn toàn (~25T), số mới đúng range 40-60T.

## 4 vấn đề đã fix

### 1. Weight mapping (ảnh hưởng lớn nhất)
- ~50% items có `net_weight = 0` (rau/củ/quả tươi)
- Fix: fallback qua **Google Sheets master data** (cùng source với transfer PT)
- File: `script/domains/daily/capacity_forecast.py` → `read_po_krc_from_db()`

### 2. Sai cột tham chiếu
- **Date**: `delivery_date` → `delivery_date_vendor_confirm` (ngày NCC xác nhận)
- **Qty**: `ri.qty` → `ri.po_qty` (số lượng đặt)

### 3. Data trùng lặp
- Cùng PO + barcode xuất hiện 2 lần trên receipt_items
- Fix: `GROUP BY ri.purchase_code, ri.product_barcode`

### 4. Không filter PO Hủy
- "Hủy" trên app = `list_sub_status` chứa **11** trên DB
- **KHÔNG phải** `status=6` hay `deleted=true`
- Fix: `AND NOT has(po.list_sub_status, 11)`

## DB Status mapping (kf_purchase_order)

| `list_sub_status` | App status | Nên tính? |
|--------------------|-----------|-----------|
| KHÔNG chứa 11 | Hoàn tất / Đã duyệt | ✅ Có |
| Chứa 11 | **● Hủy** | ❌ Bỏ |

## Query flow
```
PO_Headers.delivery_date_vendor_confirm → ngày
  → filter: deleted=0, NOT has(list_sub_status, 11)
  → JOIN receipt_items ON purchase_code
  → GROUP BY purchase_code + barcode (dedup)
  → po_qty × weight(master_data) / 1,000,000 = tons
```

## Weight priority (giống transfer PT)
1. `ri.net_weight` (grams) từ DB
2. Google Sheets master data (`MASTER_SHEET_URL` Col A=barcode, Col Z=weight grams)
3. `extract_weight_from_name()` từ tên sản phẩm

## Kết quả T5/2026
- Range: **47-78T** (trước: 25-124T)
- Alerts > 65T: **3 ngày** (trước: 15 ngày)
- Đúng range thực tế 40-60T ✅

## File changed
- `script/domains/daily/capacity_forecast.py` → `read_po_krc_from_db()`
