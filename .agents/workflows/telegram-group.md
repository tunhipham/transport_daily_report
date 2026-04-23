---
description: Create Telegram groups and manage members via Telethon Client API
---

# Telegram Group Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/telegram-group.md` trước khi chạy.

## Prerequisites

```powershell
python -u script/telegram/_login.py --status
```

> Chưa login? → Xem First-Run Setup trong prompt file.

## Commands

```powershell
# Tạo group + add members
python -u script/telegram/manage_group.py create --name "Tên Group" --members `@user1 `@user2 5593486255

# Add member / bot vào group đã có
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@user1
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@transport_daily_report_bot --bot

# Gửi thông báo DC NSO / tin nhắn tùy chỉnh
python -u script/telegram/manage_group.py notify --group "DC - A192" --dc-notice
python -u script/telegram/manage_group.py notify --group "Tên Group" --message "Nội dung"

# List / Info
python -u script/telegram/manage_group.py list
python -u script/telegram/manage_group.py info --group "Tên Group"

# Tìm user không có username → lấy ID
python -u script/telegram/search_user.py "Tên Người"
python -u script/telegram/add_by_id.py "Tên Group" USER_ID
```

## Batch Flow (NSO)

1. User cung cấp Google Sheet → Agent export CSV
2. Parse data → generate batch script (template: `output/scratch/batch_create_groups.py`)
3. Chạy batch → tạo groups + add bot + DC notice tự động

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Không tìm thấy user | `search_user.py "Tên"` → lấy ID → `add_by_id.py` |
| FloodWaitError | Chờ theo thời gian Telegram yêu cầu |
| UserPrivacyRestrictedError | Gửi invite link |
| Session hết hạn | Xóa `.telethon_session.session` → login lại |
| PowerShell ăn @ | Escape: `` `@username `` |
| CreateChatRequest lỗi response | Group vẫn tạo được, check bằng `info` |
