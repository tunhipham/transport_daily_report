---
description: Daily report automation - download data and generate summary report
---

# Workflow: Daily Report (Báo cáo xuất kho hàng ngày)

## Mục đích
Tạo báo cáo sản lượng và lưu lượng xe xuất kho hàng ngày, review và gửi lên Telegram group.

## Các bước thực hiện

### 1. Chạy generate report (tự fetch data online, tạo ảnh + HTML báo cáo)
// turbo
```
python script/generate_report.py
```
Chạy cho ngày khác:
```
python script/generate_report.py --date DD/MM/YYYY
```

Output:
- `output/BAO_CAO_DDMMYYYY_1_BANG.png` — bảng KPI chi tiết
- `output/BAO_CAO_DDMMYYYY_2_DONGGOP.png` — % đóng góp SLG (ngày + tuần)
- `output/BAO_CAO_DDMMYYYY_3_SANLUONG.png` — trend sản lượng (ngày + tuần)
- `output/BAO_CAO_DDMMYYYY_4_ITEMS.png` — trend items (ngày + tuần)
- `output/BAO_CAO_DDMMYYYY_5_XE.png` — trend xe (ngày + tuần)
- `output/BAO_CAO_DDMMYYYY.html` — bản HTML tổng hợp xem bằng trình duyệt

### 2. Review báo cáo
- Mở file ảnh hoặc HTML để kiểm tra
- Kiểm tra các chỉ số: Tổng tấn, Tổng xe, Tổng siêu thị, Tổng items
- Xác nhận trend chart (THEO NGÀY + THEO TUẦN) hợp lý

### 3. Gửi lên Telegram (chỉ khi user xác nhận)
```
python script/generate_report.py --date DD/MM/YYYY --send
```
Sẽ gửi lên Telegram group:
- 5 file PNG (5 phần báo cáo tách riêng)
- File HTML (mở bằng trình duyệt để xem chi tiết)

### 4. Lưu lên Google Drive
```
robocopy "c:\Users\admin\Downloads\transport_daily_report" "g:\My Drive\DOCS\transport_daily_report" /E /XD __pycache__ .git /XF *.pyc
```

## Ghi chú
- Script tự động fetch tất cả data từ Google Sheets/Drive (không cần download trước)
- Nếu ảnh quá lớn cho Telegram sendPhoto, tự động fallback sang sendDocument
- Báo cáo gồm 2 phần: bảng KPI daily (trên) + biểu đồ THEO NGÀY / THEO TUẦN (dưới)
- History được lưu tại `output/history.json` (giữ 30 ngày gần nhất)
