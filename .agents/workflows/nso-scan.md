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

## ⛔ Data Integrity Rules (CRITICAL)

> [!CAUTION]
> Các rule dưới đây là **bắt buộc**, vi phạm sẽ gây hỏng data production.

### 1. Single Source-of-Truth
- `data/nso/nso_stores.json` + `data/nso/nso_master.xlsx` là **master duy nhất**
- **KHÔNG BAO GIỜ** xóa master để rebuild từ đầu — data cũ có mappings thủ công không thể tái tạo
- Chỉ append data mới, không sửa/ghi đè data cũ

### 2. Lock After Validation
- Sau khi user xác nhận NSO data OK → coi như **locked**
- Các lần inject tiếp theo chỉ **thêm stores mới** hoặc **update ngày khai trương** (dời lịch)
- **KHÔNG** re-match code, re-map tên, hoặc xóa code của stores đã có

### 3. DSST Matching Rules
- Chỉ match stores **CHƯA CÓ code** (stores mới từ mail)
- Match dựa trên `name_full` từ DSST (KHÔNG dùng `branch_name` — có prefix hệ thống)
- Threshold: **LCS ≥ 10 ký tự VÀ ≥ 70%** tên ngắn hơn
- Nếu tên < 10 ký tự → phải match hoàn toàn (full containment)
- Stores đã có code → **giữ nguyên**, chỉ fill fields missing (name_system, version)
- Khi match được → lấy `code` + `name_full` + `name_system` + `version` từ DSST

### 4. Telegram
- **KHÔNG gửi `--send`** khi đang debug/test — chỉ dùng khi data đã verified
- Nếu cần test → bỏ flag `--send` hoặc dùng `--dry-run`

### 5. Weekly Plan
- NSO stores không có code → dùng `name_full` hoặc `name_mail` để hiển thị
- Code = `None` → **KHÔNG** match với bất kỳ store nào khác cũng `None`

## Troubleshoot
| Issue | Fix |
|-------|-----|
| 0 stores parsed | Check email selector + date regex |
| Browser timeout | Dùng `inject_mail_text.py` thay thế |
| DSST empty | `_save_dsst.py` with sheet open |
| Tele fail | `config/telegram.json` → `nso`/`nso_remind` |
| Task fail | `schtasks /query /tn "NsoScan" /v /fo list` |
| False match | Nâng LCS threshold hoặc review `_debug_lcs.py` |
| Duplicate stores | Dedup tự động theo `name_mail + opening_date` |
