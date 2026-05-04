---
description: Scan NSO emails, merge to master, deploy dashboard
---
# NSO Scan Workflow
// turbo-all

## ⚠ Read `agents/prompts/nso-scan.md` first.

## Schedule (Task Scheduler: NsoScan)

| Time | Mode | Action |
|------|------|--------|
| T2 10h | `scan` | Scan → merge → calendar PNG → deploy → Tele group (photo+text) + remind |
| T2 15h | `scan` | Re-scan → deploy+Tele group CHỈ KHI mail mới/thay đổi + remind |
| T3 9h | `scan` | Scan cuối → deploy → Tele group (nếu mail mới) + remind |
| T3 9h30 | `finalize` | Deploy + châm hàng Excel (tuần này + draft tuần sau) |

> ⚠ Nếu 3 lần scan liên tiếp không có mail mới → warning Telegram cá nhân

## Run

### Auto (browser scan):
```powershell
python -u script/domains/nso/fetch_nso_mail.py          # scan+deploy
python -u script/domains/nso/fetch_nso_mail.py --force   # skip dedup
```

### Manual (text paste — khi browser lỗi):
```powershell
python -u script/domains/nso/inject_mail_text.py --file data/nso/mail_w19.txt --send
```
→ Parse mail text → merge → calendar PNG → deploy → Telegram (photo+text) → châm hàng Excel

### Other:
```powershell
python -u script/domains/nso/nso_remind.py --dry-run     # remind preview
script/domains/nso/auto_nso_watch.bat scan|finalize       # Task Scheduler entry point
```

## Prereq
- `data/dsst_cache.json` (refresh: `_save_dsst.py`)
- Edge profile logged into Haraworks (browser mode only)

## Telegram Output
1. 📷 Calendar PNG (Playwright render, self-contained)
2. 📝 Text: stores KT tuần này + tuần sau (code, version, ngày, thứ)
3. Gửi vào group `nso` + remind cá nhân `nso_remind`

## Validate
- `output/state/nso/scan_summary.txt` · `data/nso/nso_master.xlsx`
- `output/state/nso/nso_calendar.png` — preview calendar image
- Dashboard → Tab NSO (Ctrl+Shift+R)

## Troubleshoot
| Issue | Fix |
|-------|-----|
| 0 stores parsed | Check email selector + date regex |
| Browser timeout | Dùng `inject_mail_text.py` thay thế |
| DSST empty | `_save_dsst.py` with sheet open |
| Tele fail | `config/telegram.json` → `nso`/`nso_remind` |
| Task fail | `schtasks /query /tn "NsoScan" /v /fo list` |
