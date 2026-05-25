# NSO Prompt

Prioritize store data correctness.

## Pipeline

```
1. User paste mail text → agent lưu file .txt
2. Parse + merge  → nso_stores.json + nso_master.xlsx (DSST enrich: code+version)
3. Deploy dash    → export_data.py --domain nso → deploy.py → GitHub Pages
4. Excel          → export_excel.py (Lich_Khai_Truong_NSO.xlsx)
5. Châm hàng      → generate_excel.py (tuần này + tuần sau)
6. Telegram       → Gửi cá nhân (nso_remind) → user review OK → gửi group (nso)
```

⚠ User copy-paste nội dung mail trực tiếp, KHÔNG scan browser.

## ⛔ Data Rules
- `nso_stores.json` + `nso_master.xlsx` = **single source-of-truth, KHÔNG xóa/rebuild**
- Data cũ (stores có code) = **LOCKED** — không re-match, không sửa, không ghi đè
- Chỉ: append stores mới | update ngày dời lịch | fill missing fields cho stores có code
- `master_schedule` (.json+.xlsx) = **KHÔNG TỰ Ý SỬA** — chỉ khi user yêu cầu

## Email Parse
- Source: "Cập nhật NSO" từ Hoàng Nguyên Công
- Entry: `\d{1,3}\.\s+(.+)` · Date: `Ngày khai trương:\s*([\d/]+)`
- Normalize: `22\n/05` → `22/05`
- Clean: strip URLs, "- Mới bổ sung", "- dời..."

## Merge
- Stores có code → **LOCKED** — giữ nguyên, chỉ fill missing (name_system, version)
- Stores chưa có code → DSST match: LCS(`name_full`) ≥10 chars VÀ ≥70% shorter name
- **NKT cross-check**: khi match DSST, NKT (ngày khai trương) từ DSST **PHẢI** khớp `opening_date` store → mới map code
  - Cùng địa chỉ nhưng NKT khác → store **KHÁC** (cũ vs mới), KHÔNG map code cũ
  - VD: DSST A107 có NKT 01/03/2026, store mới có opening 29/05/2026 → SKIP, không map A107
- Tên <10 chars → full containment. Match `name_full` DSST (KHÔNG `branch_name`)
- Code=None → KHÔNG match None==None trong weekly plan
- Dedup tự động: `name_mail + opening_date`

## Status Rules
- D→D+3 → "Đang khai trương" · Past D+3 → "Đã khai trương" (dashboard: mờ trắng)
- Versions: 2000/1500/1000/700 → KSL amounts D→D+6 · ĐM: fixed 400kg

## Telegram
- **Flow**: Gửi `nso_remind` (cá nhân) TRƯỚC → chờ user xác nhận → gửi `nso` (group)
  1. Calendar PNG (Playwright render)
  2. Text summary: stores KT tuần này + tuần sau (code, version, ngày, thứ)
- **Remind daily** (`nso_remind`): giữ nguyên — cross-check `master_schedule`+`NSO_SCHEDULE`. Flag missing code/schedule_ve/shift/version. ⚡KT Thứ 5 → nhắc đặc biệt.

## Châm hàng
- Excel: `generate_excel.py` → tuần này (chính thức) + tuần sau (draft)
- Archive: `export_excel.py` → `Lich_Khai_Truong_NSO.xlsx` (tất cả stores)
- Dashboard: nút "📥 Xuất Excel" trên bảng lịch KT

## Errors
0 stores → check email format/regex · NSO tab → JS console
