# Telegram Group — Prompt

Tạo và quản lý group Telegram bằng Telethon Client API. User là owner.

---

## NSO Group Rules

Mỗi NSO (siêu thị mới) tạo **3 groups**:

| Group | Format tên |
|-------|-----------|
| KRC | `KRC - {store_id} ({store_name})` |
| ABA | `ABA - {store_id} ({store_name})` |
| DC | `DC - {store_id} ({store_name})` |

### DC Notice (gửi sau khi tạo DC group)
```
📢 Siêu thị lưu ý:
Hàng DC sẽ châm hàng 4 ngày liên tục cho NSO.
👉 Khai trương ngày D sẽ châm hàng từ ngày D đến hết ngày D+3
👉 Từ ngày D+4 sẽ về hàng DC theo lịch daily
```
+ Tag user (từ cột D/E trong sheet) bằng @username hoặc `tg://user?id=ID`

---

## Data Source

- **Google Sheet**: [INFO TẠO GROUP](https://docs.google.com/spreadsheets/d/1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU/edit?usp=sharing)
- **CSV export**: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv`

| Cột | Nội dung |
|-----|---------|
| B | store_code (A192 (Bùi Đình Túy)) |
| C | group_name |
| D | member list (multiline) |
| E | tag_user (DC notice) |
| I, J | username + SĐT (lookup) |

---

## Member Resolution

1. **Username** (`@xxx`) → ưu tiên nhất
2. **User ID** (số) → members cố định không có username
3. **SĐT** (`+84xxx`) → fallback
4. **Tìm tên** → `search_user.py` → lấy ID

> Members cố định không có username → xem `config/credentials.md`

---

## Credentials

- **Client API**: `config/telegram_client.json` (gitignored)
- **Session**: `config/.telethon_session.session` (auto-generated, gitignored)
- **Bot**: `config/telegram.json` → `@transport_daily_report_bot`
- **2FA + user IDs**: `config/credentials.md` (gitignored)

## First-Run Setup (1 lần duy nhất)

```powershell
python -u script/telegram/_login.py --send          # Gửi OTP
python -u script/telegram/_login.py --code 12345     # Nhập OTP
python -u script/telegram/_login.py --password "xxx" # 2FA (nếu có)
python -u script/telegram/_login.py --status         # Check
```

---

## Lưu ý

- **Rate limit**: Telegram giới hạn add liên tục. Script tự delay 5-10s.
- **Privacy**: User bật privacy → không add được, gửi invite link.
- **PowerShell**: `@` escape → `` `@username ``
