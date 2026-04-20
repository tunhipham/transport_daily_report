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
- Scanner runs **Mon/Tue only** (auto). Use `--force` to override
- Stores with `original_date ≠ opening_date` → status "Dời lịch"
- Stores within 7 days → status "Đang khai trương"
- Version rules: 2000/1500/1000/700 → different KSL amounts (D→D+6)
- ĐÔNG MÁT: fixed 400kg for every version

## Commands
```powershell
# Scan + deploy
python -u script/domains/nso/fetch_nso_mail.py --force

# Dry run
python -u script/domains/nso/fetch_nso_mail.py --force --dry-run

# Refresh DSST cache
python -u script/domains/nso/_save_dsst.py

# Export + deploy dashboard only
python -u script/dashboard/deploy.py --domain nso

# Generate HTML dashboard + Excel
python -u script/domains/nso/generate.py
```
