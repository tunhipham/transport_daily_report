---
description: Daily report automation - download data and generate summary report
---

# Daily Report Workflow

// turbo-all

## Data Sources

| Source | Method | Location |
|--------|--------|----------|
| KRC | Online (Google Sheets) | Auto-fetched by script |
| KFM (KSL-Sáng/Tối) | Online (Google Sheets) | Auto-fetched by script |
| KH MEAT/ĐÔNG/MÁT | Online (Google Drive) | Auto-fetched by script |
| Master data | Online (Google Sheets) | Auto-fetched by script |
| Transfer | Online (Google Drive) | Also synced at `G:\My Drive\DOCS\DAILY\transfer` |
| Yêu cầu KSL | Online (Google Drive) | Also synced at `G:\My Drive\DOCS\DAILY\yeu_cau_chuyen_hang_thuong` |

## Prerequisites

- Python packages: `openpyxl`, `requests`, `playwright`
- Working directory: `c:\Users\admin\Downloads\transport_daily_report`
- Backup on Drive: `G:\My Drive\DOCS\transport_daily_report`

## Steps

1. Generate report (ALL data fetched online automatically):
```
python -u script/generate_report.py --send
```
Hoặc chỉ định ngày cụ thể:
```
python -u script/generate_report.py --date DD/MM/YYYY --send
```

2. Review output — report hiển thị bảng tổng hợp + charts:
   - Summary cards: Tổng Tấn, Tổng Xe, Tổng Siêu Thị, Tổng Items
   - Bảng chính: SL Siêu thị, SL Items, SL Xe, Sản lượng (Tấn)
   - KPI: Tấn/Xe, Items/Siêu Thị, Siêu Thị/Xe, KG/Siêu Thị
   - Donut chart: % Đóng góp sản lượng
   - Trend chart: Sản lượng theo kho (lịch sử 30 ngày)

3. Sync backup to Google Drive:
```
Copy-Item "c:\Users\admin\Downloads\transport_daily_report\script\generate_report.py" "G:\My Drive\DOCS\transport_daily_report\script\" -Force
Copy-Item "c:\Users\admin\Downloads\transport_daily_report\output\history.json" "G:\My Drive\DOCS\transport_daily_report\output\" -Force
```

## Notes

- Script lấy ALL data online, **không cần** download file thủ công
- KFM Google Sheets: https://docs.google.com/spreadsheets/d/1LkJFJhOQ8F2WEB3uCk7kA2Phvu8IskVi3YBfVr7pBx0/edit
- KRC Google Sheets: https://docs.google.com/spreadsheets/d/1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII/edit
- KH Google Drive: https://drive.google.com/drive/folders/1th0myHfLtdz3uTBFf2EuQ6G1GywjufYE
- Transfer Google Drive: https://drive.google.com/drive/folders/17Z_UPMDywWFplcg0fx3XSG87vSsG8LHb
- Yeu cau Google Drive: https://drive.google.com/drive/folders/1DpDon0QHhDRoX7_ZnEygwKlXsbcPGp-t
- Local sync paths: `G:\My Drive\DOCS\DAILY\transfer`, `G:\My Drive\DOCS\DAILY\yeu_cau_chuyen_hang_thuong`
- History: `output/history.json` (tối đa 30 ngày, dùng cho trend chart)
- Nếu Google Sheets bị rate limit, retry tự động hoặc chạy lại sau vài phút
