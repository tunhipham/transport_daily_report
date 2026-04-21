---
description: Create Telegram groups and manage members via Telethon Client API
---

# Telegram Group Management Workflow

## ⚠ MANDATORY: Read roles & prompts FIRST
Before doing ANYTHING:
1. Read `agents/role.md` — nguyên tắc chung
2. Read `agents/prompts/telegram-group.md` — Telethon setup, credentials, script usage

---

## Cách nhanh nhất (cho Agent)

User sẽ gửi link Google Sheet chứa data → Agent đọc sheet → tạo groups tự động.

### Sheet Format (cột A → E)
| A | B | C | D | E |
|---|---|---|---|---|
| no. | store_code | group_name | member | tag_user |

- **Cột I, J**: username + SĐT để resolve members

### Flow
1. Export sheet CSV: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv`
2. Parse data → tạo batch script (xem `output/scratch/batch_create_groups.py` làm template)
3. Chạy batch → tạo groups + add bot + send DC notice

---

## Quick Reference (Manual)

### Tạo group + add members
// turbo
```
python -u script/telegram/manage_group.py create --name "KRC - A192 (Bùi Đình Túy)" --members `@user1 `@user2 5593486255
```

### Add member vào group đã có
// turbo
```
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@user1
```

### Add bot vào group
// turbo
```
python -u script/telegram/manage_group.py add --group "Tên Group" --members `@transport_daily_report_bot --bot
```

### Gửi thông báo DC NSO vào group
// turbo
```
python -u script/telegram/manage_group.py notify --group "DC - A192" --dc-notice
```

### Gửi tin nhắn tùy chỉnh
// turbo
```
python -u script/telegram/manage_group.py notify --group "Tên Group" --message "Nội dung"
```

### Tìm user không có username (theo tên)
// turbo
```
python -u script/telegram/search_user.py "Tên Người"
```

### Add user bằng ID
// turbo
```
python -u script/telegram/add_by_id.py "Tên Group" 5593486255
```

### Liệt kê / Xem info group
// turbo
```
python -u script/telegram/manage_group.py list
python -u script/telegram/manage_group.py info --group "Tên Group"
```

---

## Steps — Tạo NSO Groups (Full Flow)

### 0. Prerequisites
// turbo
```
pip install telethon
```

Kiểm tra session:
// turbo
```
python -u script/telegram/_login.py --status
```

> Nếu chưa login → xem [First-Run Setup](#first-run-setup)

### 1. User cung cấp Google Sheet
- Mỗi siêu thị (store) tạo **3 groups**: KRC, ABA, DC
- Members từ sheet, resolve bằng username hoặc user ID
- **Thọ Nguyễn** (cố định, không username): ID trong `config/credentials.md`
- Members không có username/SĐT → tìm bằng tên: `search_user.py`

### 2. Tạo groups
Có 2 cách:

**Cách 1: Batch (Agent tạo script)**
- Agent đọc sheet CSV → generate batch script → chạy tự động
- Template: `output/scratch/batch_create_groups.py`

**Cách 2: Manual (từng group)**
```powershell
# Tạo group
python -u script/telegram/manage_group.py create --name "KRC - {store}" --members `@user1 `@user2 5593486255

# Add bot
python -u script/telegram/manage_group.py add --group "KRC - {store}" --members `@transport_daily_report_bot --bot

# DC notice (chỉ group DC)
python -u script/telegram/manage_group.py notify --group "DC - {store}" --dc-notice
```

### 3. Xử lý members không tìm thấy
```powershell
# Tìm user theo tên
python -u script/telegram/search_user.py "Tên Người"

# Add bằng ID
python -u script/telegram/add_by_id.py "Tên Group" USER_ID
```

### 4. Xác nhận kết quả
```powershell
python -u script/telegram/manage_group.py info --group "KRC - {store}"
python -u script/telegram/manage_group.py info --group "ABA - {store}"
python -u script/telegram/manage_group.py info --group "DC - {store}"
```

---

## First-Run Setup

> Chỉ cần làm **1 lần duy nhất**:

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

> 2FA password xem trong `config/credentials.md`

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Không tìm thấy user | `search_user.py "Tên"` → lấy ID → `add_by_id.py` |
| FloodWaitError | Chờ theo thời gian Telegram yêu cầu |
| UserPrivacyRestrictedError | User bật privacy → gửi invite link |
| SessionPasswordNeededError | `python _login.py --password` |
| Session hết hạn | Xóa `.telethon_session.session` → login lại |
| PowerShell ăn @ | Escape: `` `@username `` |
| CreateChatRequest lỗi response | Group vẫn tạo được, check bằng `info` |

---

## Files

| File | Purpose |
|------|---------|
| `script/telegram/manage_group.py` | Script chính: create, add, list, info, notify |
| `script/telegram/_login.py` | Login helper (2 bước, hỗ trợ 2FA) |
| `script/telegram/search_user.py` | Tìm user Telegram theo tên |
| `script/telegram/add_by_id.py` | Add user vào group bằng numeric ID |
| `config/telegram_client.json` | API credentials (gitignored) |
| `config/.telethon_session.session` | Auth session (gitignored) |
| `config/credentials.md` | Tổng hợp credentials + user IDs (gitignored) |
| `agents/prompts/telegram-group.md` | Agent context |
