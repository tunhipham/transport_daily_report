---
description: Weekly report - aggregate daily data into weekly summary report
---

# Workflow: Weekly Report

## Mục đích
Tổng hợp data daily từ `history.json` thành báo cáo tuần (Mon-Sun), format y chang daily report.

## Chạy mỗi Chủ nhật

### 1. Chạy script tạo weekly report
// turbo
```
python -u script/generate_weekly_report.py
```
Mặc định tự detect tuần hoàn chỉnh gần nhất. Chỉ định tuần cụ thể:
```
python -u script/generate_weekly_report.py --week W12/2026
```

### 2. Review report
Report lưu tại: `output/BAO_CAO_TUAN_W{num}_{year}.png`

### 3. Gửi Telegram (nếu muốn)
// turbo
```
python -u script/generate_weekly_report.py --send
```

## Lịch Giao Hàng Theo Kho

| Kho | Lịch giao | Ghi chú |
|---|---|---|
| **THỊT CÁ** | DAILY (7/7) | Ngày nào cũng có trip |
| **KRC** | DAILY (7/7) | Ngày nào cũng có trip |
| **ĐÔNG MÁT** | 6/7 — **Không giao Thứ 2** | Thứ 2 không có trip |
| **KSL (DRY)** | 6/7 — **Không giao CN** | Ngoại lệ: CN có 1-3 chuyến khai trương (chủ yếu KSL-Tối) |

> Dùng bảng này để validate weekly data: tuần 7 ngày thì ĐÔNG MÁT có 6 ngày, KSL có 6 ngày (+CN khai trương).

