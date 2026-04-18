# Compose Mail — Prompt & Context

## Role
Soạn email lịch giao hàng cho từng kho, inject vào Haraworks internal mail.

## 🔴 BẮT BUỘC: Fetch lại lịch kiểm kê trước mỗi lần compose

Lịch kiểm kê thay đổi liên tục (người input update bất kỳ lúc nào). Script `compose_mail.py` tự fetch mỗi lần chạy.
**KHÔNG BAO GIỜ** dùng data kiểm kê cũ từ cache hay từ lần chạy trước.

> Cũng áp dụng cho `export_weekly_plan.py` khi làm lịch tuần.

---

## Rules (QUAN TRỌNG)

1. **D+1**: Mail mỗi kho là lịch giao hàng cho ngày D+1 (ngày mai)
2. **KSL (DRY) chia 2 mail**: 
   - Mail Sáng: giờ từ 6h → 15h (hour 6-14)
   - Mail Tối: giờ từ 15h → 3h sáng hôm sau (hour 15-23, 0-2)
   - Ngày D sẽ mail: lịch tối ngày D + lịch sáng ngày D+1
3. **Mỗi week = 1 thread**: W14, W15... mỗi tuần dùng 1 thread email, ngày mới reply vào thread đó
4. **Store ID sort A→Z**: Cột "Điểm đến" luôn sort alphabetical
5. **Chỉ soạn DRAFT, KHÔNG BẤM GỬI** cho tới khi user xác nhận
6. **Không có lịch fix**: User sẽ nói kho nào có data rồi để soạn
7. **Kiểm kê (DRY only)**: Siêu thị có lịch kiểm kê tổng → không nhận hàng. Script tự fetch và highlight ĐỎ.
   - Source: [Lịch kiểm kê 2026](https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/edit?gid=220196646#gid=220196646)
8. **Time format**: Giờ luôn HH:MM (leading zero), ví dụ 0:17 → 00:17

---

## Thông tin mail

| Kho | Subject | To | Body greeting |
|-----|---------|-----|---------------|
| KRC | KẾ HOẠCH GIAO HÀNG KRC W{week} | Nhiều stores | Dear team ST, SCM gửi thông tin kế hoạch giao hàng KHO RCQ ngày {date}. |
| DRY Sáng | KẾ HOẠCH GIAO HÀNG KHO DRY W{week} | Đoàn Thanh Long | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng DC Dry Sáng {date}. |
| DRY Tối | (reply trong thread DRY) | (reply all) | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng DC Dry Tối {date}. |
| ĐÔNG MÁT | KẾ HOẠCH GIAO HÀNG KHO ĐÔNG MÁT W{week} | (stores) | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng Đông Mát ngày {date}. |
| THỊT CÁ | KẾ HOẠCH GIAO HÀNG KHO ABA THỊT CÁ W{week} | (stores) | Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng Thịt Cá ngày {date}. |

### CC List (tất cả các kho)
Operations, Operations Training & Development, Operations Excellence, Sales, Delivery, Delivery 1, Regional Sales 1, HCM 001, Đối Tác Seedlog, DC Seedlog (cho DRY)

### Table columns
- **KRC, DRY, THỊT CÁ**: Ngày | Điểm đến | Giờ đến dự kiến (+-30')
- **ĐÔNG MÁT**: Ngày | Điểm đến | Giờ đến dự kiến (+-30') | Loại hàng

---

## Lịch Check Từng Kho

| Kho | Check Window | Cutoff | Mail cho | Ngày nghỉ |
|-----|-------------|--------|----------|-----------|
| **DRY Tối** | 12:00 - 14:00 | 14:00 | Tối cùng ngày D | Chủ nhật |
| **DRY Sáng** | 15:00 - 16:30 | 16:30 | Sáng ngày D+1 | Chủ nhật |
| **ĐÔNG MÁT** | 15:00 - 19:00 | 19:00 | Ngày D+1 | Thứ 2 |
| **KRC** | 17:00 - 19:00 | 19:00 | Ngày D+1 | — |
| **THỊT CÁ** | 17:00 - 19:00 | 19:00 | Ngày D+1 | — |

### Timeline một ngày (ví dụ Thứ 4)

```
12:00  ─── DRY Tối bắt đầu check ───────────────────────
14:00  ─── DRY Tối CUTOFF ──────────────────────────────

15:00  ─── DRY Sáng + ĐÔNG MÁT bắt đầu check ─────────
16:30  ─── DRY Sáng CUTOFF ────────────────────────────

17:00  ─── KRC + THỊT CÁ bắt đầu check ───────────────
19:00  ─── KRC + ĐÔNG MÁT + THỊT CÁ CUTOFF ───────────

20:00  ─── Task Scheduler dừng ─────────────────────────
```

---

## Windows Task Scheduler — `AutoComposeMail`

- **Schedule**: Hàng ngày, mỗi 15 phút, 12:00 → 20:00
- **Config**: `config/auto_compose_task.xml`

```powershell
schtasks /query /tn "AutoComposeMail" /v /fo LIST
schtasks /run /tn "AutoComposeMail"
schtasks /change /tn "AutoComposeMail" /disable
schtasks /change /tn "AutoComposeMail" /enable
```

---

## First-Run Setup (Inject)

Selenium dùng **profile Edge riêng** (`.edge_automail/`) — không conflict với Edge user.

1. Script mở Edge automation → Haravan SSO login
2. User login thủ công (mã **SC012433**)
3. Session lưu vào `.edge_automail/` → các lần sau không cần login lại

---

## Data Change Detection

| Loại thay đổi | Cách detect | Action |
|---------------|-------------|--------|
| Thêm store mới | So sánh set store IDs | ➕ Re-compose |
| Bớt store | So sánh set store IDs | ➖ Re-compose |
| Đổi giờ giao | So sánh gio_den per store | 🔄 Re-compose |
| Không thay đổi | Hash giống nhau | ✓ Skip |

---

## Files

| File | Purpose |
|------|---------|
| `script/compose/auto_compose.py` | Orchestrator: watch mode, scheduled compose |
| `script/compose/inject_haraworks.py` | Selenium: inject HTML vào Haraworks CKEditor |
| `script/compose/compose_mail.py` | Generate HTML email body |
| `script/domains/performance/fetch_weekly.py` | Fetch data từ Google Sheets + Drive |
| `config/mail_schedule.json` | Config lịch compose + Drive sources |
| `config/auto_compose_task.xml` | XML định nghĩa Windows Task |

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Table hiện raw HTML | Chạy inject lại — sẽ reply mới, xóa reply lỗi |
| ĐÔNG MÁT chỉ có ĐÔNG | Re-fetch → re-compose → re-inject |
| Session hết hạn | `Remove-Item $HOME\.edge_automail\ -Recurse -Force` → chạy lại |
| Edge bị lock | `taskkill /f /im msedgedriver.exe` + xóa lockfile |
| Data thiếu / #N/A | Re-fetch data rồi chạy lại |
| DRY bị skip | `python auto_compose.py --reset` |
| Inject sai data (kho A inject data kho B) | Generic `_mail_body.html` bị ghi đè bởi kho compose sau. **Compose kho nào thì inject ngay** hoặc compose kho cuối cùng trước khi inject. |

---

## Injection Method

### PRIMARY: JS base64 + `setData()` (session-independent)

- Encode HTML → base64 → gửi qua `execute_script()` in chunks
- Decode trong browser → gọi `ckeditorInstance.setData(html)`
- **Không phụ thuộc clipboard** → hoạt động từ mọi session (terminal, Task Scheduler, Antigravity)

### FALLBACK: Clipboard paste (Ctrl+V)

- Copy HTML vào OS clipboard (CF_HTML format) → `Ctrl+V` trong CKEditor
- **Chỉ hoạt động khi run cùng desktop session** (Task Scheduler OK, Antigravity terminal FAIL)

> ⚠️ **Backup từ terminal**: Luôn dùng JS base64 method (method 1). Clipboard paste sẽ fail vì khác session.

---

## ⚠️ Compose Order (Backup)

Khi compose backup nhiều kho:
- `compose_mail.py` ghi cả file generic `_mail_body.html` lẫn file kho-specific `_mail_{kho}_body.html`
- `inject_haraworks.py` ưu tiên file **mới nhất** giữa generic vs kho-specific
- **Nếu compose KRC rồi compose ĐÔNG MÁT** → generic file = ĐÔNG MÁT → inject KRC dùng nhầm data

**Giải pháp**: Compose kho nào xong → inject ngay → rồi mới compose kho tiếp.

---

## Notes

- Haraworks login: SC012433
- CKEditor: `[role="textbox"][contenteditable="true"]`
- CKEditor injection: `ckeditorInstance.setData(html)` (CK5 API)
- **An toàn**: Script KHÔNG BAO GIỜ click nút Gửi. Chỉ tạo draft.
