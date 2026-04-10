# Walkthrough: Dự Kiến Giao — Delivery Schedule Data

## Mục đích
Fetch dữ liệu lịch giao hàng dự kiến từ nhiều nguồn online (KRC, KFM/KSL, KH MEAT/ĐÔNG/MÁT) và tạo file TSV để paste vào sheet **"Dự kiến giao"** trong [Dashboard báo cáo ABA](https://docs.google.com/spreadsheets/d/1KhRCEIgKuWYKgkAYP3Vwenet76LUADyPR0nUkqOfhLo/edit?gid=1496608719).

---

## Script chính
- **File:** `script/du_kien_giao.py`
- **Chạy:** `python script/du_kien_giao.py [--date DD/MM/YYYY]`
- **Output:** `output/du_kien_giao_DDMMYYYY.tsv`

---

## Cấu trúc output TSV (5 cột, paste vào B:F)

| Cột sheet | TSV col | Nội dung | Ví dụ |
|-----------|---------|----------|-------|
| B - Ngày giao hàng | 1 | Format M/D/YYYY | `3/26/2026` |
| C - Điểm đến | 2 | Store code | `A126` |
| D - Giờ đến dự kiến (±30') | 3 | Giờ giao H:MM | `3:05` |
| E - Kho | 4 | Tên kho | `KRC` |
| F - Loại hàng | 5 | ĐÔNG / MÁT / trống | `ĐÔNG` |

> **Lưu ý:** Cột A (Key) trong sheet có formula `=B&C&E`, KHÔNG paste vào cột A.

---

## 5 nguồn dữ liệu → 4 kho

| Nguồn | Kho output | Cột giờ giao | Cột loại hàng | Link |
|-------|-----------|-------------|---------------|------|
| KRC Google Sheet | **KRC** | Col H (7) | — | [Sheet](https://docs.google.com/spreadsheets/d/1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII) |
| KFM Google Sheet (tab DRY) | **KSL** | Col H (7) | — | [Sheet](https://docs.google.com/spreadsheets/d/1LkJFJhOQ8F2WEB3uCk7kA2Phvu8IskVi3YBfVr7pBx0) |
| KH MEAT (Google Drive) | **THỊT CÁ** | Col W (22) | — | [Folder](https://drive.google.com/drive/folders/1GIzH8nmCbLhWfpdmxFIn9cHTvQNbnwWr) |
| KH HÀNG ĐÔNG (Google Drive) | **ĐÔNG MÁT** | Col R (17) | Col S (18) | [Folder](https://drive.google.com/drive/folders/1pQ8coQeV-K0dcHlkvXcJ8KngmH22xp1Z) |
| KH HÀNG MÁT (Google Drive) | **ĐÔNG MÁT** | Col T (19) | Col U (20) | [Folder](https://drive.google.com/drive/folders/1c2zfgcXM8O9ezkOZYj0p4t_ihaJmb98f) |

> ⚠️ Script hiện output "KSL" cho KFM. Nếu cần tách KSL-Sáng / KSL-Tối, dựa vào giờ giao:
> - KSL-Sáng: 06:01 – 21:59
> - KSL-Tối: 22:00 – 06:00

> **Auto-detect cột (fix 30/03/2026):** File KH MÁT/ĐÔNG/MEAT đôi khi có cấu trúc cột KHÁC NHAU giữa các ngày (VD: 29/03 chỉ 18 cột, "Du kien giao" ở col 16 thay vì col 19).
> Script tự động scan header row tìm cột chứa "kien"+"giao" và "loại"/"loai" để detect đúng vị trí.

---

## Workflow chạy hàng ngày

### Bước 1: Chạy script
```bash
python script/du_kien_giao.py
# Hoặc cho ngày cụ thể:
python script/du_kien_giao.py --date 26/03/2026
```

### Bước 2: Copy vào clipboard
```bash
cmd /c "chcp 65001 >nul & type output\du_kien_giao_DDMMYYYY.tsv | clip"
```

### Bước 3: Paste vào Google Sheet
1. Mở [Dashboard báo cáo ABA](https://docs.google.com/spreadsheets/d/1KhRCEIgKuWYKgkAYP3Vwenet76LUADyPR0nUkqOfhLo/edit?gid=1496608719)
2. Chọn tab **"Dự kiến giao"**
3. Navigate đến row cuối cùng có data → chọn cell **B{last_row+1}**
4. **Ctrl+V** paste (KHÔNG xóa data cũ, add thêm bên dưới)

### Bước 4: Verify
- Giờ giao THỊT CÁ phải khác nhau (không toàn 3:00)
- Giờ giao ĐÔNG MÁT phải khác nhau (không toàn 9:00)
- Cột Loại hàng (F) có ĐÔNG/MÁT cho entries tương ứng
- Ngày đúng format M/D/YYYY

---

## Backfill nhiều ngày

Khi cần chạy nhiều ngày liên tiếp, chạy script cho từng ngày rồi gộp:

```powershell
# Chạy từng ngày
python script/du_kien_giao.py --date 26/03/2026
python script/du_kien_giao.py --date 27/03/2026
python script/du_kien_giao.py --date 28/03/2026

# Gộp file
cmd /c "type output\du_kien_giao_26032026.tsv output\du_kien_giao_27032026.tsv output\du_kien_giao_28032026.tsv > output\du_kien_giao_backfill.tsv"

# Copy rồi paste 1 lần
cmd /c "chcp 65001 >nul & type output\du_kien_giao_backfill.tsv | clip"
```

---

## Số liệu mẫu (26–30/03/2026)

| Ngày | Total | KRC | KSL | THỊT CÁ | ĐÔNG MÁT |
|------|-------|-----|-----|---------|----------|
| 26/03 | 621 | 154 | 80 | 154 | 233 |
| 27/03 | 626 | 154 | 86 | 154 | 232 |
| 28/03 | 647 | 154 | 110 | 154 | 229 |
| 29/03 | 538 | 154 | 2 | 154 | 228 |
| 30/03 | 406 | 154 | 98 | 154 | 0 (chưa có file) |
