---
description: Chạy báo cáo đối soát tồn kho KFM vs ABA (hàng ngày + hàng tuần)
---

# Inventory Report Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/inventory.md` trước khi chạy.

## Daily Report

### 1. Tạo report (KHÔNG gửi Telegram)
```powershell
python -u script/domains/inventory/generate.py --no-telegram
```

### 2. Chờ user review → confirm → gửi
```powershell
python -u script/domains/inventory/generate.py
```

### Chạy cho ngày cụ thể
```powershell
python -u script/domains/inventory/generate.py --date dd/mm/yyyy --no-telegram
```

## Weekly Report (1 lần/tuần — T2 đầu tuần)

### Tạo report tuần trước (auto-detect)
```powershell
python -u script/domains/inventory/generate_weekly.py --no-telegram
```

### Chạy cho tuần cụ thể
```powershell
python -u script/domains/inventory/generate_weekly.py --week W15 --year 2026 --no-telegram
```

## Deploy dashboard

```powershell
python -u script/dashboard/deploy.py --domain inventory
```

## Validation

- Check 3 nhóm Đông/Mát/TCNK đều có data
- Tỷ lệ chính xác hợp lý (thường >99%)
- Trend chart hiển thị đúng ngày
- Weekly: nhận xét tự động + bảng chi tiết mã lệch

## Chuẩn bị data

- File đối soát ngày mới: `data/doi_soat/Đối soát tồn *.xlsx`
- Master data: `data/master/` (phân loại Đông/Mát/TCNK)
- Weight data: `data/weight/` (quy đổi KG)

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| No reconciliation files found | Check `data/doi_soat/` có file cho ngày cần |
| Barcode không match category | Thêm vào CATEGORY_OVERRIDES trong generate.py |
| Weight missing | Thêm vào WEIGHT_OVERRIDES trong generate.py |
| Telegram không gửi | Check `config/telegram.json` → `inventory` domain |
| Weekly thiếu ngày | Cần có đủ file daily trong tuần |
