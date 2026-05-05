---
description: Generate or modify the monthly performance report (on-time, route, completion)
---

# Performance Report Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/performance-report.md` trước khi chạy.

## Backup (trước khi sửa code)

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"
Copy-Item "script\domains\performance\generate.py" "backups\generate_performance_report_$ts.py"
```

## Run

1. Fetch latest monthly plan (chạy cho **mỗi tháng** cần data):
```powershell
python -u script/domains/performance/fetch_monthly.py --month 4 --year 2026
```
```powershell
python -u script/domains/performance/fetch_monthly.py --month 5 --year 2026
```

2. Generate report + SLA Excel:
```powershell
python -u script/domains/performance/generate.py --months 3,4,5 --year 2026 --sla-weeks 14,15,16,17,18
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

# Standalone (chạy riêng nếu cần — sẽ load data lại)
python -u script/domains/performance/export_sla_weekly.py --months 3,4,5 --weeks 14,15,16,17,18
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

Script lỗi? → Đọc `agents/reference/performance-report-detail.md` trước khi sửa code.
