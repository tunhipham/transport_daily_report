---
description: Compose delivery schedule emails on Haraworks internal mail
---

# Compose Mail Workflow

## ⚠ MANDATORY: Read roles & prompts FIRST
Before doing ANYTHING:
1. Read `agents/role.md` — nguyên tắc chung, phạm vi, quy ước output
2. Read `agents/prompts/compose-mail.md` — mail rules, inject logic, Haraworks setup

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
7. **Kiểm kê (DRY only)**: Siêu thị có lịch kiểm kê tổng ngày X → không nhận hàng ngày D (=X) và D-1 (=X-1). Script tự động fetch lịch kiểm kê và highlight ĐỎ các dòng trùng trong table email để user check.
   - Source: [Lịch kiểm kê 2026](https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/edit?gid=220196646#gid=220196646)
   - Sheet "Lịch Kiểm kê 2026", Col D = ID Mart, Col H = Ngày kiểm kê tổng 2026
8. **Time format**: Giờ luôn HH:MM (leading zero), ví dụ 0:17 → 00:17
9. **THỊT CÁ — fetch = chốt**: Data THỊT CÁ fetch 1 lần là đủ/chính xác. Fetch xong → compose + inject luôn, không cần đợi re-compose hay cutoff.
10. **ĐÔNG MÁT — cần đủ 2 plan**: Gồm 2 file source: "KH HÀNG ĐÔNG" + "KH HÀNG MÁT". **Chỉ compose + inject khi đã fetch đủ cả 2**. Nếu chỉ có 1 → chờ file còn lại.

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

## Quick Reference — Lệnh hay dùng

### Compose + Inject tự động (RECOMMENDED)

// turbo
```
python -u script/compose/auto_compose.py --watch
```

Watch mode sẽ:
1. Poll Google Drive mỗi 10 phút (hoặc `--poll-interval N`)
2. Detect file KH mới cho ngày D+1
3. Fetch data + compose HTML
4. Khi đến cutoff (status FINAL) → tự mở Edge automation → **tìm thread W{week} trong Sent → reply** (hoặc compose mới nếu chưa có thread)
5. Inject HTML vào CKEditor → auto-save draft
6. **KHÔNG bấm Gửi** → user review rồi gửi tay

**Flags:**
- `--poll-interval 5` → poll mỗi 5 phút
- `--no-inject` → chỉ compose HTML, không inject vào Haraworks
- `--dry-run` → check file mà không compose
- **ĐÔNG MÁT**: chờ cả 2 file ĐÔNG + MÁT mới compose
- Ctrl+C để dừng

> **LƯU Ý**: Inject chỉ xảy ra khi status = FINAL (tại cutoff hoặc catch-up).
> Không inject mỗi lần data thay đổi để tránh update draft liên tục.

### Inject thủ công (từng kho)

```powershell
# Reply vào thread có sẵn (mặc định — tự tìm thread W{week})
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W15
python -u script/compose/inject_haraworks.py --kho DRY --session sang --date DD/MM/YYYY --week W15
python -u script/compose/inject_haraworks.py --kho "DONG MAT" --date DD/MM/YYYY --week W15
python -u script/compose/inject_haraworks.py --kho "THIT CA" --date DD/MM/YYYY --week W15

# Force compose mail MỚI (đầu tuần, tạo thread mới)
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W15 --new
```

**Reply vs New logic:**
- Mặc định: script tự tìm thread `"KẾ HOẠCH GIAO HÀNG ... W{week}"` trong **Sent** trước, rồi Inbox → reply
- Nếu không tìm thấy → tự compose mail mới
- `--new` flag: bỏ qua search, force compose mới (dùng cho ngày đầu tuần)

### auto_compose.py commands

// turbo
```
python -u script/compose/auto_compose.py --status
```

- `python script/compose/auto_compose.py` — chạy scheduled (check time window + compose + **auto inject FINAL**)
- `python script/compose/auto_compose.py --status` — xem trạng thái hôm nay
- `python script/compose/auto_compose.py --force KRC` — force compose KRC (bypass time window)
- `python script/compose/auto_compose.py --force DRY --force-session sang` — force DRY Sáng
- `python script/compose/auto_compose.py --dry-run` — check data mà không compose
- `python script/compose/auto_compose.py --no-auto-inject` — compose nhưng không inject vào Haraworks
- `python script/compose/auto_compose.py --reset` — reset state hôm nay

---

## Lịch Check Từng Kho

| Kho | Check Window | Cutoff | Mail cho | Ngày nghỉ | Ghi chú |
|-----|-------------|--------|----------|-----------|--------|
| **DRY Tối** | 12:00 - 14:00 | 14:00 | Tối cùng ngày D | Chủ nhật | Data thay đổi liên tục → re-compose |
| **DRY Sáng** | 15:00 - 16:30 | 16:30 | Sáng ngày D+1 | Chủ nhật | Data thay đổi liên tục → re-compose |
| **ĐÔNG MÁT** | 15:00 - 19:00 | 19:00 | Ngày D+1 | Thứ 2 | ⚠ Cần đủ cả 2 file (ĐÔNG + MÁT) mới compose |
| **KRC** | 17:00 - 19:00 | 19:00 | Ngày D+1 | — | Data thay đổi liên tục → re-compose |
| **THỊT CÁ** | 17:00 - 19:00 | 19:00 | Ngày D+1 | — | ✅ Fetch = chốt → inject luôn |

### Đặc thù từng kho khi compose

- **THỊT CÁ**: Data bình thường fetch 1 lần là chính xác. Fetch xong → compose + inject luôn (không cần đợi cutoff hay re-compose).
- **ĐÔNG MÁT**: Gồm 2 file source trên Drive: "KH HÀNG ĐÔNG" + "KH HÀNG MÁT". Chỉ compose khi đủ cả 2 file. Nếu 1 file chưa có → chờ.
- **DRY / KRC**: Data từ Google Sheets, planner update liên tục → cần re-fetch + re-compose gần cutoff.

### Timeline một ngày (ví dụ Thứ 4)

```
12:00  ─── DRY Tối bắt đầu check ───────────────────────
13:40  │ ⏰ APPROACHING CUTOFF → FINAL compose
14:00  ─── DRY Tối CUTOFF ──────────────────────────────

15:00  ─── DRY Sáng + ĐÔNG MÁT bắt đầu check ─────────
16:10  │ ⏰ DRY Sáng APPROACHING CUTOFF → FINAL
16:30  ─── DRY Sáng CUTOFF ────────────────────────────
       │ ĐÔNG MÁT tiếp tục check...

17:00  ─── KRC + THỊT CÁ bắt đầu check ───────────────
         (THỊT CÁ: fetch đc = inject luôn, ko cần chờ cutoff)
18:40  │ ⏰ ALL APPROACHING CUTOFF → FINAL compose
19:00  ─── KRC + ĐÔNG MÁT + THỊT CÁ CUTOFF ───────────
         (ĐÔNG MÁT: chỉ inject nếu đủ cả 2 plan ĐÔNG + MÁT)

20:00  ─── Task Scheduler dừng ─────────────────────────
```

---

## First-Run Setup (Lần đầu chạy inject)

Selenium dùng **profile Edge riêng** (`.edge_automail/`) để không conflict với Edge đang mở.

**Lần đầu chưa có login session:**
1. Script mở Edge automation → redirect tới Haravan SSO login
2. User login thủ công trong cửa sổ Edge đó (mã **SC012433**)
3. Script tự detect login thành công → tiếp tục inject
4. Session lưu vào `.edge_automail/` → **các lần sau không cần login lại**

**Nếu session hết hạn:** Script tự phát hiện → mở login → chờ user login lại

---

## Windows Task Scheduler

### Task: `AutoComposeMail`

- **Schedule**: Hàng ngày, mỗi 15 phút
- **Window**: 12:00 → 20:00
- **Chạy khi**: User đã login (Interactive)
- **Auto-login**: Nếu session hết hạn, script tự đăng nhập
- **Bỏ lỡ**: Chạy bù khi có thể (StartWhenAvailable = true)
- **Timeout**: 5 phút mỗi lần chạy

### Quản lý Task

```powershell
# Xem trạng thái
schtasks /query /tn "AutoComposeMail" /v /fo LIST

# Chạy thủ công (test)
schtasks /run /tn "AutoComposeMail"

# Tắt tạm / Bật lại
schtasks /change /tn "AutoComposeMail" /disable
schtasks /change /tn "AutoComposeMail" /enable

# Xóa / Tạo lại từ XML
schtasks /delete /tn "AutoComposeMail" /f
schtasks /create /tn "AutoComposeMail" /xml "config\auto_compose_task.xml" /f
```

---

## Steps (Manual — khi không dùng watch mode)

### 0. LUÔN re-fetch data mới nhất trước khi compose (BẮT BUỘC)
// turbo
```
python -u script/domains/performance/fetch_weekly.py --week W{week} --start DD/MM/YYYY
```

⚠️ **QUAN TRỌNG**: Google Sheet nguồn được planner cập nhật liên tục trong ngày.
Data fetch từ sáng có thể thiếu/sai cho ngày D+1 (giờ giao còn #N/A).
**Phải re-fetch ngay trước khi compose** để đảm bảo data đầy đủ.

### 1. Generate HTML email body
// turbo
```
python -u script/compose/compose_mail.py --kho KRC --date DD/MM/YYYY
```
Hoặc cho DRY:
```
python -u script/compose/compose_mail.py --kho DRY --session sang --date DD/MM/YYYY
python -u script/compose/compose_mail.py --kho DRY --session toi --date DD/MM/YYYY
```

### 2. Inject vào Haraworks
```
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W15
```

### 3. Review draft trên Haraworks
- Kiểm tra greeting text đúng kho + ngày + session
- Đếm số rows trong table đúng expected
- Kiểm tra stores có flag kiểm kê (tô đỏ) → báo user
- Thêm To/CC → **Gửi**

---

## Data Change Detection

Script track thay đổi ở mức **từng store + thời gian**:

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
| `script/compose/auto_compose.py` | Orchestrator: watch mode, scheduled compose, state tracking |
| `script/compose/inject_haraworks.py` | Selenium: inject HTML vào Haraworks CKEditor, tạo draft |
| `script/compose/compose_mail.py` | Generate HTML email body cho mỗi kho/ngày |
| `script/domains/performance/fetch_weekly.py` | Fetch data từ Google Sheets + Drive |
| `config/mail_schedule.json` | Config lịch compose + Drive sources |
| `config/auto_compose_task.xml` | XML định nghĩa Windows Task |
| `output/state/auto_compose_state.json` | State tracking (compose count, hash, status) |
| `output/logs/auto_compose.log` | Log file |
| `output/mail/_mail_{kho}_body.html` | Generated HTML body per kho |
| `.edge_automail/` | Edge automation profile (login session lưu ở đây) |

## Troubleshooting

### Inject lỗi sau khi bị gián đoạn (resume/restart)
> **Đã fix 11/04/2026** — script tự cleanup khi khởi động:
> - Tự kill stale `msedgedriver.exe` từ session trước
> - Tự xoá `lockfile` nếu profile bị khoá
> - Clipboard PS1 đã trỏ đúng path Google Drive
>
> Nếu vẫn lỗi, chạy thủ công:
- `taskkill /f /im msedgedriver.exe`
- `Remove-Item $HOME\.edge_automail\lockfile -Force`
- Chạy lại inject

### Session hết hạn
- Script tự detect → mở login → chờ user login
- Nếu bị lỗi: xoá `$HOME\.edge_automail\` folder → chạy lại (login từ đầu)

### Edge đang mở conflict
- Script dùng profile riêng `$HOME\.edge_automail\` (local disk, không phải Google Drive) nên KHÔNG conflict với Edge user đang dùng
- Nếu vẫn lỗi: đóng tất cả Edge → chạy lại

### Data thiếu rows / có #N/A
- Re-fetch data (`fetch_weekly_plan.py`) rồi chạy lại compose/inject
- Rows #N/A → mặc định vào ca sáng nhưng giờ giao sẽ sai

### DRY bị skip vì "final"
- DRY có thể đã compose qua scheduled task → state = "final"
- Fix: `python auto_compose.py --reset` hoặc reset state thủ công

### Task Scheduler không chạy
1. Check: `schtasks /query /tn "AutoComposeMail"`
2. Đảm bảo user đã login (task = Interactive mode)
3. Check log: `output/auto_compose.log`

## Notes

- Haraworks login: SC012433
- Data source: `output/weekly_plan_W{week}.json` (generated by `fetch_weekly_plan.py`)
- CKEditor selector: `[role="textbox"][contenteditable="true"]` hoặc `.ck-editor__editable`
- CKEditor injection: dùng `ckeditorInstance.setData(html)` (CK5 API)
- Vietnamese diacritics: dùng JS injection, KHÔNG dùng browser_press_key
- **An toàn**: Script KHÔNG BAO GIỜ click nút Gửi. Chỉ tạo draft.
