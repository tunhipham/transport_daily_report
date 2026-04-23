# NSO (New Store Opening) — Prompt

Prioritize correctness of store data over completeness of parsing explanation.

## Overview

NSO pipeline quét email "Cập nhật NSO" trên Haraworks, merge dữ liệu store mới vào master Excel, deploy lên dashboard.

---

## Data Flow

```
_save_dsst.py → data/dsst_cache.json (DSST store lookup)
                       ↓
fetch_nso_mail.py → Haraworks mail → parse → NsoMaster.merge_mail()
                       ↓
             data/nso/nso_master.xlsx (Stores + History)
                       ↓
             export_data.py → docs/data/nso.json
                       ↓
             deploy.py → GitHub Pages
```

## Email Parsing Rules

### Source
Email "Cập nhật NSO" từ Hoàng Nguyên Công — text numbered entries.

### Patterns
- Entry: `\d{1,3}\.\s+(.+)`
- Date: `Ngày khai trương:\s*([\d/]+)`
- Normalize: `22\n/05/2026` → `22/05/2026`

### Content Selectors (fallback chain)
1. `.ck-content` (CKEditor — forwarded)
2. `.mail-body` (direct)
3. `.card-body` (fallback)

## Merge Logic

- **Exact code match**: store.code == mail.code
- **Name fuzzy match**: keyword overlap ≥ 2 significant words
- **DSST enrichment**: fuzzy match → fill code + version

### Change Tracking (History sheet)
`Thêm mới` | `Dời lịch` | `DSST match` | `Update {field}`

## Business Rules

- Stores with `original_date ≠ opening_date` → status "Dời lịch"
- Stores within D→D+3 → status "Đang khai trương"
- **Past D+3 → auto-hidden** (Python `get_status()` returns `None`)
- **Client-side D+3 filter**: Dashboard JS tự filter real-time bằng `new Date()`
- Version rules: 2000/1500/1000/700 → different KSL amounts (D→D+6)
- ĐÔNG MÁT: fixed 400kg for every version

## Telegram (Thứ 3 auto)

- Trigger: `auto_nso_watch.bat` detects Tuesday → `generate.py --send-telegram`
- Flow: Xóa tin cũ → screenshot calendar → gửi ảnh → gửi dashboard HTML kèm caption
- Caption: Tổng active + TUẦN NÀY + TUẦN SAU
- Config: `config/telegram.json` → `nso` domain
- State: `output/state/nso/sent_messages.json`

---

## Khi lỗi

Script lỗi hoặc parsed 0 stores → kiểm tra email format, selector chain, date regex.
Check JS console nếu dashboard tab NSO trống.
