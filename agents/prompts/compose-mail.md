# Compose Mail — Prompt

Soạn email lịch giao hàng cho từng kho, inject vào Haraworks internal mail.

---

## Rules

> [!CAUTION]
> **--date luôn = D+1** (ngày mai) cho KRC / ĐÔNG MÁT / THỊT CÁ / DRY Sáng.
> Ngoại lệ duy nhất: DRY Tối dùng D (cùng ngày).
> ⛔ KHÔNG BAO GIỜ tự đổi sang ngày khác — đây là rule cứng, không có ngoại lệ.

1. **D+1**: Mail = lịch giao hàng ngày D+1 (ngày mai)
2. **DRY chia 2 mail**:
   - Sáng: hour 6-14 | Tối: hour 15-23, 0-2
   - Ngày D mail: lịch tối D + lịch sáng D+1
3. **Thread per week**: W14, W15... mỗi tuần 1 thread, ngày mới reply vào thread đó
4. **Store sort A→Z**
5. **Time format**: HH:MM (leading zero)
6. **Draft only**: KHÔNG bấm Gửi cho tới khi user xác nhận
7. **Kiểm kê (DRY only)**: Store có kiểm kê ngày X → không nhận hàng ngày X và X-1. Script tự fetch + highlight ĐỎ.
   - Source: [Lịch kiểm kê 2026](https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/edit?gid=220196646#gid=220196646)

⚠ ALWAYS re-fetch inspection data (no cache).

---

## Kho-specific Logic

- **THỊT CÁ**: Fetch 1 lần = final → compose + inject luôn, không cần chờ cutoff.
- **ĐÔNG MÁT**: Cần đủ 2 file "KH HÀNG ĐÔNG" + "KH HÀNG MÁT". Thiếu 1 → chờ.
- **DRY / KRC**: Data thay đổi liên tục → re-fetch + re-compose gần cutoff.

---

## Cutoff Schedule

| Kho | Check Window | Cutoff | Mail cho | Ngày nghỉ |
|-----|-------------|--------|----------|-----------|
| DRY Tối | 12:00-14:00 | 14:00 | Tối cùng ngày D | CN |
| DRY Sáng | 15:00-16:30 | 16:30 | Sáng D+1 | CN |
| ĐÔNG MÁT | 15:00-19:00 | 19:00 | D+1 | Thứ 2 |
| KRC | 17:00-19:00 | 19:00 | D+1 | — |
| THỊT CÁ | 17:00-19:00 | 19:00 | D+1 | — |

---

## Email Template

| Kho | Subject | Greeting |
|-----|---------|----------|
| KRC | KẾ HOẠCH GIAO HÀNG KRC W{week} | Dear team ST, SCM gửi thông tin kế hoạch giao hàng KHO RCQ ngày {date}. |
| DRY Sáng | KẾ HOẠCH GIAO HÀNG KHO DRY W{week} | Dear team Siêu Thị, SCM gửi ... DC Dry Sáng {date}. |
| DRY Tối | (reply thread DRY) | Dear team Siêu Thị, SCM gửi ... DC Dry Tối {date}. |
| ĐÔNG MÁT | KẾ HOẠCH GIAO HÀNG KHO ĐÔNG MÁT W{week} | Dear team Siêu Thị, SCM gửi ... Đông Mát ngày {date}. |
| THỊT CÁ | KẾ HOẠCH GIAO HÀNG KHO ABA THỊT CÁ W{week} | Dear team Siêu Thị, SCM gửi ... Thịt Cá ngày {date}. |

### CC (tất cả kho)
Operations, Operations Training & Development, Operations Excellence, Sales, Delivery, Delivery 1, Regional Sales 1, HCM 001, Đối Tác Seedlog, DC Seedlog (cho DRY)

### Table columns
- **KRC, DRY, THỊT CÁ**: Ngày | Điểm đến | Giờ đến dự kiến (+-30')
- **ĐÔNG MÁT**: Ngày | Điểm đến | Giờ giao dự kiến (+- 1 tiếng) | Loại hàng
  - ⚠ Giờ hiển thị = `gio_den + 90 phút` (script tự cộng)

---

## Khi lỗi

Script lỗi hoặc inject bất thường →
đọc `agents/reference/compose-mail-detail.md` để hiểu injection method, Edge setup,
compose order, và data change detection trước khi debug.
