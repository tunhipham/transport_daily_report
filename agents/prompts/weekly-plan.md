# Weekly Transport Plan — Agent Context

## Bối cảnh

Dashboard logistics KFM — Tab "📅 Lịch Tuần" hiển thị lịch giao hàng siêu thị theo tuần.

**Flow**: `master_schedule.json` → `generate_excel.py` → Excel W{nn} → `export_weekly_plan.py` → JSON → deploy

**Thursday Cadence**: 12h check → 13h generate + export + save baseline + send review → user confirm → `--deliver`
**Monday Cadence**: 07h→12h monitor → 12h cutoff: re-gen Excel + diff vs Thu + deploy → send summary + draft caption → user confirm → `--deliver`

## Data Source Rules

| Data | Nguồn | Tính chất |
|------|-------|-----------|
| Lịch về/shift | `data/master_schedule.json` + `.xlsx` | 🔒 ONE-SOURCE-OF-TRUTH |
| Lịch kiểm kê | Google Sheets (`INVENTORY_SHEET_URL`) | 🔄 Dynamic — auto-fetch |
| Lịch về hàng | Auto-generate từ master_schedule | 🤖 `generate_excel.py` |
| NSO dates | `data/nso/nso_stores.json` | ➕ Auto từ mail scan |
| NSO schedule | `data/nso/nso_schedule.json` | 🔒 User cung cấp |

> ⛔ **master_schedule (.json + .xlsx) = KHÔNG TỰ Ý SỬA.** Chỉ update khi user yêu cầu. Ngoại lệ tự tính: A112 Cô Giang (even-date), post-châm-hàng skip D+4.

## ⚠️ Date Normalization

```python
# ✅ ĐÚNG — check datetime TRƯỚC date
if isinstance(val, datetime):
    dt = val.date()
elif isinstance(val, date):
    dt = val
```

Áp dụng cho mọi script đọc ngày từ openpyxl/Google Sheets.

## Cấu trúc project

```
data/master_schedule.json           # 🔒 Lịch về/shift
script/
  domains/weekly_plan/
    generate_excel.py               # 🤖 Generate Excel W{nn}
    finalize.py                     # 📋 Thu: --check / --send / --deliver / --test
  domains/nso/generate.py           # NSO STORES list
  dashboard/
    export_weekly_plan.py           # Excel → JSON
    auto_inventory_watch.py         # 🔄 Kiểm kê watch (thứ 2)
    deploy.py                       # Git push → GitHub Pages
  lib/
    sources.py                      # INVENTORY_SHEET_URL
    telegram.py                     # Telegram helpers
output/artifacts/weekly transport plan/  # Excel files
docs/data/weekly_plan.json              # Dashboard JSON
config/telegram.json → "weekly_plan"    # chat_id + group_chat_id
```

## Key Logic

### Kiểm kê
- Kiểm kê ngày D → ghi "Kiểm kê" vào **D** và **D-1** unconditionally
- Không cần check shift/schedule/delivery day

### NSO Châm Hàng
- D→D+3: 4 ngày châm hàng liên tiếp
- D+4: skip nếu trùng delivery day (giảm tải), không skip nếu đã có gap tự nhiên
- NSO dời lịch (`original_date`): bỏ tuần cũ, chỉ tính tuần mới
- Inject missing: NSO có opening trong tuần nhưng thiếu row → inject tự động

### A112 Cô Giang
- `schedule_ve: "Ngày chẵn"` → về hàng ngày chẵn (2,4,6,8...), trừ CN
- `compute_even_date_schedule()` tính dynamic theo tuần

### Đếm Stats
- **Ngày/Đêm**: theo field `shift` (độc lập)
- **Châm hàng/Kiểm kê**: theo `days[]` (độc lập)
- Store có thể vừa Đêm vừa Châm hàng → đếm cả hai

### Code Corrections
- `CODE_CORRECTIONS` dict sửa code sai (vd: A179 → A176 Sunrise Riverside)
- `_name_matches()` check 50% từ khớp — tránh false positive trùng code

## Thursday Finalize (Thứ 5 — tạo lịch W+1)

Script: `script/domains/weekly_plan/finalize.py`

| Mode | Schedule | Target |
|------|----------|--------|
| `--check` | Thu 12:00 (auto) | Telegram cá nhân — data status |
| `--send` | Thu 13:00 (auto) | Generate + export + save baseline + Telegram review |
| `--deliver` | **Manual** (user confirm) | Group SCM - NCP — file Excel final |
| `--test` | Manual | Telegram cá nhân — test send |

> [!NOTE]
> `--send` lưu **Thursday baseline** (`output/state/thursday_baseline_W{nn}.json`) để Monday diff.

## Monday Kiểm Kê Refresh (Thứ 2 — update lịch tuần hiện tại)

Script: `script/dashboard/auto_inventory_watch.py`

| Giờ | Action |
|-----|--------|
| 07:00→11:00 | Monitor kiểm kê mỗi 1h (log only, không deploy) |
| 12:00 cutoff | Re-generate Excel W → export JSON → deploy dashboard |
| 12:00 | Diff vs Thursday baseline: shift + kiểm kê + lịch giao (246/357) |
| 12:00 | Gửi Telegram: summary + file Excel + draft caption gửi group |
| User confirm | `--deliver`: gửi group SCM-NCP với caption đã duyệt |

Thursday baseline: `output/state/thursday_baseline_W{nn}.json`
- Lưu tự động khi `finalize.py --send` (thứ 5)
- Chứa snapshot tất cả stores: shift, inventory_date, days

| Mode | Mô tả |
|------|-------|
| `--watch` | Watch mode: monitor → cutoff 12h full pipeline |
| `--backup` | One-shot full pipeline (bất kỳ ngày) |
| `--deliver` | Gửi Excel cập nhật vào group SCM-NCP |

Config: `config/telegram.json` → key `weekly_plan`
- `chat_id: 5782090339` (personal)
- `group_chat_id: -4702773130` (SCM - NCP)

## Diff Rules (Monday caption)
- Chỉ ghi **code** store (A176, LPM...) — không ghi tên dài
- Nếu days đổi do kiểm kê → gộp vào kiểm kê, không ghi riêng "đổi lịch giao"
- Chỉ report kiểm kê **trong tuần W hiện tại** (bỏ ngoài tuần)
- Telegram gửi kèm **draft caption** để user duyệt trước khi gửi group

## Formatting Rules
- Số: dùng dấu "," | Ngày: dd/mm/yyyy | Vietnamese diacritics: giữ nguyên
- KHÔNG viết tắt trong report

