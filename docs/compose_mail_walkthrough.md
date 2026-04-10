# Compose Mail — Walkthrough

Tổng hợp quá trình phát triển hệ thống soạn email tự động trên Haraworks.

## Timeline & Conversations

| # | Conversation | Ngày | Mục tiêu | Kết quả |
|---|-------------|------|----------|---------|
| 1 | [03ce9cd3](file:///C:/Users/admin/.gemini/antigravity/brain/03ce9cd3-fa30-4f53-a0ca-056b466972bf) | 30/03/2026 | Khảo sát format 4 loại email | ✅ Tạo `mail_format_summary.md` |
| 2 | [88e4e765](file:///C:/Users/admin/.gemini/antigravity/brain/88e4e765-6efa-41a6-8e57-bdd984fc488d) | 31/03/2026 | Build script + soạn draft mail KRC, DRY | ✅ Tạo `compose_mail.py`, `fetch_weekly_plan.py`, workflow |
| 3 | [3f487fc6](file:///C:/Users/admin/.gemini/antigravity/brain/3f487fc6-4003-4d89-bdaa-c1cd5a740f5b) | 31/03/2026 | Soạn draft DRY Sáng (W14) | ✅ Inject HTML thành công |
| 4 | [607af53b](file:///C:/Users/admin/.gemini/antigravity/brain/607af53b-21d4-46c0-ae9d-773fc1eb044b) | 01/04/2026 | Fix bugs + Inventory check + DRY Tối | ✅ Fix HNNv, date format, HH:MM, kiểm kê |

---

## Files Created/Modified

### Scripts

| File | Purpose | Created in |
|------|---------|-----------|
| [compose_mail.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/compose_mail.py) | Generate HTML email body cho mỗi kho/ngày | Conv #2 |
| [fetch_weekly_plan.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/fetch_weekly_plan.py) | Fetch data cả tuần từ Google Sheets + Drive | Conv #2 |

### Output Files (generated per run)

| File | Purpose |
|------|---------|
| [_mail_body.html](file:///c:/Users/admin/Downloads/transport_daily_report/output/_mail_body.html) | Raw HTML email body |
| [_mail_inject.js](file:///c:/Users/admin/Downloads/transport_daily_report/output/_mail_inject.js) | JS snippet inject vào CKEditor |
| [_mail_preview.html](file:///c:/Users/admin/Downloads/transport_daily_report/output/_mail_preview.html) | Preview page để kiểm tra trước khi inject |
| [_clip_html.ps1](file:///c:/Users/admin/Downloads/transport_daily_report/output/_clip_html.ps1) | PowerShell: copy HTML clipboard format |
| [weekly_plan_W14.json](file:///c:/Users/admin/Downloads/transport_daily_report/output/weekly_plan_W14.json) | Data tuần W14 (150KB, 4 kho) |

### Workflow

| File | Purpose |
|------|---------|
| [compose-mail.md](file:///c:/Users/admin/Downloads/transport_daily_report/.agents/workflows/compose-mail.md) | Workflow `/compose-mail` |

### Artifacts (conversation storage)

| File | Purpose |
|------|---------|
| [mail_format_summary.md](file:///C:/Users/admin/.gemini/antigravity/brain/03ce9cd3-fa30-4f53-a0ca-056b466972bf/mail_format_summary.md) | Format 4 loại email (from Conv #1) |

---

## Phát triển Chi tiết

### Phase 1: Khảo sát Format (Conv #1 — 30/03)

**Mục tiêu:** Login Haraworks, xem format email hiện có của 4 kho.

**Kết quả quan trọng:**
- Login: `SC012433` (Phạm Tú Nhi - Transport Coordinator)
- Xác định 4 loại mail: KRC, DRY, ĐÔNG MÁT, THỊT CÁ
- DRY chia 2 session: Sáng (6h-15h) / Tối (15h-3h sáng)
- ĐÔNG MÁT có thêm cột "Loại hàng" (4 cột thay vì 3)
- Mỗi tuần = 1 thread, ngày mới reply vào thread
- CC list rất dài (Operations, Sales, Delivery, ...)

### Phase 2: Build Scripts (Conv #2 — 31/03 sáng)

**Tạo `fetch_weekly_plan.py`:**
- Fetch KRC (Google Sheets) → col G, H
- Fetch KFM/DRY (Google Sheets) → sheet "DRY", col G, H  
- Fetch KH MEAT/ĐÔNG/MÁT (Google Drive folders) → từng file xlsx theo ngày
- Auto-detect header columns cho time + loại hàng
- Output: `weekly_plan_W{n}.json`

**Tạo `compose_mail.py`:**
- Load JSON → filter ngày + session → sort A→Z → generate HTML
- 4 generator functions: `generate_html_krc`, `generate_html_dry`, `generate_html_dong_mat`, `generate_html_thit_ca`
- Auto-detect week number từ available files
- Output 3 files: HTML, JS inject, preview

**Tạo workflow `/compose-mail`:**
- 4 steps: generate → login → inject → review

### Phase 3: Thực thi (Conv #2 + Conv #3 — 31/03)

**KRC mail W14:** ✅ Compose thành công
- Inject JS vào CKEditor qua browser console
- Add CC bằng thao tác trên org chart popup (rất cực, nhiều bước click)

**DRY Sáng W14:** ✅ Inject thành công
- Reply vào thread "KẾ HOẠCH GIAO HÀNG KHO DRY W14"
- HTML inject qua JS snippet hoạt động tốt

### Phase 4: Bug Fixes + Inventory Check (Conv #4 — 01/04)

**Bug #1 — "HNNv" thay vì "Dear team Siêu Thị":**
- **Root cause:** JS inject cũ dùng `editor.innerHTML = html` bypass CKEditor internal model → text corruption (Unicode đứt đoạn)
- **Fix:** Đổi JS inject sang 3-method cascade: CK5 API `setData()` → CK4 API `setData()` → `innerHTML` fallback

**Bug #2 — Date format mixed (01/04/2026 vs 1/4/2026):**
- **Root cause:** CKEditor auto-parse bare date text → strip leading zeros, row đầu khác format
- **Fix:** Wrap dates trong `<span style="white-space:nowrap">DD/MM/YYYY</span>` + `_normalize_date()` đảm bảo leading zeros

**Feature: Time format HH:MM:**
- **Vấn đề:** Giờ như `0:17` không chỉnh chu, và `9:50` cũng vậy
- **Fix:** `_format_time_hhmm()` — `0:17` → `00:17`, `9:50` → `09:50`
- Áp dụng cho tất cả bảng (KRC, DRY, ĐÔNG MÁT, THỊT CÁ)

**Feature: Inventory check (DRY only):**
- Fetch lịch kiểm kê từ Google Sheets "Lịch Kiểm kê 2026"
- Cross-reference: store ID + ngày kiểm kê tổng (Col D + Col H)
- Rule: store kiểm kê ngày X → flag nếu giao hàng ngày D (=X) hoặc D-1 (=X-1)
- Rows flagged được highlight đỏ (`#FF6B6B`, bold) trong email table
- Test 01/04/2026: PHI flagged (kiểm kê 01/04) nhưng PHI không có lịch giao → logic đúng

**DRY Tối 01/04 W14:** ✅ Soạn draft thành công
- 71 rows, giờ 22:00-00:17
- Paste vào CKEditor qua clipboard (CF_HTML format)
- Greeting đúng, dates đồng nhất, times HH:MM

---

## Vấn đề Gặp Phải & Giải Pháp

### 1. Vietnamese Diacritics

> [!WARNING]
> **Vấn đề:** `browser_press_key` không hỗ trợ tiếng Việt có dấu → gây lỗi "Unknown key"

**Giải pháp:** Sử dụng JS injection thay vì gõ ký tự. Toàn bộ nội dung (greeting + table) được encode thành JSON string trong `_mail_inject.js` rồi inject 1 lần qua `innerHTML`.

### 2. CKEditor Detection

> [!WARNING]
> **Vấn đề:** Haraworks dùng CKEditor nhưng version + selector thay đổi giữa compose/reply mode.

**Giải pháp:** JS snippet thử nhiều selector:
```javascript
// CKEditor 5
document.querySelector('.ck-editor__editable, [role="textbox"][contenteditable="true"]')
// CKEditor 4  
CKEDITOR.instances[0].setData(html)
```
Và set `document.title = 'INJECTED_OK'` để confirm thành công.

### 3. Clipboard HTML Format

> [!WARNING]
> **Vấn đề:** Copy HTML text bình thường → paste vào CKEditor mất format table.

**Giải pháp:** Tạo `_clip_html.ps1` — PowerShell script build CF_HTML clipboard format (với `StartHTML`, `EndHTML`, `StartFragment`, `EndFragment` headers) → paste giữ format table.

### 4. CKEditor Injection — Text Corruption ("HNNv")

> [!CAUTION]
> **Vấn đề:** Dùng `innerHTML` bypass CKEditor model → text corruption, Unicode bị đứt → "Dear team Siêu Thị" thành "HNNv"

**Giải pháp:** Đổi sang 3-method cascade:
1. CKEditor 5 API: `editable.ckeditorInstance.setData(html)`
2. CKEditor 4 API: `CKEDITOR.instances[key].setData(html)`
3. Fallback: `innerHTML` + dispatch `['input','change','keyup']` events

### 5. CKEditor Date Auto-Formatting

> [!WARNING]
> **Vấn đề:** CKEditor tự parse bare date text → "01/04/2026" thành "1/4/2026" ở một số rows, row đầu giữ nguyên

**Giải pháp:** Wrap dates trong `<span style="white-space:nowrap">` để CKEditor không auto-parse. Thêm `_normalize_date()` đảm bảo DD/MM/YYYY với leading zeros.

### 6. CC List rất dài

> [!WARNING]  
> **Vấn đề:** Mỗi mail cần CC ~10+ departments, phải tìm từng cái trong org chart popup.

**Hiện trạng:** Chưa tự động hóa. Vẫn phải thao tác thủ công qua browser subagent (click vào popup, search department, tick checkbox).

### 5. Thread Reply vs New Compose

> [!IMPORTANT]
> **Vấn đề:** Đầu tuần cần compose mail mới (tạo thread mới W{n+1}), các ngày sau reply vào thread cũ.

**Hiện trạng:** Logic chưa tự động. User phải chỉ định compose hay reply.

---

## Hiện trạng (01/04/2026)

### ✅ Hoạt động tốt
- Fetch data từ 5 nguồn → JSON
- Generate HTML email body cho cả 5 loại mail
- CKEditor injection (3-method cascade: CK5 → CK4 → innerHTML)
- Clipboard paste (CF_HTML format) là phương án inject chính
- Preview HTML trước khi inject
- Workflow `/compose-mail` documented
- **Time format HH:MM** (leading zeros)
- **Date format DD/MM/YYYY** với span wrapper chống auto-parse
- **Inventory check** cho DRY (kiểm kê D và D-1, highlight đỏ)

### ✅ Bugs đã fix
- "HNNv" greeting → "Dear team Siêu Thị" (CKEditor API thay innerHTML)
- Mixed date format → consistent DD/MM/YYYY (span wrapper)
- Time `0:17` → `00:17` (HH:MM leading zero)

### ⚠ Cần cải thiện
- CC list: chưa tự động hóa (vẫn thủ công)
- Thread detection: chưa tự động detect compose vs reply
- Error handling: fetch fail → script exit, chưa có retry
- Duplicate store IDs: cùng store nhận nhiều chuyến/ngày → giữ tất cả rows (đúng business logic)

### 🔜 Potential Improvements
1. Auto CC bằng JavaScript inject (tự click org chart, search, tick)
2. Auto detect thread/compose mode từ calendar
3. Batch mode: soạn tất cả 5 mail 1 lần
4. Validation: so sánh data với ngày trước để detect anomalies
5. Email template customization qua config file
