# Telegram Group Management — Prompt & Context

## Role
Tạo và quản lý group Telegram bằng Telegram Client API (Telethon).
User là owner của group được tạo.

---

## Kiến trúc

### Tại sao dùng Telethon (Client API) thay vì Bot API?

| Tính năng | Bot API | Client API (Telethon) |
|-----------|---------|----------------------|
| Tạo group | ❌ | ✅ |
| Tìm user theo username | ❌ | ✅ |
| Add member vào group | ❌ (chỉ qua invite link) | ✅ |
| Owner là user thật | ❌ | ✅ |
| Cần OTP lần đầu | Không | Có (1 lần duy nhất) |

### Cách hoạt động

1. Script dùng **Telethon** đăng nhập bằng account Telegram cá nhân
2. Tạo group → user là **owner** (y như tạo trên app)
3. Tìm members theo **username** hoặc **phone** → add vào group
4. Tuỳ chọn: add bot vào group để gửi notification

---

## Credentials

> 📁 Xem `config/credentials.md` (gitignored) cho đầy đủ API keys, passwords.

### Telegram Client API (Telethon)
- **Config file**: `config/telegram_client.json` (gitignored)
- **Session file**: `config/.telethon_session.session` (auto-generated, gitignored)
- **2FA**: Account bật Two-Step Verification → cần cloud password khi login lần đầu

### Telegram Bot (existing)
- **Config**: `config/telegram.json` (gitignored)

---

## Script

### File: `script/telegram/manage_group.py`

**Chức năng:**
- `create` — Tạo group mới + add members
- `add` — Add members vào group đã có
- `list` — Liệt kê groups hiện tại
- `info` — Xem thông tin group (members, admins)

### Usage

```powershell
# Tạo group mới + add members
python -u script/telegram/manage_group.py create --name "Tên Group" --members @user1 @user2 +84xxx

# Add member vào group đã có
python -u script/telegram/manage_group.py add --group "Tên Group" --members @user1

# Add bot vào group
python -u script/telegram/manage_group.py add --group "Tên Group" --members @bot_username --bot

# Liệt kê tất cả groups
python -u script/telegram/manage_group.py list

# Xem info group
python -u script/telegram/manage_group.py info --group "Tên Group"
```

---

## First-Run Setup

1. **Cài Telethon**: `pip install telethon`
2. **Config đã có sẵn** tại `config/telegram_client.json`
3. **Login dùng `_login.py`** (tránh lỗi stdin interactive):
   ```powershell
   # Bước 1: Gửi OTP
   python -u script/telegram/_login.py --send

   # Bước 2: Nhập OTP (từ app Telegram)
   python -u script/telegram/_login.py --code 12345

   # Bước 3: Nhập 2FA password (nếu account bật 2FA)
   python -u script/telegram/_login.py --password "your_password"

   # Check status
   python -u script/telegram/_login.py --status
   ```
4. **Session được lưu** → các lần sau không cần OTP nữa

---

## Lưu ý quan trọng

1. **Rate limit**: Telegram giới hạn số lượng add member liên tục. Script tự delay 10-15s giữa mỗi lần add.
2. **Privacy**: Một số user bật privacy → không thể add bằng phone, cần username.
3. **Spam protection**: Nếu add quá nhiều người lạ → account có thể bị tạm blocked. Nên add từ từ.
4. **Session bảo mật**: File `.telethon_session.session` chứa auth token → KHÔNG commit lên git.

---

## Files

| File | Purpose |
|------|---------|
| `script/telegram/manage_group.py` | Script chính: tạo group, add member |
| `config/telegram_client.json` | API credentials (api_id, api_hash) |
| `config/.telethon_session.session` | Session file (auto-generated, gitignored) |
| `config/telegram.json` | Bot token config (existing) |
