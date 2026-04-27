# NSO (New Store Opening) — Prompt

Prioritize correctness of store data over completeness of parsing explanation.

## Overview

NSO pipeline quét email "Cập nhật NSO" trên Haraworks, merge dữ liệu store mới vào master Excel, deploy lên dashboard.

---

## Automated Timeline

```
THỨ 2:
  10:00  scan    → Scan mail → deploy dashboard → Telegram group (KT tuần này + sau)
                  → Remind cá nhân (NSO thiếu info trong master_schedule)
  15:00  track   → Re-scan → chỉ deploy + notify nếu có thay đổi

THỨ 3:
  09:00  scan    → Scan cuối → deploy → Telegram group (nếu thay đổi)
  09:30  finalize → Export + deploy + generate châm hàng Excel (local only)
```

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
                       ↓
             nso_remind.py → cross-check vs master_schedule → personal Telegram
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

## Telegram

### Group (NSO summary) — Thứ 2 10h + Thứ 3 9h (nếu thay đổi)
- Flow: Xóa tin cũ → screenshot calendar → gửi ảnh → gửi dashboard HTML kèm caption
- Caption: Tổng active + TUẦN NÀY + TUẦN SAU
- Config: `config/telegram.json` → `nso` domain
- State: `output/state/nso/sent_messages.json`

### Personal Remind — Thứ 2 10h
- Cross-check NSO tuần này + tuần sau vs `master_schedule.json` + `NSO_SCHEDULE`
- Flag: missing code, missing schedule_ve, missing shift, missing version
- ⚡ NSO khai trương Thứ 5 → nhắc đặc biệt (cần lịch tuần trước Thứ 5)
- Config: `config/telegram.json` → `nso_remind` domain (chat cá nhân)

## Châm hàng (Thứ 3 09:30 — local only)
- `generate_excel.py` tạo Excel lịch đi hàng có châm hàng NSO
- KHÔNG gửi Telegram cho châm hàng
- Output: `output/artifacts/weekly transport plan/Lịch đi hàng ST W{nn}.xlsx`

---

## Khi lỗi

Script lỗi hoặc parsed 0 stores → kiểm tra email format, selector chain, date regex.
Check JS console nếu dashboard tab NSO trống.
