# Performance Report — Prompt

Prioritize correctness of KPI over completeness of data explanation.

## Role

Tạo báo cáo hiệu suất vận chuyển hàng tháng: on-time SLA, route compliance, trip completion.

---

## 4 KPI

1. **On-time SLA** — Giao trong khung giờ cam kết của kho
2. **On-time Per Destination** — Giao đúng giờ kế hoạch từng điểm
3. **Plan Compliance (Đúng Kế Hoạch)** — Thứ tự giao thực tế khớp kế hoạch per-destination
4. **Trip Completion** — Tỷ lệ hoàn thành chuyến

---

## SLA Windows

| Kho | Start | End |
|---|---|---|
| KRC | 03:00 | 05:30 |
| THỊT CÁ | 03:00 | 06:00 |
| ĐÔNG MÁT | 09:00 | 16:00 |
| KSL-Sáng | 12:00 | 14:00 |
| KSL-Tối | 22:00 | 00:30 (overnight) |

> **Giao SỚM = ĐÚNG GIỜ.** Chỉ tính TRỄ khi qua sla_end.

## On-time Plan

```
arrival_time ≤ planned_time → ĐÚNG ✅
arrival_time > planned_time → TRỄ ❌
thiếu planned_time          → KHÔNG TÍNH
```

> **KHÔNG tự fill planned_time từ ngày khác** (giờ KH biến động 94-585 phút giữa các ngày).



---

## Lịch Giao Hàng (Validation)

| Kho | Lịch | Ghi chú |
|---|---|---|
| THỊT CÁ | 7/7 | Luôn có trip |
| KRC | 7/7 | Luôn có trip |
| ĐÔNG MÁT | 6/7 | **Không giao Thứ 2** |
| KSL (DRY) | 6/7 | **Không giao CN** (ngoại lệ: CN khai trương) |

→ Ngày thường mà thiếu kho = **warning**.

---

## Output

- KPI summary (4 chỉ tiêu) + breakdown by kho
- Weekly tables với color gradient
- Warnings / anomalies
- Interactive: Kho filter buttons (Tổng / KRC / THỊT CÁ / ...) + Date range filter

---

## Khi lỗi

Script lỗi hoặc KPI bất thường →
đọc `agents/reference/performance-report-detail.md` để hiểu data schema, column mapping,
kho mapping, và known gotchas trước khi debug.
