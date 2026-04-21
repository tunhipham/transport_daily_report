# NSO (New Store Opening) — Agent Prompt

## Overview
NSO pipeline quét email "Cập nhật NSO" trên Haraworks, merge dữ liệu store mới vào master Excel, và deploy lên dashboard.

## Architecture

### Data Sources
- **Haraworks Mail**: Email "Cập nhật NSO" từ Hoàng Nguyên Công hoặc fwd từ Ms. Giang
- **DSST Google Sheet**: Master store metadata (code, version, name_system)
- **Master Excel**: `data/nso/nso_master.xlsx` — Single source of truth

### Key Files
| File | Mô tả |
|------|--------|
| `script/domains/nso/fetch_nso_mail.py` | Main scanner: browser → parse → merge |
| `script/domains/nso/nso_master.py` | NsoMaster class: Excel read/write + history |
| `script/domains/nso/_save_dsst.py` | Refresh DSST cache from Google Sheet |
| `script/domains/nso/generate.py` | Generate HTML dashboard + Excel exports |
| `script/dashboard/export_data.py` | Export NSO JSON for dashboard |
| `data/nso/nso_master.xlsx` | 🗃️ Master data (Stores + History sheets) |
| `data/nso/.last_mail_url` | 📌 Last processed mail URL (dedup state) |
| `data/dsst_cache.json` | 📦 DSST store lookup cache |

### Output Files
| File | Mô tả |
|------|--------|
| `output/nso/nso_master.xlsx` | Copy of master for review |
| `output/nso/nso.json` | Dashboard JSON (intermediate) |
| `output/nso/scan_summary.txt` | Scan result summary |
| `docs/data/nso.json` | Dashboard data (deployed) |

## Email Parsing Rules

### Supported Formats
1. **Forwarded mail** (Ms. Giang): HTML table with `#stt | name | date` format
2. **Direct mail** (Hoàng Nguyên Công): Text format with numbered entries

### Text Parsing
```
164. Chung cư Opal Boulevard
Ngày khai trương: 23/04/2026 - Thứ 5
```
- Entry pattern: `\d{1,3}\.\s+(.+)`
- Date pattern: `Ngày khai trương:\s*([\d/]+)`
- Date normalization: `22\n/05/2026` → `22/05/2026`

### Content Selectors (fallback chain)
1. `.ck-content` (CKEditor — forwarded mails)
2. `.mail-body` (direct mails)
3. `.card-body` (fallback)

## Merge Logic

### Store Matching
1. **Exact code match**: store.code == mail.code
2. **Name fuzzy match**: keyword overlap ≥ 2 significant words
3. **DSST enrichment**: fuzzy match mail name → DSST branch_name → fill code + version

### Change Tracking
NsoMaster logs every change to History sheet:
- `Thêm mới`: New store added
- `Dời lịch`: Opening date changed
- `DSST match`: Code assigned via fuzzy matching
- `Update {field}`: Manual field update

## Business Rules
- Scanner runs **Thứ 2 + Thứ 3 only** (auto). Use `--force` to override
- **Dedup**: Track last mail URL in `data/nso/.last_mail_url` — skip if same
- `--force` bypasses both weekday check AND dedup
- Stores with `original_date ≠ opening_date` → status "Dời lịch"
- Stores within D→D+3 → status "Đang khai trương"
- **Stores past D+3 auto-hidden** — Python `get_status()` returns `None` khi `delta > 3`
- **Client-side D+3 filter** — Dashboard JS tự filter real-time bằng `new Date()`, dù `nso.json` stale vẫn hiển thị đúng
- Version rules: 2000/1500/1000/700 → different KSL amounts (D→D+6)
- ĐÔNG MÁT: fixed 400kg for every version

## Telegram Notification (Thứ 3)
- **Trigger**: `auto_nso_watch.bat` detects `DayOfWeek == Tuesday` → `generate.py --send-telegram`
- **Config**: `config/telegram.json` → `nso` domain (bot_token + chat_id)
- **Flow**: Xóa tin cũ → screenshot calendar → gửi ảnh → gửi dashboard HTML kèm caption
- **Caption**: Tổng active stores + TUẦN NÀY (stores khai trương) + TUẦN SAU (stores khai trương)
- **State**: `output/state/nso/sent_messages.json` — track message IDs để xóa tin cũ

## Commands
```powershell
# Auto mode (Thứ 2+3, skip mail cũ)
python -u script/domains/nso/fetch_nso_mail.py

# Force mode (bypass weekday + dedup)
python -u script/domains/nso/fetch_nso_mail.py --force

# Dry run
python -u script/domains/nso/fetch_nso_mail.py --force --dry-run

# Refresh DSST cache
python -u script/domains/nso/_save_dsst.py

# Export + deploy dashboard only
python -u script/dashboard/deploy.py --domain nso

# Generate HTML dashboard + Excel
python -u script/domains/nso/generate.py

# Generate + send Telegram notification (thủ công)
python -u script/domains/nso/generate.py --send-telegram
```
