---
description: Scan NSO emails, merge to master, deploy dashboard
---

# NSO Mail Scanner Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/nso-scan.md` trước khi chạy.

## Automated Schedule (Task Scheduler: NsoScan)

| Thời điểm | Mode | Action |
|-----------|------|--------|
| **T2 10:00** | `scan` | Scan mail → deploy → Telegram group + remind cá nhân |
| **T2 15:00** | `track` | Re-scan → deploy + notify CHỈ KHI có thay đổi |
| **T3 09:00** | `scan` | Scan mail cuối → deploy → Telegram group |
| **T3 09:30** | `finalize` | Export + deploy + generate châm hàng Excel |

## Manual Run

```powershell
# Full scan + deploy + Telegram
python -u script/domains/nso/fetch_nso_mail.py

# Scan without deploy (tracking)
python -u script/domains/nso/fetch_nso_mail.py --no-deploy

# Force re-process (skip dedup)
python -u script/domains/nso/fetch_nso_mail.py --force

# Dry run (xem trước, không ghi)
python -u script/domains/nso/fetch_nso_mail.py --force --dry-run

# Remind only (check missing info → personal Telegram)
python -u script/domains/nso/nso_remind.py
python -u script/domains/nso/nso_remind.py --dry-run

# Mode-based via bat
script/domains/nso/auto_nso_watch.bat scan
script/domains/nso/auto_nso_watch.bat track
script/domains/nso/auto_nso_watch.bat finalize
```

## Prerequisites

- `data/dsst_cache.json` phải có (refresh: `python -u script/domains/nso/_save_dsst.py`)
- Edge browser profile đã login Haraworks

## Validation

- Review `output/nso/scan_summary.txt`
- Check `data/nso/nso_master.xlsx` → Sheet "Stores" + "History"
- Dashboard: https://tunhipham.github.io/transport_daily_report/ → Tab NSO (Ctrl+Shift+R)

## Deploy (nếu cần re-deploy)

```powershell
python -u script/dashboard/deploy.py --domain nso
```

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Parsed 0 stores | Email format mới? Check selector + date regex |
| DSST cache empty | Chạy `_save_dsst.py` với DSST sheet mở |
| NSO tab trống | Check JS console cho null code errors |
| Date sai format | Check `22\n/05` pattern → text normalization |
| Telegram không gửi | Check `config/telegram.json` → `nso` / `nso_remind` |
| Task ko chạy | `schtasks /query /tn "NsoScan" /v /fo list` |
