# Inventory (Đối Soát Tồn Kho) — Prompt

Tạo báo cáo đối soát tồn kho KFM vs ABA: daily + weekly.

---

## KPI

### Tỷ lệ chính xác (Accuracy)
```
accuracy = max(0, 1 - discrepancy/total) × 100

Item accuracy = (1 - item_lech / item_KFM_total) × 100
SKU accuracy  = (1 - sku_lech / sku_total) × 100
KG accuracy   = (1 - kg_lech / kg_KFM_total) × 100
```

- **Lệch** = abs(ton_KFM - ton_ABA) cho từng SKU — giá trị tuyệt đối
- **Làm tròn**: TRUNCATE xuống 2 decimal (math.floor), KHÔNG round lên
- **Max**: 100%, không vượt quá

### 3 Nhóm phân loại
- **ĐÔNG**: Chi nhánh = KHO LƯU HÀNG/QUÁ CẢNH, Phân Loại = ĐÔNG
- **MÁT**: Chi nhánh = KHO LƯU HÀNG/QUÁ CẢNH, Phân Loại = MÁT
- **TCNK**: Chi nhánh chứa "TCNK"

---

## Data Sources

| Data | File | Ghi chú |
|------|------|---------|
| Đối soát | `data/doi_soat/Đối soát tồn *.xlsx` | 1 file/ngày, sheet "Đối soát tồn" |
| Master | `data/master/*.xlsx` | barcode → nhóm (Đông/Mát/TCNK) |
| Weight | `data/weight/*.xlsx` | barcode → KG/item |
| Paths | `script/lib/sources.py` | DOI_SOAT_DIR, MASTER_DATA_FILE, WEIGHT_DATA_FILE |

---

## Daily Output

- HTML report: `output/artifacts/inventory/report_doi_soat_dd.mm.yyyy.html`
- 8 PNG screenshots (Selenium headless):
  1. Thống kê + Summary cards
  2-4. Trend Item/SKU/KG
  5-6. Pie Item/KG
  7. Bảng tổng hợp tuần
  8. Chi tiết mã lệch
- So sánh: vs hôm qua + vs LFL (cùng ngày tuần trước)

## Weekly Output

- HTML report: `output/artifacts/inventory/report_doi_soat_weekly_W{N}_{YYYY}.html`
- Sections: Weekly summary table, thống kê theo nhóm, 3 trend + 2 pie + 2 stacked charts, nhận xét tự động, chi tiết mã lệch cả tuần
- Recurring: Mã lệch xuất hiện ≥3 ngày → badge 🔴

## Telegram

- Config: `config/telegram.json` → `inventory` domain
- Auto-cleanup: xóa message cũ cùng ngày trước khi gửi
- State: `output/state/inventory/sent_messages.json`
- Daily: chờ user confirm trước khi gửi
- Weekly: chờ user confirm

---

## Khi lỗi

Script lỗi → check file đối soát format, master data coverage, weight data.
Barcode không match → thêm CATEGORY_OVERRIDES hoặc WEIGHT_OVERRIDES trong generate.py.
