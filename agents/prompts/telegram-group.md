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
3. Tìm members theo **username**, **phone**, hoặc **user ID** → add vào group
4. Add bot vào group → gửi notification qua Bot API

---

## Credentials

> 📁 Xem `config/credentials.md` (gitignored) cho đầy đủ API keys, passwords, user IDs.

### Telegram Client API (Telethon)
- **Config file**: `config/telegram_client.json` (gitignored)
- **Session file**: `config/.telethon_session.session` (auto-generated, gitignored)
- **2FA**: Account bật Two-Step Verification → cần cloud password khi login lần đầu

### Telegram Bot
- **Config**: `config/telegram.json` (gitignored)
- **Bot**: `@transport_daily_report_bot`

---

## Scripts

| Script | Chức năng |
|--------|----------|
| `script/telegram/manage_group.py` | **Script chính**: create, add, list, info, notify |
| `script/telegram/_login.py` | Login helper (send OTP → enter code → 2FA password) |
| `script/telegram/search_user.py` | Tìm user Telegram theo tên (khi không có username/SĐT) |
| `script/telegram/add_by_id.py` | Add user vào group bằng numeric user ID |

### manage_group.py — Commands

```powershell
# Tạo group mới + add members (username, phone, hoặc user ID)
python -u script/telegram/manage_group.py create --name "Tên Group" --members `@user1 `@user2 5593486255

# Add member vào group đã có
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@user1

# Add bot vào group
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@transport_daily_report_bot --bot

# Gửi thông báo DC NSO (preset)
python -u script/telegram/manage_group.py notify --group "DC - A192" --dc-notice

# Gửi tin nhắn tùy chỉnh
python -u script/telegram/manage_group.py notify --group "Tên Group" --message "Nội dung"

# Liệt kê tất cả groups
python -u script/telegram/manage_group.py list

# Xem info group
python -u script/telegram/manage_group.py info --group "Tên Group"
```

### Utility scripts

```powershell
# Tìm user theo tên (fallback khi không có username/SĐT)
python -u script/telegram/search_user.py "Tên Người"

# Add user bằng ID vào group
python -u script/telegram/add_by_id.py "Tên Group" 5593486255
```

---

## NSO Group Flow

Mỗi NSO (siêu thị mới) cần tạo **3 groups**:

| Group | Format tên | Mục đích |
|-------|-----------|----------|
| **KRC** | `KRC - {store_id} ({store_name})` | Kho rau củ |
| **ABA** | `ABA - {store_id} ({store_name})` | Kho đông mát / thịt cá |
| **DC** | `DC - {store_id} ({store_name})` | Distribution Center - Dry |

### Sau khi tạo DC group → Bot gửi thông báo lưu ý:
```
📢 Siêu thị lưu ý:
Hàng DC sẽ châm hàng 4 ngày liên tục cho NSO.
👉 Khai trương ngày D sẽ châm hàng từ ngày D đến hết ngày D+3
👉 Từ ngày D+4 sẽ về hàng DC theo lịch daily
```
+ Tag user (từ cột D trong sheet) bằng @username hoặc `tg://user?id=ID`

### Data source
- **Google Sheet**: [INFO TẠO GROUP](https://docs.google.com/spreadsheets/d/1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU/edit?usp=sharing)
- **CSV export**: `https://docs.google.com/spreadsheets/d/1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU/export?format=csv`
- User update sheet trước → gọi `/telegram-group` → Agent đọc + tạo group
- Cột A: no.
- Cột B: store_code (ví dụ: A192 (Bùi Đình Túy))
- Cột C: group_name (ví dụ: KRC - A192 (Bùi Đình Túy))
- Cột D: member list (multiline)
- Cột E: tag_user (người cần tag trong DC notice)
- Cột I, J: username + SĐT (lookup table)

### Batch creation flow
1. Export sheet CSV → parse
2. Generate batch script (template: `output/scratch/batch_create_groups.py`)
3. Chạy batch → tạo tất cả groups + add bot + DC notice tự động

---

## Member Resolution Priority

1. **Username** (`@xxx`) → ưu tiên cao nhất, chắc chắn nhất
2. **User ID** (số) → dùng cho members cố định không có username (ví dụ: Thọ Nguyễn)
3. **SĐT** (`+84xxx`) → fallback nếu có
4. **Tìm theo tên** → cuối cùng, dùng `search_user.py` → lấy ID

### Members cố định không có username
Xem `config/credentials.md` → bảng "Telegram — Members không có username"

---

## First-Run Setup

1. **Cài Telethon**: `pip install telethon`
2. **Config đã có sẵn** tại `config/telegram_client.json`
3. **Login dùng `_login.py`** (tránh lỗi stdin interactive):
   ```powershell
   python -u script/telegram/_login.py --send
   python -u script/telegram/_login.py --code 12345
   python -u script/telegram/_login.py --password "your_password"
   python -u script/telegram/_login.py --status
   ```
4. **Session được lưu** → các lần sau không cần OTP nữa

---

## Lưu ý quan trọng

1. **Rate limit**: Telegram giới hạn add member liên tục. Script tự delay 5-10s.
2. **Privacy**: Một số user bật privacy → không add được, gửi invite link.
3. **PowerShell escape**: `@` là special character → escape: `` `@username ``
4. **User không có username**: `search_user.py` → lấy ID → `add_by_id.py` hoặc truyền ID vào `--members`
5. **CreateChatRequest lỗi response**: Group vẫn tạo OK, check bằng `info --group`
6. **Session bảo mật**: `.telethon_session.session` → KHÔNG commit lên git.

---

## Files

| File | Purpose |
|------|---------|
| `script/telegram/manage_group.py` | Script chính: create, add, list, info, notify |
| `script/telegram/_login.py` | Login helper (2 bước, hỗ trợ 2FA) |
| `script/telegram/search_user.py` | Tìm user Telegram theo tên |
| `script/telegram/add_by_id.py` | Add user vào group bằng ID |
| `config/telegram_client.json` | API credentials (gitignored) |
| `config/.telethon_session.session` | Session file (gitignored) |
| `config/telegram.json` | Bot token config (gitignored) |
| `config/credentials.md` | Tổng hợp credentials + user IDs (gitignored) |
