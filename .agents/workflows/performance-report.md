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

1. Fetch latest monthly plan:
```powershell
python -u script/domains/performance/fetch_monthly.py --month 4 --year 2026
```

2. Generate report:
```powershell
python -u script/domains/performance/generate.py --months 3,4 --year 2026
```

3. Deploy:
```powershell
python -u script/dashboard/deploy.py --domain performance
```

## Validation

- Check all KPIs present: SLA, Plan, Completion
- Review ⚠ warnings in output
- Verify no missing kho
- Check weekly tables: color gradient, SLA rows, sticky columns

## Troubleshooting

Script lỗi? → Đọc `agents/reference/performance-report-detail.md` trước khi sửa code.
