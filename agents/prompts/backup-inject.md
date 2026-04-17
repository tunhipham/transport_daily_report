# Backup Inject — Prompt & Context

## Role
Chạy thủ công sau giờ cutoff khi auto_compose đã miss hoặc lỗi inject.

---

## ⚠️ Quy tắc quan trọng

### KHÔNG dùng `--new` flag khi inject

> **TUYỆT ĐỐI KHÔNG** dùng `--new` khi inject.
> Script mặc định **tự dò thread** `"KẾ HOẠCH GIAO HÀNG ... W{week}"` trong Sent → Inbox:
> - **Tìm thấy** → reply vào thread có sẵn ✅
> - **Không tìm thấy** → tự tạo mail mới ✅
>
> `--new` bỏ qua bước dò → **tạo duplicate thread** → loạn mail.

### Check status trước khi inject

| Status | Ý nghĩa | Action |
|--------|---------|--------|
| `final` | Đã compose + inject xong | ❌ Không cần backup |
| `composed` | Đã compose nhưng **chưa inject** | ✅ Cần backup inject |
| `waiting_data` | Chưa có data | ⚠️ Cần xác nhận data rồi mới inject |

### PowerShell — Không dùng `&&`
Dùng `;` thay vì `&&` khi nối lệnh.

---

## Xác định ngày và tuần

- **DRY Tối**: date = ngày hôm nay (D) — lịch tối cùng ngày
- **DRY Sáng / KRC / ĐÔNG MÁT / THỊT CÁ**: date = ngày mai (D+1)
- **Week**: tuần ISO hiện tại (W15, W16...)

---

## Injection Method (Backup)

### PRIMARY: JS base64 + `setData()` (tự động)

`inject_haraworks.py` sẽ dùng JS base64 method tự động — không cần clipboard.
Hoạt động từ mọi session (Task Scheduler, Antigravity terminal...).

### Manual fallback (khi Selenium timeout)

Mở file HTML trong browser để user tự copy:
```powershell
Start-Process "output\_mail_KRC_body.html"
```
User: **Ctrl+A → Ctrl+C** → qua Haraworks CKEditor → **Ctrl+V**

> ⚠️ Clipboard từ terminal session không chia sẻ với desktop session.
> Nếu cần copy thủ công, mở file HTML trong browser rồi copy từ đó.

---

## ⚠️ Compose Order

Compose kho nào xong → **inject ngay** → rồi mới compose kho tiếp.

Generic `_mail_body.html` bị ghi đè mỗi lần compose → inject sau có thể dùng nhầm data kho khác.

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Table hiện raw HTML | Chạy inject lại → reply mới, xóa reply lỗi |
| ĐÔNG MÁT chỉ có ĐÔNG | Re-fetch → re-compose → re-inject |
| Session hết hạn | `Remove-Item $HOME\.edge_automail\ -Recurse -Force` |
| Edge bị lock | `taskkill /f /im msedgedriver.exe` + xóa lockfile |
