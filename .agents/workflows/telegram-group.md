---
description: Create Telegram groups and manage members via Telethon Client API
---

# Telegram Group Management Workflow

## ⚠ MANDATORY: Read roles & prompts FIRST
Before doing ANYTHING:
1. Read `agents/role.md` — nguyên tắc chung
2. Read `agents/prompts/telegram-group.md` — Telethon setup, credentials, script usage

---

## Quick Reference

### Tạo group + add members
// turbo
```
python -u script/telegram/manage_group.py create --name "Tên Group" --members @user1 @user2
```

### Add member vào group đã có
// turbo
```
python -u script/telegram/manage_group.py add --group "Tên Group" --members @user1
```

### Add bot vào group
// turbo
```
python -u script/telegram/manage_group.py add --group "Tên Group" --members @kfm_transport_bot --bot
```

### Liệt kê groups
// turbo
```
python -u script/telegram/manage_group.py list
```

### Xem info group
// turbo
```
python -u script/telegram/manage_group.py info --group "Tên Group"
```

---

## Steps (Full Flow)

### 0. Prerequisites
// turbo
```
pip install telethon
```

Kiểm tra config tồn tại:
// turbo
```
type config\telegram_client.json
```

### 1. User cung cấp thông tin
- **Tên group**: Bắt buộc
- **Members**: username (@xxx) hoặc số điện thoại (+84xxx)
- **Add bot?**: Có/Không

### 2. Tạo group
// turbo
```
python -u script/telegram/manage_group.py create --name "{group_name}" --members {member_list}
```

Script sẽ:
1. Login Telegram (lần đầu: nhập phone + OTP)
2. Tạo group → user là **owner**
3. Add từng member (delay 10s giữa mỗi người)
4. In kết quả: success / failed / already_in

### 3. Xác nhận kết quả
- Kiểm tra group đã tạo trên Telegram app
- Kiểm tra members đã add đủ
- Nếu cần add thêm → dùng lệnh `add`

---

## First-Run Setup

> Chỉ cần làm **1 lần duy nhất**:

1. Chạy script → nhập **số điện thoại** (format: +84xxxxxxxxx)
2. Mở **app Telegram trên điện thoại** → lấy mã OTP
3. Nhập OTP → đăng nhập thành công
4. Session được lưu → **các lần sau không cần OTP**

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Không tìm thấy user | Kiểm tra username có đúng không (bỏ @) |
| FloodWaitError | Chờ theo thời gian Telegram yêu cầu |
| UserPrivacyRestrictedError | User bật privacy → không add được, gửi invite link |
| SessionPasswordNeededError | Account bật 2FA → cần nhập password |
| Session hết hạn | Xóa `config/.telethon_session.session` → login lại |

---

## Files

| File | Purpose |
|------|---------|
| `script/telegram/manage_group.py` | Script chính |
| `config/telegram_client.json` | API credentials |
| `config/.telethon_session.session` | Auth session (auto-generated) |
| `agents/prompts/telegram-group.md` | Agent context |
