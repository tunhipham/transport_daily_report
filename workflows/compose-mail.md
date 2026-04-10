---
description: Compose delivery schedule emails on Haraworks internal mail
---

# Compose Mail Workflow

## Rules (QUAN TRỌNG)

1. **D+1**: Mail mỗi kho là lịch giao hàng cho ngày D+1 (ngày mai)
2. **KSL (DRY) chia 2 mail**: 
   - Mail Sáng: giờ từ 6h → 15h (hour 6-14)
   - Mail Tối: giờ từ 15h → 3h sáng hôm sau (hour 15-23, 0-2)
   - Ngày D sẽ mail: lịch tối ngày D + lịch sáng ngày D+1
3. **Mỗi week = 1 thread**: W14, W15... mỗi tuần dùng 1 thread email, ngày mới reply vào thread đó
4. **Store ID sort A→Z**: Cột "Điểm đến" luôn sort alphabetical
5. **Chỉ soạn DRAFT, KHÔNG BẤM GỬI** cho tới khi user xác nhận
6. **Không có lịch fix**: User sẽ nói kho nào có data rồi để soạn
7. **Kiểm kê (DRY only)**: Siêu thị có lịch kiểm kê tổng ngày X → không nhận hàng ngày D (=X) và D-1 (=X-1). Script tự động fetch lịch kiểm kê và highlight ĐỎ các dòng trùng trong table email để user check.
   - Source: [Lịch kiểm kê 2026](https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/edit?gid=220196646#gid=220196646)
   - Sheet "Lịch Kiểm kê 2026", Col D = ID Mart, Col H = Ngày kiểm kê tổng 2026
8. **Time format**: Giờ luôn HH:MM (leading zero), ví dụ 0:17 → 00:17

## Thông tin mail

| Kho | Subject | To | Body greeting |
|-----|---------|-----|---------------|
| KRC | KẾ HOẠCH GIAO HÀNG KRC W{week} | Nhiều stores | Dear team ST, SCM gửi thông tin kế hoạch giao hàng KHO RCQ ngày {date}. |
| DRY Sáng | KẾ HOẠCH GIAO HÀNG KHO DRY W{week} | Đoàn Thanh Long | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng DC Dry Sáng {date}. |
| DRY Tối | (reply trong thread DRY) | (reply all) | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng DC Dry Tối {date}. |
| ĐÔNG MÁT | KẾ HOẠCH GIAO HÀNG KHO ĐÔNG MÁT W{week} | (stores) | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng Đông Mát ngày {date}. |
| THỊT CÁ | KẾ HOẠCH GIAO HÀNG KHO ABA THỊT CÁ W{week} | (stores) | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng Thịt Cá ngày {date}. |

### CC List (tất cả các kho)
Operations, Operations Training & Development, Operations Excellence, Sales, Delivery, Delivery 1, Regional Sales 1, HCM 001, Đối Tác Seedlog, DC Seedlog (cho DRY)

### Table columns
- **KRC, DRY, THỊT CÁ**: Ngày | Điểm đến | Giờ đến dự kiến (+-30')
- **ĐÔNG MÁT**: Ngày | Điểm đến | Giờ đến dự kiến (+-30') | Loại hàng

## Steps

### 0. LUÔN re-fetch data mới nhất trước khi compose (BẮT BUỘC)
// turbo
```
python -u script/fetch_weekly_plan.py --week W{week} --start DD/MM/YYYY
```

⚠️ **QUAN TRỌNG**: Google Sheet nguồn được planner cập nhật liên tục trong ngày.
Data fetch từ sáng có thể thiếu/sai cho ngày D+1 (giờ giao còn #N/A).
**Phải re-fetch ngay trước khi compose** để đảm bảo data đầy đủ.

Sau khi fetch xong, kiểm tra output xem có bao nhiêu rows cho ngày cần compose.
Nếu thấy nhiều #N/A → data chưa sẵn sàng, báo user chờ.

### 1. Generate HTML email body
// turbo
```
python -u script/compose_mail.py --kho KRC --date DD/MM/YYYY
```
Hoặc cho DRY:
```
python -u script/compose_mail.py --kho DRY --session sang --date DD/MM/YYYY
python -u script/compose_mail.py --kho DRY --session toi --date DD/MM/YYYY
```

Script sẽ:
- Load data từ `output/weekly_plan_W{week}.json`
- Filter theo ngày + session (nếu DRY)
- Rows có giờ `#N/A` hoặc unparseable → mặc định vào ca sáng
- Sort store ID A→Z
- Check lịch kiểm kê → flag stores trùng D hoặc D-1
- Generate HTML hoàn chỉnh (text tiếng Việt có dấu + bảng)
- Output ra `output/_mail_body.html` và `output/_mail_inject.js`
- Copy HTML vào clipboard

**Kiểm tra output**: Đếm số rows có đúng với expected không. Nếu sai → re-fetch data (Step 0).

### 2. Open Haraworks
Navigate to: https://ic.haraworks.vn/internal_mail/inbox
Login: SC012433

### 3. Inject HTML into CKEditor

**Cách 1 — Clipboard paste (RECOMMENDED):**
1. Chạy `powershell -ExecutionPolicy Bypass -File output/_clip_html.ps1` để copy HTML format vào clipboard
2. Browser subagent: click vào CKEditor → Ctrl+A → Ctrl+V
3. Ưu điểm: nhanh, ổn định, không bị lỗi javascript: URL

**Cách 2 — JS Console (manual fallback):**
Mở browser console (F12) trên trang compose/reply, paste nội dung file `output/_mail_inject.js` → Enter.

**KHÔNG dùng javascript: URL** — Playwright block, gây ERR_ABORTED.
**KHÔNG gõ từng ô** — Vietnamese diacritics gây lỗi Unknown key.

### 4. Review draft
- Kiểm tra greeting text đúng kho + ngày + session
- Đếm số rows trong table đúng expected
- Kiểm tra stores có flag kiểm kê (tô đỏ) → báo user
- Screenshot cho user xác nhận
- **KHÔNG bấm Gửi** cho tới khi user confirm

## Troubleshooting

### Data thiếu rows / có #N/A
- **Nguyên nhân**: Google Sheet nguồn chưa cập nhật xong giờ giao
- **Fix**: Re-fetch data (`fetch_weekly_plan.py`) rồi chạy lại compose_mail
- Script đã có fallback: rows #N/A → mặc định vào ca sáng. Nhưng giờ giao sẽ hiển thị sai → nên re-fetch cho đúng

### CKEditor inject bị lỗi
- **Ưu tiên dùng clipboard paste** (Cách 1): `_clip_html.ps1` → Ctrl+A → Ctrl+V
- Nếu paste bị mất format → dùng JS console (Cách 2)
- **Không** dùng `javascript:` URL qua browser subagent's `open_browser_url`

### Browser subagent mở nhiều tab
- Luôn close tab thừa trước khi làm việc
- Chỉ dùng 1 page duy nhất cho Haraworks

## Notes

- Haraworks login: SC012433
- Data source: `output/weekly_plan_W{week}.json` (generated by `fetch_weekly_plan.py`)
- CKEditor selector: `[role="textbox"][contenteditable="true"]` hoặc `.ck-editor__editable`
- Clipboard HTML: `output/_clip_html.ps1` (PowerShell, copies as CF_HTML format)
- Vietnamese diacritics: dùng clipboard paste hoặc JS injection, KHÔNG dùng browser_press_key
