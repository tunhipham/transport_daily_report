---
description: Daily report automation - download data and update DAILY REPORT.xlsx
---

# Daily Report Workflow

Run this workflow each morning to update the daily report.

## Prerequisites (User does manually BEFORE running this workflow)
- Download KFM file (`THỜI GIAN GIAO HÀNG KFM.xlsx`) and save to `data/` folder (overwrite old file)
- Download transfer file (`transfer_*.xlsx`) and save to `data/` folder (overwrite old file)

## Steps

### 1. Download KRC data from Google Sheets
// turbo
```
python script/download_data.py
```

### 2. Download KH MEAT/ĐÔNG/MÁT files from Google Drive
Use the browser tool to:
- Navigate to https://drive.google.com/drive/folders/1th0myHfLtdz3uTBFf2EuQ6G1GywjufYE
- Get file IDs for today's files from KH MEAT, KH HÀNG ĐÔNG, KH HÀNG MÁT
- Then run:
// turbo
```
python script/download_data.py --kh MEAT_FILE_ID DONG_FILE_ID MAT_FILE_ID
```

### 3. Run the data update script
// turbo
```
python script/update_daily_report.py
```

### 4. Verify the results
Open `output/DAILY REPORT.xlsx` and check:
- Sheet `DATA STHI + XE` has new rows for today's date
- All warehouses have data: KRC, KSL-Sáng, KSL-Tối, THỊT CÁ, ĐÔNG MÁT
