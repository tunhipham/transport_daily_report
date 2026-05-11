---
description: Scan NSO emails, merge to master, deploy dashboard
---
# NSO Scan Workflow
// turbo-all

## ⚠ Read `agents/prompts/nso-scan.md` first.

## Flow (manual — user chạy `/nso-scan`)

1. User paste nội dung mail NSO vào chat
2. Agent lưu → `data/nso/mail_wXX.txt`
3. Parse + merge → `nso_stores.json` + `nso_master.xlsx`
4. Deploy dashboard + generate Excel
5. Gửi Telegram **cá nhân** (nso_remind) → chờ user OK → gửi **group** (nso)

## Run

### Parse mail text (user paste):
```powershell
python -u script/domains/nso/inject_mail_text.py --file data/nso/mail_wXX.txt
```

### Deploy + Export:
```powershell
python -u script/dashboard/export_data.py --domain nso
python -u script/domains/nso/export_excel.py
python -u script/domains/weekly_plan/generate_excel.py --week <N>
python -u script/domains/weekly_plan/generate_excel.py --week <N+1>
python -u script/dashboard/deploy.py
```

### Remind daily (giữ nguyên — Task Scheduler):
```powershell
python -u script/domains/nso/nso_remind.py
```

## Prereq
- `data/dsst_cache.json` (refresh: `_save_dsst.py`)

## Telegram

### Lịch KT (tuần này + tuần sau):
1. 📷 Calendar PNG (Playwright render)
2. 📝 Text summary (code, version, ngày, thứ)
3. **Gửi `nso_remind` (cá nhân) TRƯỚC** → user xác nhận → gửi `nso` (group)

### Remind daily (giữ nguyên):
- `nso_remind` → cross-check `master_schedule` + `NSO_SCHEDULE`
- Flag: missing code/schedule_ve/shift/version
- ⚡KT Thứ 5 → nhắc đặc biệt

## Validate
- `data/nso/nso_master.xlsx` · `data/nso/nso_stores.json`
- `output/artifacts/nso/Lich_Khai_Truong_NSO.xlsx`
- Dashboard → Tab NSO (Ctrl+Shift+R)

## ⛔ Data Integrity Rules (CRITICAL)

> [!CAUTION]
> Vi phạm sẽ gây hỏng data production.

1. **Source-of-Truth**: `nso_stores.json` + `nso_master.xlsx` — KHÔNG xóa/rebuild
2. **Lock**: stores có code = locked — không re-match, không ghi đè
3. **Match**: chỉ stores chưa có code — LCS ≥10 + ≥70% trên `name_full` DSST
4. **Telegram**: gửi cá nhân trước, group sau khi user OK
5. **Weekly Plan**: Code=None → KHÔNG match None==None

## Troubleshoot
| Issue | Fix |
|-------|-----|
| 0 stores parsed | Check regex + mail format |
| DSST empty | `_save_dsst.py` with sheet open |
| Tele fail | `config/telegram.json` → `nso`/`nso_remind` |
| False match | Nâng LCS threshold |
| Duplicate stores | Dedup tự động `name_mail + opening_date` |
