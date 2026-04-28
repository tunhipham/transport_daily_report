---
description: Scan NSO emails, merge to master, deploy dashboard
---
# NSO Scan Workflow
// turbo-all

## ⚠ Read `agents/prompts/nso-scan.md` first.

## Schedule (Task Scheduler: NsoScan)

| Time | Mode | Action |
|------|------|--------|
| T2 10h | `scan` | Scan → deploy → Tele group (nếu mail mới) + remind |
| T2 15h | `scan` | Re-scan → deploy+Tele group CHỈ KHI mail mới/thay đổi + remind |
| T3 9h | `scan` | Scan cuối → deploy → Tele group (nếu mail mới) + remind |
| T3 9h30 | `finalize` | Deploy + châm hàng Excel |

> ⚠ Nếu 3 lần scan liên tiếp không có mail mới → warning Telegram cá nhân

## Run

```powershell
python -u script/domains/nso/fetch_nso_mail.py          # scan+deploy
python -u script/domains/nso/fetch_nso_mail.py --force   # skip dedup
python -u script/domains/nso/nso_remind.py --dry-run     # remind preview
script/domains/nso/auto_nso_watch.bat scan|finalize
```

## Prereq
- `data/dsst_cache.json` (refresh: `_save_dsst.py`)
- Edge profile logged into Haraworks

## Validate
- `output/nso/scan_summary.txt` · `data/nso/nso_master.xlsx`
- Dashboard → Tab NSO (Ctrl+Shift+R)

## Troubleshoot
| Issue | Fix |
|-------|-----|
| 0 stores parsed | Check email selector + date regex |
| DSST empty | `_save_dsst.py` with sheet open |
| Tele fail | `config/telegram.json` → `nso`/`nso_remind` |
| Task fail | `schtasks /query /tn "NsoScan" /v /fo list` |
