# Implementation Plan: Dự Kiến Giao — Delivery Schedule Automation

## Tổng quan

Script `du_kien_giao.py` tự động fetch dữ liệu lịch giao hàng từ 5 nguồn online, xử lý và xuất file TSV để paste vào sheet "Dự kiến giao" trong Dashboard báo cáo ABA.

---

## Kiến trúc

```
┌─────────────────────────┐
│   Google Sheets (KRC)   │──┐
│   Google Sheets (KFM)   │──┤
│   Google Drive (MEAT)   │──┼──→  du_kien_giao.py  ──→  TSV file  ──→  Google Sheet
│   Google Drive (ĐÔNG)   │──┤                                          "Dự kiến giao"
│   Google Drive (MÁT)    │──┘
└─────────────────────────┘
```

---

## Chi tiết script `du_kien_giao.py`

### Functions

| Function | Mô tả |
|----------|-------|
| `read_xlsx_from_url(url)` | Download & parse xlsx từ Google Sheet export URL |
| `_list_drive_folder(url)` | Scrape Google Drive folder HTML để lấy file IDs |
| `read_kh_from_drive(url, name, date)` | Download xlsx từ Drive (match filename chứa date) |
| `format_time(val)` | Convert time → `H:MM` (handle string, datetime, Excel float) |
| `fetch_delivery_data(date_str, date_for_file)` | Fetch tất cả 5 nguồn, trả về `(rows, warnings)` |
| `generate_tsv(rows, path)` | Ghi rows ra file TSV (5 cột, tab-separated) |

### Flow xử lý

1. **Input:** `--date DD/MM/YYYY` (default: hôm nay)
2. **Date formats:**
   - Sheet search: `DD/MM/YYYY` (khớp col A)
   - Drive file search: `DD.MM.YYYY` (khớp tên file)
   - Output: `M/D/YYYY` (format US cho Google Sheet)
3. **Fetch per source:**
   - KRC: Sheet "KRC", filter col A = date, lấy col G (điểm đến) + col H (giờ)
   - KFM: Sheet tab "DRY", filter col A = date, lấy col G + col H
   - KH MEAT: Drive folder → find file `*DD.MM.YYYY*`, col C (điểm đến) + col W (giờ)
   - KH ĐÔNG: col C + col R (giờ) + col S (loại hàng)
   - KH MÁT: col C + col T (giờ) + col U (loại hàng)
4. **Output:** TSV file tại `output/du_kien_giao_DDMMYYYY.tsv`

---

## Data mapping chi tiết

### Google Sheet sources

| Source | Sheet ID | Tab | Date col | Store col | Time col |
|--------|----------|-----|----------|-----------|----------|
| KRC | `1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII` | "KRC" | A (0) | G (6) | H (7) |
| KFM | `1LkJFJhOQ8F2WEB3uCk7kA2Phvu8IskVi3YBfVr7pBx0` | "DRY" | A (0) | G (6) | H (7) |

### Google Drive sources

| Source | Folder ID | Store col | Time col | Loại hàng col |
|--------|-----------|-----------|----------|---------------|
| KH MEAT | `1GIzH8nmCbLhWfpdmxFIn9cHTvQNbnwWr` | C (2) | W (22) | — |
| KH ĐÔNG | `1pQ8coQeV-K0dcHlkvXcJ8KngmH22xp1Z` | C (2) | R (17) | S (18) |
| KH MÁT | `1c2zfgcXM8O9ezkOZYj0p4t_ihaJmb98f` | C (2) | T (19) | U (20) |

---

## Output sheet "Dự kiến giao" (`gid=1496608719`)

| Cột | Header | Nguồn |
|-----|--------|-------|
| A | Key | Formula `=B&C&E` (tự động) |
| B | Ngày giao hàng | TSV col 1 |
| C | Điểm đến | TSV col 2 |
| D | Giờ đến dự kiến (±30') | TSV col 3 |
| E | Kho | TSV col 4 |
| F | Loại hàng | TSV col 5 |
| H-N | Pivot COUNTA | Formula tự động |

---

## Lưu ý & Known Issues

> [!WARNING]
> - **KH ĐÔNG/MÁT file timing:** File thường up muộn (ngày 30/03 có thể chưa có file trên Drive)
> - **KSL chưa tách:** Script hiện output "KSL", chưa tách thành "KSL-Sáng"/"KSL-Tối"
> - **Column A:** KHÔNG được paste vào — cột A có formula `=B&C&E`

> [!IMPORTANT]
> - Mỗi file KH có cấu trúc cột **KHÁC NHAU** — MEAT dùng col 22, ĐÔNG dùng col 17, MÁT dùng col 19
> - KHÔNG dùng col 5 (F) "Thoi gian" — đó là khung giờ chung (VD: "09:00 - 16:00")

---

## Verification

```bash
python script/du_kien_giao.py --date DD/MM/YYYY
```

Kiểm tra:
- ✅ Có đủ 4 kho (KRC, KSL, THỊT CÁ, ĐÔNG MÁT)
- ✅ Giờ giao THỊT CÁ khác nhau (không toàn 3:00)
- ✅ Giờ giao ĐÔNG MÁT khác nhau (không toàn 9:00)
- ✅ Loại hàng (F) có ĐÔNG/MÁT tương ứng
- ✅ Tổng rows khoảng 500–650/ngày
