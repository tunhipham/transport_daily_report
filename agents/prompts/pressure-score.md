# Pressure Score (Phân Loại Tồn Kho Chuyển Kho) — Prompt

Xác định SKU tồn cao / xuất thấp → quyết định chuyển kho trước kiểm kê.
Tách riêng ĐÔNG và MÁT. Bỏ qua: lưu TCNK, quá cảnh.

---

## Công Thức

```
Avg_Daily_Outbound = Outbound_14d / 14
Days_Cover         = Current_Inventory / max(Avg_Daily_Out, 0.01)
Pressure_Score     = (Inventory × Days_Cover) / (Avg_Daily_Out + 1)
```

- **Outbound** = `abs(Số lượng xuất chuyển)` — col 34 trong XNT (giá trị âm trong file)
- **Inventory** = `Tồn cuối kỳ` — col 38 từ file XNT mới nhất
- Kho ABA **không có xuất bán** (col 26 = 0), toàn bộ outbound qua xuất chuyển

### Ý nghĩa Pressure Score
- Tồn càng cao → score ↑
- Cover càng lâu → score ↑
- Xuất càng thấp → score ↑↑ (mẫu số nhỏ, tăng mạnh)

---

## Data Sources

| Data | Path | Ghi chú |
|------|------|---------|
| Tồn KFM (XNT) | `G:\My Drive\DOCS\DAILY\ton_kfm\XNT_ddmmyyyy.xlsx` | Sheet `BAO_CAO_XUAT_NHAP_TON`, 1 file/ngày |
| Master Data | `G:\My Drive\DOCS\DAILY\ton_aba\data\master_data\Master Data.xlsx` | barcode → ĐÔNG/MÁT |

### XNT Columns quan trọng

| Col | Header | Ý nghĩa |
|-----|--------|---------|
| 4 | Mã hàng | Barcode (join key) |
| 5 | Tên hàng | Tên sản phẩm |
| 7 | Chi nhánh | Filter: chỉ lấy `KHO ABA LƯU HÀNG` |
| 9 | Cate Level 2 | Fallback phân loại khi master không có |
| 34 | Số lượng xuất chuyển | **Outbound chính** (abs, giá trị âm) |
| 38 | Tồn cuối kỳ | **Current Inventory** |

### Phân loại ĐÔNG / MÁT

```
Priority 1: Master Data (barcode → Phân Loại)
Priority 2: Cate Level 2 fallback
  ĐÔNG: 2.FROZEN FOODS, 2.ICE CREAM
  MÁT:  2.CHILLED FOODS, 2.DAIRY, 2.BAKERY, 2.DELICA, 2.FRESH FOOD (all sub)
```

### Filter — Bỏ qua

| Chi nhánh | Lý do |
|-----------|-------|
| KHO ABA QUÁ CẢNH | Hàng transit |
| KHO ABA KHAI TRƯƠNG | Hàng sự kiện |
| KHO ABA XỬ LÝ CHÊNH LỆCH | Hàng lệch |
| KHO ABA ĐỔI TRẢ | Hàng trả |
| Cate 1 = `1.zHÀNG KHÔNG BÁN` | Hàng KM |
| Cate 1 = `1.CÔNG CỤ DỤNG CỤ` | Dụng cụ |

---

## Outbound 14 ngày — Cách ghép file

Mỗi file XNT chứa tổng cộng dồn (3-7 ngày), **không phải daily**.
Cần ghép 2-3 file không overlap để cover 14 ngày.

```
Ví dụ: target 01/05 → 14/05
  XNT_14052026: 10/05 → 14/05  (latest, lấy Tồn cuối kỳ)
  XNT_09052026: 03/05 → 09/05  (fill gap)
  XNT_02052026: 01/05 → 02/05  (partial, scale theo tỷ lệ ngày)
```

File partial → `outbound × (effective_days / file_days)` để normalize.

---

## Thresholds (data-driven, calibrate từ percentile)

| Metric | ĐÔNG | MÁT | Basis |
|--------|------|-----|-------|
| Transfer: Days Cover > | 60 | 25 | ~P75 |
| Transfer: Pressure > | 5,000 | 1,000 | ~P90 |
| Review: Days Cover > | 36 | 14 | ~P50 |
| Review: Pressure > | 2,000 | 400 | ~P75 |
| Dead stock: không xuất ≥ | 10d | 7d | ĐÔNG turnover chậm hơn |

### Action logic

```
1. Dead stock (không xuất ≥ N ngày, tồn > 0) → Transfer
2. Cover > transfer_cover HOẶC Pressure > transfer_pressure → Transfer
3. Cover > review_cover HOẶC Pressure > review_pressure → Review
4. Còn lại → Keep
```

### Pressure Score Labels

| Range | Label |
|-------|-------|
| > 50,000 | 🔴 Cực cao |
| 10,000 – 50,000 | 🔴 Cao |
| 3,000 – 10,000 | 🟡 Trung bình cao |
| 500 – 3,000 | 🟡 Trung bình |
| < 500 | 🟢 Thấp |

---

## Output

- Excel: `output/artifacts/inventory/pressure_score_ddmmyyyy.xlsx`
- 4 sheets: Summary, ĐÔNG, MÁT, ⚠ Tồn Âm
- Sorted: Pressure Score DESC
- Tồn âm: highlight đỏ + alert

---

## CLI

```bash
python script/domains/inventory/generate_pressure.py                    # latest
python script/domains/inventory/generate_pressure.py --date dd/mm/yyyy  # specific date
```

---

## Khi lỗi

| Vấn đề | Giải pháp |
|---------|-----------|
| No XNT files found | Check `G:\My Drive\DOCS\DAILY\ton_kfm\` có file |
| Barcode không match category | Thêm vào FALLBACK_CAT hoặc Master Data |
| Coverage < 14 ngày | Script tự scale, nhưng data ít → kém chính xác |
| Threshold cần calibrate | Chỉnh THRESHOLDS dict trong `generate_pressure.py` |
