---
description: Tạo và paste dữ liệu "Dự kiến giao" vào Google Sheet Dashboard báo cáo ABA
---

# Workflow: Dự kiến giao

## Mục đích
Fetch dữ liệu lịch giao hàng từ KRC, KFM (KSL), KH MEAT/ĐÔNG/MÁT và paste vào sheet **"Dự kiến giao"** trong Google Sheet [Dashboard báo cáo ABA](https://docs.google.com/spreadsheets/d/1KhRCEIgKuWYKgkAYP3Vwenet76LUADyPR0nUkqOfhLo/edit?gid=0#gid=0).

## Cấu trúc sheet "Dự kiến giao"
| Cột | Nội dung | Ghi chú |
|-----|----------|---------|
| A - Key | `=B&C&E` | Formula tự động, KHÔNG paste |
| B - Ngày giao hàng | `3/24/2026` | Format M/D/YYYY |
| C - Điểm đến | `A126` | Store code |
| D - Giờ đến dự kiến (+-30') | `3:05` | Giờ giao thực tế |
| E - Kho | `KRC`, `KSL`, `THỊT CÁ`, `ĐÔNG MÁT` | |
| F - Loại hàng | `ĐÔNG`, `MÁT`, hoặc trống | |

## Nguồn dữ liệu & cột giờ giao

| Nguồn | Kho report | Cột giờ giao | Cột loại hàng |
|-------|-----------|-------------|---------------|
| KRC Google Sheet | KRC | Col H (7) | - |
| KFM Google Sheet (tab DRY) | KSL | Col H (7) | - |
| KH MEAT (Google Drive) | THỊT CÁ | Col W (22) "Du kien giao" | - |
| KH HÀNG ĐÔNG (Google Drive) | ĐÔNG MÁT | Col R (17) "TG DỰ KIẾN" | Col S (18) "LOẠI HÀNG" |
| KH HÀNG MÁT (Google Drive) | ĐÔNG MÁT | Col T (19) "Du kien giao" | Col U (20) "LOẠI HÀNG" |

> **⚠️ Lưu ý quan trọng:** Mỗi file KH có cấu trúc cột KHÁC NHAU. Đặc biệt cột giờ giao:
> - KH MEAT: col 22 (W)
> - KH ĐÔNG: col 17 (R) 
> - KH MÁT: col 19 (T)
> 
> KHÔNG dùng col 5 (F) "Thoi gian" — đó là khung giờ chung (VD: "09:00 - 16:00"), không phải giờ giao cụ thể.

## Các bước thực hiện

### 1. Chạy script tạo TSV
// turbo
```
python script/du_kien_giao.py
```
Mặc định lấy ngày hôm nay. Chạy cho ngày khác:
```
python script/du_kien_giao.py --date 23/03/2026
```

Output: `output/du_kien_giao_DDMMYYYY.tsv`

### 2. Copy TSV vào clipboard
// turbo
```
cmd /c "chcp 65001 >nul & type output\du_kien_giao_DDMMYYYY.tsv | clip"
```
(Thay `DDMMYYYY` bằng ngày tương ứng)

### 3. Mở Google Sheet và paste
- Mở sheet: https://docs.google.com/spreadsheets/d/1KhRCEIgKuWYKgkAYP3Vwenet76LUADyPR0nUkqOfhLo/edit?gid=0#gid=0
- Chọn tab **"Dự kiến giao"**
- Tìm row cuối cùng có data (dùng Ctrl+End hoặc Name Box)

**Nếu thêm data cho ngày MỚI NHẤT (append cuối):**
- Navigate đến cell B{last_row+1}
- Ctrl+V để paste

**Nếu chèn data cho ngày GIỮA (VD: ngày 23 giữa ngày 22 và 24):**
- Chọn N rows cần chèn (Name Box: `{start}:{end}`)
- Insert > Rows > "Chèn N hàng phía trên"
- Navigate đến cell B{start}
- Ctrl+V để paste

### 4. Verify
- Kiểm tra giờ giao THỊT CÁ có KHÁC NHAU (không phải toàn 3:00)
- Kiểm tra giờ giao ĐÔNG MÁT có KHÁC NHAU (không phải toàn 9:00)
- Kiểm tra cột Loại hàng (F) có ĐÔNG/MÁT cho entries tương ứng
- Kiểm tra ngày đúng format M/D/YYYY
