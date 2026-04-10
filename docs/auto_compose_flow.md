# Auto Compose Mail — Tài liệu hệ thống

> Tự động check data + compose email kế hoạch giao hàng cho 4 kho, chạy hàng ngày qua Windows Task Scheduler.

---

## Tổng quan Flow

```
Windows Task Scheduler (mỗi 15 phút, 12:00-20:00)
         │
         ▼
   auto_compose_task.bat
         │
         ▼
   auto_compose.py
         │
         ├── Load config (mail_schedule.json)
         ├── Check time window từng kho
         ├── Check day-of-week exclusions
         │
         ▼
   Kho nào đang trong window?
         │
    ┌────┴────┐
    │ ACTIVE  │ → fetch_weekly_plan.py (re-fetch data mới nhất)
    │         │ → Load data từ weekly_plan_W{n}.json
    │         │ → Compute hash → so sánh với lần compose trước
    │         │
    │  Có thay đổi?
    │    │
    │   YES → compose_mail.py (generate HTML)
    │    │    ├── DRY: check lịch kiểm kê (highlight đỏ)
    │    │    ├── Output: _mail_body.html + _mail_inject.js
    │    │    ├── Save kho-specific copies
    │    │    └── Windows notification 🔔
    │    │
    │    NO → "No changes since last compose" → skip
    │
    │  Gần cutoff (20 phút trước)?
    │    │
    │   YES → FINAL compose → mark done
    │
    └────┬────┐
         │ NOT ACTIVE │ → skip, show status
         └────────────┘
         │
         ▼
   Save state (auto_compose_state.json)
   Log (auto_compose.log)
```

---

## Lịch check từng kho

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
12:15  │ check #2 (nếu data thay đổi → re-compose)
12:30  │ check #3
12:45  │ check #4
13:00  │ check #5
13:15  │ check #6
13:30  │ check #7
13:40  │ ⏰ APPROACHING CUTOFF → FINAL compose
14:00  ─── DRY Tối CUTOFF ──────────────────────────────

15:00  ─── DRY Sáng + ĐÔNG MÁT bắt đầu check ─────────
15:15  │ check #2
15:30  │ check #3
15:45  │ check #4
16:00  │ check #5
16:10  │ ⏰ DRY Sáng APPROACHING CUTOFF → FINAL
16:30  ─── DRY Sáng CUTOFF ────────────────────────────
       │ ĐÔNG MÁT tiếp tục check...

17:00  ─── KRC + THỊT CÁ bắt đầu check ───────────────
17:15  │ check #2
...    │ (tiếp tục mỗi 15 phút)
18:40  │ ⏰ ALL APPROACHING CUTOFF → FINAL compose
19:00  ─── KRC + ĐÔNG MÁT + THỊT CÁ CUTOFF ───────────

20:00  ─── Task Scheduler dừng ─────────────────────────
```

---

## Files hệ thống

### Scripts

| File | Chức năng |
|------|-----------|
| `script/auto_compose.py` | Script chính — orchestrate check + compose |
| `script/auto_compose_task.bat` | Wrapper cho Task Scheduler |
| `script/compose_mail.py` | Generate HTML email body cho từng kho |
| `script/fetch_weekly_plan.py` | Fetch data từ Google Sheets/Drive |

### Config

| File | Chức năng |
|------|-----------|
| `config/mail_schedule.json` | Lịch check/cutoff từng kho |
| `config/auto_compose_task.xml` | XML định nghĩa Windows Task |

### Output (generated per run)

| File | Chức năng |
|------|-----------|
| `output/_mail_body.html` | HTML email body (latest compose) |
| `output/_mail_inject.js` | JS snippet inject CKEditor |
| `output/_clip_html.ps1` | PowerShell copy HTML clipboard |
| `output/_mail_{KHO}_body.html` | Bản copy theo kho (VD: `_mail_DRY_toi_body.html`) |
| `output/auto_compose_state.json` | State tracking (đã compose kho nào) |
| `output/auto_compose.log` | Log file |
| `output/weekly_plan_W{n}.json` | Data tuần (input cho compose) |

---

## Windows Task Scheduler

### Task: `AutoComposeMail`

- **Schedule**: Hàng ngày, mỗi 15 phút
- **Window**: 12:00 → 20:00
- **Chạy khi**: User đã login (Interactive)
- **Auto-login**: Nếu session hết hạn, script tự đăng nhập (Dismiss → Sign in with password → nhập credentials → Login)
- **Bỏ lỡ**: Chạy bù khi có thể (StartWhenAvailable = true)
- **Timeout**: 5 phút mỗi lần chạy

### Quản lý Task

```powershell
# Xem trạng thái
schtasks /query /tn "AutoComposeMail" /v /fo LIST

# Chạy thủ công (test)
schtasks /run /tn "AutoComposeMail"

# Tắt tạm
schtasks /change /tn "AutoComposeMail" /disable

# Bật lại
schtasks /change /tn "AutoComposeMail" /enable

# Xóa
schtasks /delete /tn "AutoComposeMail" /f

# Tạo lại từ XML
schtasks /create /tn "AutoComposeMail" /xml "config\auto_compose_task.xml" /f
```

---

## CLI Commands

```powershell
# Xem trạng thái hôm nay
python script/auto_compose.py --status

# Chạy scheduled (check all time windows)
python script/auto_compose.py

# Force compose cho 1 kho (bypass time window)
python script/auto_compose.py --force KRC
python script/auto_compose.py --force DRY --force-session sang
python script/auto_compose.py --force DRY --force-session toi
python script/auto_compose.py --force "ĐÔNG MÁT"
python script/auto_compose.py --force "THỊT CÁ"

# Check data mà không compose
python script/auto_compose.py --dry-run

# Dùng data có sẵn (không re-fetch)
python script/auto_compose.py --no-fetch

# Reset state hôm nay (compose lại từ đầu)
python script/auto_compose.py --reset
```

---

## Data Change Detection

Script track thay đổi ở mức **từng store + thời gian**:

| Loại thay đổi | Cách detect | Action |
|---------------|-------------|--------|
| Thêm store mới | So sánh set store IDs | ➕ Re-compose |
| Bớt store | So sánh set store IDs | ➖ Re-compose |
| Đổi giờ giao | So sánh gio_den per store | 🔄 Re-compose |
| Không thay đổi | Hash giống nhau | ✓ Skip |

**Log ví dụ khi có thay đổi:**
```
🔀 Changes detected:
  ➕ Thêm: HCM005, HCM012
  ➖ Bớt: HCM003
  🔄 HCM001: 14:30 → 15:00
  🔄 HCM008: 22:00 → 22:30
```

---

## DRY — Lịch kiểm kê (Inventory Check)

Chỉ áp dụng cho **DRY** (cả Sáng và Tối).

**Rule**: Store kiểm kê tổng ngày X → không nhận hàng ngày D (=X) và D-1 (=X-1).

**Source**: [Lịch Kiểm kê 2026](https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/edit?gid=220196646#gid=220196646)
- Sheet "Lịch Kiểm kê 2026", Col D = ID Mart, Col H = Ngày kiểm kê tổng

**Trong email**: Rows trùng được highlight đỏ (`#FF6B6B`, bold) để user review.

---

## Troubleshooting

### Task không chạy
1. Check Task Scheduler: `schtasks /query /tn "AutoComposeMail"`
2. Đảm bảo user đã login (task = Interactive mode)
3. Check log: `output/auto_compose.log`

### Data fetch fail
- Google Sheet/Drive có thể timeout → script tự retry lần sau (15 phút)
- Check internet connection
- Check URL nguồn có thay đổi không

### Compose sai data
- `--reset` rồi `--force {KHO}` để compose lại
- Hoặc chạy manual: `python script/compose_mail.py --kho DRY --session sang --date DD/MM/YYYY`

### Muốn đổi lịch check
- Edit `config/mail_schedule.json` → thay `check_time`, `cutoff_time`
- Không cần restart Task Scheduler (script đọc config mỗi lần chạy)

---

## Paste vào Haraworks

Sau khi auto_compose chạy xong, mail HTML đã sẵn sàng. Để paste vào Haraworks:

```powershell
# 1. Copy HTML vào clipboard (format bảng)
powershell -ExecutionPolicy Bypass -File output\_clip_html.ps1

# 2. Mở Haraworks → vào ô soạn mail (CKEditor)
# 3. Ctrl+A → Ctrl+V
```

> ⚠ **KHÔNG copy trực tiếp từ file .html** — sẽ paste ra raw code.
> Phải dùng `_clip_html.ps1` để copy ở định dạng CF_HTML (clipboard HTML format).

Nếu cần paste cho kho cụ thể (không phải bản compose cuối cùng):
```powershell
# Copy file kho-specific thay vì _mail_body.html
copy output\_mail_DRY_toi_body.html output\_mail_body.html
powershell -ExecutionPolicy Bypass -File output\_clip_html.ps1
```

---

## Run History

| Ngày | Kho | Rows | Composes | Kết quả |
|------|-----|------|----------|---------|
| 02/04/2026 | DRY Tối | 83 | 3x (data thay đổi 2 lần) | ✅ FINAL 13:48, paste OK |

---

## Roadmap

### ✅ Mức 1 (hiện tại — từ 02/04/2026)
- Auto check + compose HTML
- User chạy `_clip_html.ps1` → paste vào Haraworks
- DRY Tối: ✅ verified

### 🔜 Mức 2 (planned)
- Thêm flag `--inject`
- Playwright automation: login → find thread → paste HTML → save draft
- Vẫn KHÔNG auto send
- Target: sau 2-3 ngày Mức 1 ổn định
