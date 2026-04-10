# Compose Mail — Implementation Plan

Tự động hóa việc soạn email kế hoạch giao hàng hàng ngày cho 4 kho (5 mail) trên hệ thống Haraworks Internal Mail (Kingfoodmart).

## Background

Mỗi ngày, Transport Coordinator (SC012433 - Phạm Tú Nhi) phải gửi email kế hoạch giao hàng cho các stores qua Haraworks internal mail. Có 4 kho, tạo ra 5 emails/ngày:

| # | Kho | Mail | Ngày giao |
|---|-----|------|-----------|
| 1 | KRC | 1 mail/ngày | D+1 |
| 2 | DRY (KSL) | 2 mail: Sáng + Tối | D+1 sáng, D tối |
| 3 | ĐÔNG MÁT | 1 mail/ngày | D+1 |
| 4 | THỊT CÁ | 1 mail/ngày | D+1 |

---

## Architecture Overview

```mermaid
flowchart LR
    A[Google Sheets<br/>KRC + KFM] --> B[fetch_weekly_plan.py]
    C[Google Drive<br/>KH MEAT/ĐÔNG/MÁT] --> B
    B --> D[weekly_plan_W{n}.json]
    D --> E[compose_mail.py]
    E --> F[_mail_body.html]
    E --> G[_mail_inject.js]
    E --> H[_mail_preview.html]
    G --> I[Browser Console<br/>Haraworks CKEditor]
```

### 3 Giai đoạn

1. **Fetch Data** → `fetch_weekly_plan.py` tải data cả tuần 1 lần
2. **Generate HTML** → `compose_mail.py` tạo HTML email cho từng kho/ngày
3. **Inject vào Editor** → JS snippet inject HTML vào CKEditor trên Haraworks

---

## Proposed Changes

### Data Layer

#### [EXISTING] [fetch_weekly_plan.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/fetch_weekly_plan.py)

Fetch data từ 5 nguồn, output JSON cho cả tuần:

| Source | Type | URL/Location |
|--------|------|-------------|
| KRC | Google Sheets | Sheet "KRC", col G=điểm đến, col H=giờ đến |
| KFM/DRY | Google Sheets | Sheet chứa "DRY", col G+H |
| KH MEAT | Google Drive folder | File `.xlsx` theo ngày (DD.MM.YYYY) |
| KH ĐÔNG | Google Drive folder | File `.xlsx` + cột loại hàng |
| KH MÁT | Google Drive folder | File `.xlsx` + cột loại hàng |

**Usage:**
```bash
python script/fetch_weekly_plan.py --week W14 --start 30/03/2026
```

**Output:** `output/weekly_plan_W14.json`
```json
{
  "week": "W14",
  "start": "30/03/2026",
  "end": "05/04/2026",
  "data": {
    "KRC": [{"date": "01/04/2026", "diem_den": "A115", "gio_den": "3:05"}],
    "DRY": [{"date": "01/04/2026", "diem_den": "A101", "gio_den": "9:50"}],
    "ĐÔNG MÁT": [{"date": "...", "diem_den": "...", "gio_den": "...", "loai_hang": "ĐÔNG"}],
    "THỊT CÁ": [{"date": "...", "diem_den": "...", "gio_den": "..."}]
  }
}
```

---

### Email Generation Layer

#### [EXISTING] [compose_mail.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/compose_mail.py)

Đọc JSON → filter theo ngày/session → sort A→Z → generate HTML email body.

**Usage:**
```bash
# KRC
python script/compose_mail.py --kho KRC --date 01/04/2026

# DRY Sáng (giờ 6h-14h59)
python script/compose_mail.py --kho DRY --session sang --date 01/04/2026

# DRY Tối (giờ 15h-2h59 sáng hôm sau)
python script/compose_mail.py --kho DRY --session toi --date 31/03/2026

# ĐÔNG MÁT (có thêm cột loại hàng)
python script/compose_mail.py --kho "ĐÔNG MÁT" --date 01/04/2026

# THỊT CÁ
python script/compose_mail.py --kho "THỊT CÁ" --date 01/04/2026
```

**Outputs:**
- `output/_mail_body.html` — Raw HTML (clipboard)
- `output/_mail_inject.js` — JS snippet cho browser console
- `output/_mail_preview.html` — Preview page (mở local để kiểm tra trước khi inject)

---

### Email Format Details

#### 1. KRC
- **Subject:** `KẾ HOẠCH GIAO HÀNG KRC W{week}`
- **Greeting:** "Dear team ST, SCM gửi thông tin kế hoạch giao hàng KHO RCQ ngày {date}."
- **Table:** 3 cột

| Ngày | Điểm đến | Giờ đến dự kiến (+-30') |
|------|----------|------------------------|

#### 2. DRY Sáng
- **Subject:** `KẾ HOẠCH GIAO HÀNG KHO DRY W{week}`
- **Greeting:** "Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng DC Dry Sáng {date}."
- **Table:** 3 cột (header: "Ngày giao hàng")

| Ngày giao hàng | Điểm đến | Giờ đến dự kiến (+-30') |
|----------------|----------|------------------------|

#### 3. DRY Tối
- **Reply** trong thread DRY
- **Greeting:** "...DC Dry Tối {date}."
- **Table:** Giống DRY Sáng

#### 4. ĐÔNG MÁT
- **Subject:** `KẾ HOẠCH GIAO HÀNG KHO ĐÔNG MÁT W{week}`
- **Greeting:** "Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng Đông Mát ngày {date}."
- **Table:** **4 cột** (có thêm Loại hàng)

| Ngày | Điểm đến | Giờ đến dự kiến (+-30') | Loại hàng |
|------|----------|------------------------|-----------|

#### 5. THỊT CÁ
- **Subject:** `KẾ HOẠCH GIAO HÀNG KHO ABA THỊT CÁ W{week}`
- **Greeting:** "Dear team Siêu Thị, SCM gửi thông tin kế hoạch giao hàng Thịt Cá ngày {date}."
- **Table:** 3 cột

---

### HTML Table Styling
- Header: `background:#4472C4; color:white; font-weight:bold`
- Striped rows: Even rows `background:#D9E2F3`
- **Red highlight**: `background:#FF6B6B; font-weight:bold` — rows trùng lịch kiểm kê
- Border: `1px solid #000`
- Font: `Arial, sans-serif; font-size:12px`
- Cell padding: `4px 8px`

### Date & Time Formatting
- **Date**: DD/MM/YYYY (leading zeros) — wrapped in `<span style="white-space:nowrap">` để CKEditor không auto-parse
- **Time**: HH:MM (leading zeros) — `0:17` → `00:17`, `9:50` → `09:50`
- Helper functions: `_normalize_date()`, `_safe_date()`, `_format_time_hhmm()`

### Inventory Check (DRY only)

> [!IMPORTANT]
> Chỉ áp dụng cho kho DRY. Kiểm tra lịch giao hàng vs lịch kiểm kê tổng.

**Source:** [Lịch kiểm kê năm 2026](https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/edit?gid=220196646#gid=220196646)
- Sheet: "Lịch Kiểm kê 2026", Header row 9
- Col D: `ID Mart` (store ID)
- Col H: `Ngày kiểm kê tổng 2026` (datetime)

**Rule:** Siêu thị có lịch kiểm kê ngày X → không nhận hàng ngày **D** (=X) và **D-1** (=X-1).

**Logic trong `compose_mail.py`:**
1. `fetch_inventory_schedule()` — download xlsx, parse Col D + Col H → dict `store_id → datetime`
2. `get_inventory_flagged_stores(inventory, delivery_date)` — trả về set store IDs cần flag
3. `_make_table(..., flagged_stores=set)` — rows flagged được highlight đỏ

---

### Injection Layer

#### [EXISTING] [_mail_inject.js](file:///c:/Users/admin/Downloads/transport_daily_report/output/_mail_inject.js)

JS snippet inject HTML vào CKEditor (3-method cascade):
1. **CKEditor 5 API**: `editable.ckeditorInstance.setData(html)` — ưu tiên cao nhất
2. **CKEditor 4 API**: `CKEDITOR.instances[key].setData(html)` — fallback
3. **innerHTML**: `editable.innerHTML = html` + dispatch events — last resort
4. Set `document.title = 'INJECTED_OK'` để confirm

> [!TIP]
> Dùng CKEditor API (`setData`) thay vì `innerHTML` để tránh text corruption (bug "HNNv") và date auto-formatting.

#### [EXISTING] [_clip_html.ps1](file:///c:/Users/admin/Downloads/transport_daily_report/output/_clip_html.ps1)

PowerShell script copy HTML vào clipboard đúng format CF_HTML (clipboard format) — giữ table formatting khi paste.

#### [EXISTING] [_mail_preview.html](file:///c:/Users/admin/Downloads/transport_daily_report/output/_mail_preview.html)

Page preview hiện nội dung email, có thể Ctrl+A → Ctrl+C copy thủ công.

---

### Workflow File

#### [EXISTING] [compose-mail.md](file:///c:/Users/admin/Downloads/transport_daily_report/.agents/workflows/compose-mail.md)

Workflow `/compose-mail` với các bước:
1. Generate HTML email body (turbo)
2. Open Haraworks, login SC012433
3. Inject HTML vào CKEditor
4. Review draft → screenshot → user confirm

---

## CC List (chung cho tất cả kho)

Operations, Operations Training & Development, Operations Excellence, Sales, Delivery, Delivery 1, Regional Sales 1, HCM 001, Đối Tác Seedlog, DC Seedlog (chỉ cho DRY)

## Business Rules

> [!IMPORTANT]
> 1. **D+1**: Mail mỗi kho là lịch giao hàng cho ngày mai (trừ DRY Tối = chiều/đêm cùng ngày)
> 2. **DRY chia 2 session**: Sáng (6h-14h59), Tối (15h-2h59 sáng hôm sau)
> 3. **1 thread/tuần**: W14, W15... mỗi tuần dùng 1 email thread, ngày mới reply vào thread đó
> 4. **Sort A→Z**: Store ID (điểm đến) luôn alphabetical
> 5. **Chỉ DRAFT**: Không bấm gửi cho tới khi user confirm
> 6. **Kiểm kê (DRY only)**: Stores có lịch kiểm kê tổng → không nhận hàng ngày D và D-1 → highlight đỏ nếu vẫn có lịch giao
> 7. **Time format**: Giờ luôn HH:MM (leading zero)

## Open Questions

> [!WARNING]
> Các vấn đề cần giải quyết trong tương lai:
> 1. **Auto CC**: CC list hiện tại phải add thủ công qua org chart popup trên Haraworks — rất cực. Có cần tự động hóa bước này?
> 2. **Reply vs Compose mới**: Đầu tuần cần compose mail mới (tạo thread), các ngày sau cần reply vào thread đó. Logic detect tự động?
> 3. **Error handling**: Nếu fetch data từ Google Drive fail 1 ngày thì sao? Skip hay retry?
> 4. **Duplicate detection**: Store ID trùng (cùng store nhận 2 chuyến/ngày) — giữ nguyên hay merge?

## Verification Plan

### Automated Tests
- Run `compose_mail.py` với mỗi kho → check output files tồn tại
- Verify HTML valid (có `<table>`, `<thead>`, rows khớp số lượng data)
- Check sort order A→Z

### Manual Verification
- Mở `_mail_preview.html` trong browser → kiểm tra format table
- Inject vào Haraworks → screenshot cho user confirm trước khi gửi
