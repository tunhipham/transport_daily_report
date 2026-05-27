---
description: Generate or modify the monthly performance report (on-time, route, completion)
---

# Performance Report Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/performance-report.md` trước khi chạy.

## Mode 1: Realtime (Auto — mỗi 30 phút)

Dashboard tự động cập nhật qua Task Scheduler `RealtimePerformance`.

```powershell
# Chạy thủ công 1 lần
tools\run-realtime-performance.bat

# Check sync đang chạy không
tools\check-realtime-status.bat
```

Luồng realtime:
1. `push_compose_plan.py` — extract lịch dự kiến từ auto_compose_state.json
2. `fetch_db_realtime.py` — trip data từ ClickHouse (~5 giây, kèm data thùng/rổ cho tracking)
3. `fetch_plan_incremental.py` — plan hôm nay từ Google Sheet (~30 giây)
4. `generate.py --realtime` — tính KPI + xuất HTML/Excel/JSON
5. `deploy.py --domain performance` — push GitHub Pages

### Task Scheduler

| Task | Schedule | Description |
|---|---|---|
| `RealtimePerformance` | Mỗi 30 phút | Fetch DB + deploy dashboard |
| `TripReminder` | T2 + T3 08:00 | Telegram: trips chưa hoàn thành |
| `TripCutoff` | T3 09:00 | Xuất Excel final + gửi Telegram |

```powershell
# Kiểm tra / bật / tắt
schtasks /query /tn "RealtimePerformance" /v /fo LIST
schtasks /change /tn "RealtimePerformance" /disable
schtasks /change /tn "RealtimePerformance" /enable
```

### Monday Telegram (Dzí trip)

```powershell
python script\telegram\trip_reminder.py --dry-run    # Preview
python script\telegram\trip_reminder.py               # Send
```

### Tuesday Cutoff (9h — xuất Excel)

```powershell
tools\run-trip-cutoff.bat                              # Chạy manual
python script\telegram\trip_cutoff_export.py --dry-run # Preview
```

### Dashboard Tracking Realtime

Tính năng tracking trên Dashboard được nuôi bằng:
1. **Planned Times**: Lấy từ mail Compose (D-1) sang `auto_compose_state.json`. `push_compose_plan.py` extract ra `tracking_plan.json`.
2. **Thực tế + Container**: `fetch_db_realtime.py` query `tli_transfer_qty` và `tli_received_qty` từ ClickHouse, phân rã loại container (Rổ/Tote vs Thùng/Kiện) bằng `barrel_basket_name`.
3. **Hiển thị**: 6 tabs kho, click tooltip để xem chi tiết thùng/rổ. Thịt cá được fix cứng ẩn lượng giao nhận.

---

## Mode 2: Manual (Báo cáo tháng — full data)

Backup trước khi sửa code:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"
Copy-Item "script\domains\performance\generate.py" "backups\generate_performance_report_$ts.py"
```

### Run

1. Fetch latest monthly plan (chạy cho **mỗi tháng** cần data):
```powershell
python -u script/domains/performance/fetch_monthly.py --month 4 --year 2026
python -u script/domains/performance/fetch_monthly.py --month 5 --year 2026
```

2. Generate report + SLA Excel:
```powershell
python -u script/domains/performance/generate.py --months 3,4,5 --year 2026 --sla-weeks auto
```

3. Deploy:
```powershell
python -u script/dashboard/deploy.py --domain performance
```

## SLA Export Options

`--sla-weeks` tích hợp trong `generate.py` — **dùng lại metrics đã tính, không load data lần 2**.

```bash
# Chỉ định weeks cụ thể (recommended)
python -u script/domains/performance/generate.py --months 3,4,5 --sla-weeks 14,15,16,17,18

# Auto-detect weeks từ months (sẽ ra nhiều tuần)
python -u script/domains/performance/generate.py --months 3,4,5 --sla-weeks auto
```

Output (2 files in `output/artifacts/performance/`):
- `SLA_ONTIME_W{...}.xlsx` — all kho
- `SLA_ONTIME_DM_TC_W{...}.xlsx` — ĐÔNG MÁT + THỊT CÁ

## Validation

- Check all KPIs present: SLA, Plan, Completion
- Review ⚠ warnings in output
- Verify no missing kho
- Check weekly tables: color gradient, SLA rows, sticky columns

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Script lỗi | Đọc `agents/reference/performance-report-detail.md` |
| Realtime sync không chạy | `check-realtime-status.bat` → kiểm tra Task Scheduler |
| Plan hôm nay thiếu | `fetch_plan_incremental.py` chạy auto, check file KH local |
| THỊT CÁ data cũ | Re-run `fetch_monthly.py` khi anh update file BÁO CÁO |
| Trip Telegram sai | `trip_reminder.py --dry-run` → check ClickHouse connection |
