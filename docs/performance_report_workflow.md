---
description: Generate or modify the monthly performance report (on-time, route, completion)
---

# Performance Report Workflow

## ⚠ MANDATORY: Read docs FIRST
Before making ANY changes to `generate_performance_report.py` or `fetch_monthly_plan.py`:
1. Read `G:\My Drive\DOCS\transport_daily_report\docs\performance_report_implementation_plan.md`
2. Understand the 4 KPIs: SLA, Plan, Route, Completion
3. Understand the data model and kho mapping
4. Check Known Gotchas section

## ⚠ MANDATORY: Backup BEFORE editing
```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"
Copy-Item "script\generate_performance_report.py" "G:\My Drive\DOCS\transport_daily_report\backups\generate_performance_report_$ts.py"
```

## ⚠ IMPORTANT: Doc & workflow files
- ALL docs, workflows, notes → save to `G:\My Drive\DOCS\transport_daily_report\docs\`
- Do NOT create .md files locally — always save directly to Drive
- Backups → `G:\My Drive\DOCS\transport_daily_report\backups\`

## Steps to generate report

// turbo
1. Run the report generation script:
```powershell
python -u script/generate_performance_report.py --months 3,4 --year 2026
```

2. Copy output to Drive:
```powershell
Copy-Item "output\RAW_DATA_T03+T04_2026.xlsx" "G:\My Drive\DOCS\transport_daily_report\output\" -Force
```

## Key architecture notes

### Kho mapping (KHO_COLORS)
- KRC, THỊT CÁ, ĐÔNG MÁT, ĐÔNG, MÁT, KSL-Sáng, KSL-Tối

### Sub-kho classification (ĐÔNG MÁT → ĐÔNG / MÁT)
Based on "Loại rổ" (col S in trip data):
- `Tote ABA đông mát` → **ĐÔNG**
- `Rổ ABA đông mát` / `Thùng Carton, Bịch nguyên` → **MÁT**

### Weekly tables — Ontime logic per table
| Table | % On Time uses | Extra SLA row? |
|---|---|---|
| THỊT CÁ | **SLA window** (03:00-06:00) | No |
| ĐÔNG MÁT | Plan (arrival ≤ planned) | Yes (% On Time SLA) |
| HÀNG ĐÔNG | Plan (arrival ≤ planned) | Yes (% On Time SLA) |
| HÀNG MÁT | Plan (arrival ≤ planned) | Yes (% On Time SLA) |

### CSS sticky columns
2 cột đầu (KHO + Chỉ Tiêu) freeze khi scroll ngang.

## Verification after generation
- Script now auto-verifies: no "DRY" kho, planned_time coverage, etc.
- Review ⚠ warnings in output and report to user
- Check weekly tables: color gradient, SLA rows, sticky columns
- ĐÔNG MÁT plan ontime ~80% is correct (data verified 2026-04-09)
