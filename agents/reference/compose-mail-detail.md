# Compose Mail — Detail Reference

> Chỉ đọc file này khi debug hoặc sửa code. Không đọc khi chạy compose bình thường.

---

## Injection Method

### PRIMARY: JS base64 + `setData()` (session-independent)
- Encode HTML → base64 → gửi qua `execute_script()` in chunks
- Decode trong browser → `ckeditorInstance.setData(html)`
- Không phụ thuộc clipboard → hoạt động từ mọi session

### FALLBACK: Clipboard paste (Ctrl+V)
- Copy HTML vào OS clipboard (CF_HTML format) → `Ctrl+V` trong CKEditor
- Chỉ hoạt động khi run cùng desktop session

> ⚠ Backup từ terminal: luôn dùng JS base64. Clipboard paste sẽ fail vì khác session.

---

## First-Run Setup (Edge)

Selenium dùng profile Edge riêng (`$HOME\.edge_automail\`) — không conflict với Edge user.

1. Script mở Edge → Haravan SSO login
2. User login thủ công (mã **SC012433**)
3. Session lưu → các lần sau không cần login lại
4. Session hết hạn → script tự detect → chờ user login lại

---

## Compose Order Warning

`compose_mail.py` ghi cả file generic `_mail_body.html` lẫn `_mail_{kho}_body.html`.
`inject_haraworks.py` ưu tiên file mới nhất.

**Nếu compose KRC rồi compose ĐÔNG MÁT** → generic = ĐÔNG MÁT → inject KRC dùng nhầm data.
**Giải pháp**: Compose kho nào → inject ngay → rồi compose kho tiếp.

---

## Data Change Detection

| Loại thay đổi | Detect | Action |
|---------------|--------|--------|
| Thêm/bớt store | So sánh set store IDs | Re-compose |
| Đổi giờ giao | So sánh gio_den per store | Re-compose |
| Không đổi | Hash giống | Skip |

---

## Reply vs New Logic

- Mặc định: tìm thread `"KẾ HOẠCH GIAO HÀNG ... W{week}"` trong Sent → Inbox → reply
- Không tìm thấy → compose mail mới
- `--new` flag: force compose mới (đầu tuần)

---

## Files

| File | Purpose |
|------|---------|
| `script/compose/auto_compose.py` | Orchestrator: watch + scheduled compose |
| `script/compose/inject_haraworks.py` | Selenium: inject HTML vào CKEditor |
| `script/compose/compose_mail.py` | Generate HTML email body |
| `config/mail_schedule.json` | Config lịch compose + Drive sources |
| `output/state/auto_compose_state.json` | State tracking |
| `output/mail/_mail_{kho}_body.html` | Generated HTML body per kho |
| `.edge_automail/` | Edge automation profile |

---

## Timeline một ngày

```
12:00  ─── DRY Tối check ─────────────────────
14:00  ─── DRY Tối CUTOFF ────────────────────

15:00  ─── DRY Sáng + ĐÔNG MÁT check ────────
16:30  ─── DRY Sáng CUTOFF ───────────────────

17:00  ─── KRC + THỊT CÁ check ───────────────
         (THỊT CÁ: fetch đc = inject luôn)
19:00  ─── KRC + ĐÔNG MÁT + THỊT CÁ CUTOFF ──
         (ĐÔNG MÁT: chỉ nếu đủ cả 2 plan)

20:00  ─── Task Scheduler dừng ────────────────
```

## Notes

- Haraworks login: SC012433
- CKEditor: `[role="textbox"][contenteditable="true"]`
- CKEditor API: `ckeditorInstance.setData(html)` (CK5)
- Script KHÔNG BAO GIỜ click nút Gửi.
