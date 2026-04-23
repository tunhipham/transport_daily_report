---
description: Compose delivery schedule emails on Haraworks internal mail
---

# Compose Mail Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/compose-mail.md` trước khi chạy.

## Run (recommended — watch mode)

```powershell
python -u script/compose/auto_compose.py --watch
```

Watch mode: poll Drive mỗi 10p → detect file mới → compose → inject FINAL tại cutoff → save draft.

**Flags:**
- `--poll-interval 5` → poll mỗi 5 phút
- `--no-inject` → chỉ compose HTML, không inject
- `--dry-run` → check data mà không compose

## auto_compose commands

```powershell
python -u script/compose/auto_compose.py --status              # xem trạng thái
python -u script/compose/auto_compose.py --force KRC           # force compose KRC
python -u script/compose/auto_compose.py --force DRY --force-session sang  # force DRY Sáng
python -u script/compose/auto_compose.py --reset               # reset state hôm nay
```

## Manual compose + inject

```powershell
# 1. Fetch data
python -u script/domains/performance/fetch_weekly.py --week W{week} --start DD/MM/YYYY

# 2. Compose
python -u script/compose/compose_mail.py --kho KRC --date DD/MM/YYYY
python -u script/compose/compose_mail.py --kho DRY --session sang --date DD/MM/YYYY
python -u script/compose/compose_mail.py --kho DRY --session toi --date DD/MM/YYYY

# 3. Inject (reply vào thread W{week})
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W15
python -u script/compose/inject_haraworks.py --kho "DONG MAT" --date DD/MM/YYYY --week W15
python -u script/compose/inject_haraworks.py --kho "THIT CA" --date DD/MM/YYYY --week W15

# Force compose mail MỚI (đầu tuần, tạo thread mới)
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W15 --new
```

## Validation

- Greeting đúng kho + ngày + session
- Store sort A→Z, time HH:MM
- Kiểm kê highlighted đỏ (DRY only)
- ĐÔNG MÁT có đủ cả ĐÔNG + MÁT
- Draft only — KHÔNG bấm Gửi

## Task Scheduler — `AutoComposeMail`

- Hàng ngày, mỗi 15p, 12:00→20:00 | Config: `config/auto_compose_task.xml`

```powershell
schtasks /query /tn "AutoComposeMail" /v /fo LIST
schtasks /change /tn "AutoComposeMail" /disable
schtasks /change /tn "AutoComposeMail" /enable
```

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Edge bị lock | `taskkill /f /im msedgedriver.exe` + xóa lockfile |
| Session hết hạn | `Remove-Item $HOME\.edge_automail\ -Recurse -Force` → chạy lại |
| Data thiếu / #N/A | Re-fetch data rồi chạy lại |
| DRY bị skip "final" | `python auto_compose.py --reset` |
| ĐÔNG MÁT chỉ có ĐÔNG | Chờ file MÁT hoặc re-fetch |
| Inject sai data | Compose kho nào → inject ngay, rồi compose kho tiếp |

Script lỗi? → Đọc `agents/reference/compose-mail-detail.md` trước khi sửa code.
