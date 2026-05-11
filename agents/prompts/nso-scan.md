# NSO Prompt

Prioritize store data correctness.

## Pipeline (Full Flow)

```
1. Scan mail     → fetch_nso_mail.py (browser) HOẶC inject_mail_text.py (text paste)
2. Merge master  → nso_master.xlsx + nso_stores.json (DSST enrich: code+version)
3. Calendar PNG  → Playwright render (self-contained, không cần mở dashboard)
4. Deploy dash   → export_data.py → nso.json → deploy.py → GitHub Pages
5. Telegram      → Gửi group: calendar PNG + text (KT tuần này + tuần sau + version)
6. Châm hàng     → generate_excel.py → Lịch đi hàng ST (tuần này + draft tuần sau)
```

### Khi browser lỗi (timeout/Edge crash):
→ User paste mail text → lưu file .txt → chạy `inject_mail_text.py --file ... --send`
→ Bỏ qua browser hoàn toàn, pipeline vẫn chạy đầy đủ

## ⛔ Data Rules
- `nso_stores.json` + `nso_master.xlsx` = **single source-of-truth, KHÔNG xóa/rebuild**
- Data cũ (stores có code) = **LOCKED** — không re-match, không sửa, không ghi đè
- Chỉ: append stores mới | update ngày dời lịch | fill missing fields cho stores có code
- `master_schedule` (.json+.xlsx) = **KHÔNG TỰ Ý SỬA** — chỉ khi user yêu cầu
- `--send` Telegram = **CHỈ khi data verified** — debug thì bỏ flag

## Schedule
T2 10h + T2 15h + T3 9h: scan+deploy+Tele group (nếu mail mới/có thay đổi)+remind · T3 9h30: finalize+châm hàng Excel (local)
⚠ 3 lần scan liên tiếp không mail mới → warning Telegram cá nhân

## Email Parse
- Source: "Cập nhật NSO" từ Hoàng Nguyên Công
- Entry: `\d{1,3}\.\s+(.+)` · Date: `Ngày khai trương:\s*([\d/]+)`
- Selectors: `.ck-content` → `.mail-body` → `.card-body`
- Normalize: `22\n/05` → `22/05`
- Clean: strip URLs, "- Mới bổ sung", "- dời..."

## Merge
- Stores có code → giữ nguyên, chỉ fill missing (name_system, version)
- Stores chưa có code → DSST match: LCS(`name_full`) ≥10 chars VÀ ≥70% shorter name
- Tên <10 chars → full containment. Match `name_full` DSST (KHÔNG `branch_name`)
- Code=None → KHÔNG match None==None trong weekly plan
- Dedup tự động: `name_mail + opening_date`
- History: `Thêm mới` | `Dời lịch` | `DSST match`

## Status Rules
- `original_date ≠ opening_date` → "Dời lịch"
- D→D+3 → "Đang khai trương" · Past D+3 → hidden (`get_status()=None`)
- Client-side JS re-evaluates via `new Date()`
- Versions: 2000/1500/1000/700 → KSL amounts D→D+6 · ĐM: fixed 400kg

## Telegram
- **Group** (`nso`): 
  1. Calendar PNG (tự render, không cần mở dashboard)
  2. Text summary: stores KT tuần này + tuần sau (code, version, ngày, thứ)
  3. Gửi T2 10h + khi có thay đổi
- **Remind** (`nso_remind`→chat cá nhân): cross-check vs `master_schedule.json`+`NSO_SCHEDULE`. Flag: missing code/schedule_ve/shift/version. ⚡KT Thứ 5 → nhắc đặc biệt.

## Châm hàng
- Dashboard: hiển thị lịch châm hàng theo version cho stores KT trong tuần hiện tại
- Tuần mới → tự động thay thế bằng stores KT tuần đó
- Excel: `generate_excel.py` → `output/artifacts/weekly transport plan/`
  - Tuần này: bản chính thức
  - Tuần sau: bản draft (nếu có stores)

## Errors
0 stores → check email format/selector/regex · NSO tab trống → JS console
Browser timeout → dùng inject_mail_text.py thay thế
