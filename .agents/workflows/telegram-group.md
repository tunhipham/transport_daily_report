---
description: Create Telegram groups and manage members via Telethon Client API
---

# Telegram Group Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/telegram-group.md` trước khi chạy.

## Step 1 — Check session

```powershell
python -u script/telegram/_login.py --status
```

> Chưa login? → Xem First-Run Setup trong prompt file. **Nếu OK → tiếp.**

## Step 2 — Open Google Sheet

Mở link Google Sheet để user xem/cập nhật data trước khi tạo:

```powershell
start "https://docs.google.com/spreadsheets/d/1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU/edit"
```

## Step 3 — Dry run (preview)

Fetch sheet → parse → hiển thị plan. Chưa tạo gì.

```powershell
python -u script/telegram/batch_nso.py
```

> Review output. Nếu có member unresolved, script tự search tên + dùng SĐT fallback.

## Step 4 — Execute (tạo groups + add members + bot + DC notice)

```powershell
python -u script/telegram/batch_nso.py --execute --notice
```

> Script tự:
> 1. Tạo mỗi group từ cột C
> 2. Add members từ cột D (resolve qua lookup J→L, fixed IDs, search tên)
> 3. Add bot `@transport_daily_report_bot` vào mỗi group
> 4. Gửi DC notice cho group DC (tag user từ cột E)
> 5. Skip group đã tồn tại

## Manual Commands (nếu cần)

```powershell
# Tạo 1 group thủ công
python -u script/telegram/manage_group.py create --name "Tên Group" --members `@user1 `@user2 5593486255

# Add member / bot vào group đã có
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@user1
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@transport_daily_report_bot --bot

# Gửi DC notice / tin nhắn
python -u script/telegram/manage_group.py notify --group "DC - A192" --dc-notice
python -u script/telegram/manage_group.py notify --group "Tên Group" --message "Nội dung"

# List / Info
python -u script/telegram/manage_group.py list
python -u script/telegram/manage_group.py info --group "Tên Group"

# Tìm user không có username → lấy ID
python -u script/telegram/search_user.py "Tên Người"
python -u script/telegram/add_by_id.py "Tên Group" USER_ID
```

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Không tìm thấy user | Script tự search tên + SĐT fallback |
| FloodWaitError | Chờ theo thời gian Telegram yêu cầu |
| UserPrivacyRestrictedError | Gửi invite link |
| Session hết hạn | Xóa `.telethon_session.session` → login lại |
| PowerShell ăn @ | Escape: `` `@username `` |
| CreateChatRequest lỗi response | Group vẫn tạo được, check bằng `info` |
