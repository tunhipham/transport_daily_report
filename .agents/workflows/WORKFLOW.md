# Workflows Index

> Danh sách workflows cho project KFM Logistics monorepo.

## Available Workflows

| Slash Command | File | Mô tả | Cadence |
|---------------|------|--------|---------|
| `/daily-report` | [daily-report.md](daily-report.md) | Download data + generate summary report | Hàng ngày |
| `/compose-mail` | [compose-mail.md](compose-mail.md) | Compose delivery schedule emails on Haraworks | Hàng ngày 12:00-19:00 |
| `/backup-inject` | [backup-inject.md](backup-inject.md) | Manual fetch + compose + inject (backup) | Khi cần |
| `/performance-report` | [performance-report.md](performance-report.md) | Generate monthly performance report | Khi cần |
| `/weekly-plan` | [weekly-plan.md](weekly-plan.md) | Tạo/cập nhật lịch tuần giao hàng ST | Thứ 5 hàng tuần |
| `/telegram-group` | [telegram-group.md](telegram-group.md) | Tạo group Telegram + add members | Khi cần |
| `/dashboard` | [dashboard.md](dashboard.md) | Deploy dashboard lên GitHub Pages | Sau mỗi report |

## Project Structure

```
.agents/
  workflows/         ← Workflow files (bạn đang ở đây)

agents/
  prompts/           ← Agent context prompts
    weekly-plan.md   ← Context cho weekly transport plan
    compose-mail.md  ← Context cho compose mail
    daily-report.md  ← Context cho daily report
    ...

data/
  master_schedule.json ← 🔒 Master data: lịch chia/về/shift (CỐ ĐỊNH)
  master_schedule.xlsx ← 🔒 Backup Excel

script/
  dashboard/         ← Dashboard export + deploy
  domains/           ← Domain-specific logic (daily, inventory, nso, performance)
  compose/           ← Email composition
  orchestrator/      ← Auto-compose orchestrator
  lib/               ← Shared libraries (sources, utils)

output/
  artifacts/         ← Report artifacts per domain
    daily/
    inventory/
    nso/
    performance/
    weekly transport plan/   ← Excel files Lịch đi hàng ST W{nn}

docs/
  index.html         ← Dashboard SPA (5 tabs)
  data/              ← JSON data files per domain
```

## Quick Reference

```powershell
# Daily report
python script/domains/daily/generate.py --send

# Performance report
python script/domains/performance/generate.py --month 04

# Weekly plan export + deploy
python script/dashboard/deploy.py --domain weekly_plan

# Deploy all domains
python script/dashboard/deploy.py --domain all

# Compose mail (auto mode)
python -u script/auto_compose.py --watch
```
