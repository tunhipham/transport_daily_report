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
+ Tag user (từ cột E trong sheet) bằng @username hoặc `tg://user?id=ID`

---

## Data Source

- **Google Sheet**: [INFO TẠO GROUP](https://docs.google.com/spreadsheets/d/1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU/edit?usp=sharing)
- **CSV export**: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv`

| Cột | Index | Nội dung |
|-----|-------|---------|
| A | 0 | no. (STT) |
| B | 1 | store_code (VD: A192 (Bùi Đình Túy)) |
| C | 2 | group_name → tên group cần tạo |
| D | 3 | member list (multiline, tên đầy đủ) |
| E | 4 | tag_user (DC notice — tag siêu thị) |
| J | 9 | user_info (bảng lookup tên) |
| K | 10 | @username (bảng lookup) |
| L | 11 | SĐT (bảng lookup, fallback) |

---

## Member Resolution (thứ tự ưu tiên)

1. **Lookup từ cột J→K**: Tên member khớp user_info → lấy @username
2. **Fixed IDs** từ `config/credentials.md`: Members cố định không có username
3. **SĐT** (cột L): Fallback khi không có username → dùng `+84xxx`
4. **Auto-search tên**: `search_user.py "Tên"` → lấy user ID → add trực tiếp

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

- **Rate limit**: Telegram giới hạn add liên tục. Script tự delay 5-15s.
- **Privacy**: User bật privacy → không add được, gửi invite link.
- **PowerShell**: `@` escape → `` `@username ``
- **Workflow 100% turbo**: Khi chạy `/telegram-group`, agent tự mở sheet → tạo groups → add members → add bot → DC notice. Không hỏi gì.
