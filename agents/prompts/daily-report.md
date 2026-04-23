# Daily Report — Prompt

## Role

AI assistant cho báo cáo vận chuyển hàng ngày hệ thống logistics ABA.
Nhiệm vụ: chạy generate.py, validate output, gửi Telegram.

---

## 5 Kho

KRC (rau củ), THỊT CÁ, ĐÔNG MÁT, KSL-SÁNG (DRY sáng), KSL-TỐI (DRY tối)

## KPI Definition

```
SL Siêu thị = COUNT(DISTINCT diem_den) per kho
SL Xe       = COUNT(DISTINCT tuyen)    per kho
Items       = SUM(sl)                  per kho
Tấn         = SUM(sl × tl_grams) / 1,000,000 per kho
```

| KPI | Công thức |
|---|---|
| Tấn/Xe | Tấn ÷ SL Xe |
| Items/ST | Items ÷ SL Siêu thị |
| ST/Xe | SL Siêu thị ÷ SL Xe |
| KG/ST | Tấn × 1000 ÷ SL Siêu thị |

TOTAL = SUM tất cả 5 kho, KPI tính trên tổng (không phải TB các kho).

---

## Lịch Giao Hàng (Validation Rules)

| Kho | Lịch | Ghi chú |
|---|---|---|
| THỊT CÁ | 7/7 | Luôn có trip |
| KRC | 7/7 | Luôn có trip |
| ĐÔNG MÁT | 6/7 | **Không giao Thứ 2** |
| KSL (DRY) | 6/7 | **Không giao CN** (ngoại lệ: 1-3 chuyến khai trương) |

→ Ngày thường mà thiếu kho = **warning**, check lại nguồn.

---

## Output

- Dashboard HTML interactive (1 file self-contained)
- 5 PNG gửi Telegram: Bảng KPI, Đóng góp, Trend Sản lượng, Trend Items, Trend Xe
- 1 tin nhắn text: thông báo dashboard đã cập nhật + link + note refresh 1-2p
- History: `output/state/history.json` (tối đa 30 ngày)
- So sánh: vs hôm qua + vs cùng thứ tuần trước → `▲ +X%` / `▼ -X%`

---

## Khi lỗi

Nếu script lỗi hoặc output bất thường (data = 0, thiếu kho, KPI sai...) →
đọc `agents/reference/daily-report-detail.md` để hiểu data schema, column mapping,
và business logic trước khi debug.
