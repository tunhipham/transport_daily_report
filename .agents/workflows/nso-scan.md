---
description: Scan NSO emails, merge to master, deploy dashboard
---

# NSO Mail Scanner Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/nso-scan.md` trước khi chạy.

## Prerequisites

- `data/dsst_cache.json` phải có (refresh: `python -u script/domains/nso/_save_dsst.py`)
- Edge browser profile đã login Haraworks

## Run

```powershell
# Auto mode (Thứ 2+3, skip mail cũ)
python -u script/domains/nso/fetch_nso_mail.py

# Force mode (bypass weekday + dedup)
python -u script/domains/nso/fetch_nso_mail.py --force

# Dry run (xem trước, không ghi)
python -u script/domains/nso/fetch_nso_mail.py --force --dry-run
```

## Validation

- Review `output/nso/scan_summary.txt`
- Check `data/nso/nso_master.xlsx` → Sheet "Stores" + "History"
- Dashboard: https://tunhipham.github.io/transport_daily_report/ → Tab NSO (Ctrl+Shift+R)

## Telegram (Thứ 3 — tự động qua Task Scheduler)

Gửi thủ công bất kỳ ngày nào:
```powershell
python -u script/domains/nso/generate.py --send-telegram
```

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
| Telegram không gửi | Check `config/telegram.json` → `nso` domain |
