# Weekly Plan Automation — Implementation Plan

## Mục tiêu

Tự động hóa quy trình tạo lịch tuần (weekly transport plan) theo 2 phase:
- **T3 (sau NSO scan)**: Auto-kickoff draft lịch W+1
- **T5 (trước 14:00)**: Auto-finalize + deploy + notify team

Đồng thời tổ chức lại structure cho weekly_plan domain.

---

## User Review Required

> [!IMPORTANT]
> **Move script có risk**: `export_weekly_plan.py` đang được import bởi `auto_inventory_watch.py` (gián tiếp qua subprocess). Move sẽ cần update path trong `auto_inventory_watch.py` và `deploy.py`.

> [!WARNING]
> **T3 auto-kickoff chỉ hoạt động nếu đã có file Excel `Lịch đi hàng ST W{nn}.xlsx`** cho tuần W+1. Nếu chưa có file → script sẽ skip (safe, không crash).

---

## Proposed Changes

### Phase 1: Reorganize scripts

#### [NEW] `script/domains/weekly_plan/` folder

Tạo domain folder mới, move + wrap scripts:

#### [NEW] [export.py](file:///g:/My%20Drive/DOCS/transport_daily_report/script/domains/weekly_plan/export.py)
- Wrapper import existing `export_weekly_plan.py` logic hoặc **move file** trực tiếp
- Giữ nguyên tất cả logic hiện tại (NSO châm hàng, kiểm kê, A112)

#### [MODIFY] [auto_inventory_watch.py](file:///g:/My%20Drive/DOCS/transport_daily_report/script/dashboard/auto_inventory_watch.py)
- Update L282: path trỏ tới `script/domains/weekly_plan/export.py` thay vì `script/dashboard/export_weekly_plan.py`

#### [MODIFY] [deploy.py](file:///g:/My%20Drive/DOCS/transport_daily_report/script/dashboard/deploy.py)
- Nếu deploy.py trỏ trực tiếp tới `export_weekly_plan.py` → update path

---

### Phase 2: Auto-weekly script

#### [NEW] [auto_weekly.py](file:///g:/My%20Drive/DOCS/transport_daily_report/script/domains/weekly_plan/auto_weekly.py)

Script chính cho automation, 2 mode:

**Mode 1: `--kickoff` (T3 sau NSO scan)**
```
auto_nso_watch.bat xong
  → auto_weekly.py --kickoff
    → Check hôm nay có phải T3? (hoặc --force)
    → Tìm file Excel W+1 mới nhất
    → export_weekly_plan.py (fetch kiểm kê + NSO)
    → deploy --domain weekly_plan
    → Telegram notify: "📅 Draft lịch W{nn} đã cập nhật"
```

**Mode 2: `--finalize` (T5 trước 14:00)**
```
Task Scheduler trigger T5 12:00
  → auto_weekly.py --finalize
    → Watch mode: poll mỗi 30 min (12:00 → 13:30)
    → Mỗi cycle: re-fetch kiểm kê + re-export + diff
    → 13:30: final export + deploy
    → Telegram notify: "📅 Lịch W{nn} FINAL — ready for review"
    → Stop
```

**Flags:**
- `--force`: bỏ qua check ngày trong tuần
- `--dry-run`: check only, không deploy/notify
- `--week W15`: force tuần cụ thể

**Pattern theo**: `auto_inventory_watch.py` (lock file, logging, Telegram cleanup, state tracking)

#### [NEW] [auto_weekly.bat](file:///g:/My%20Drive/DOCS/transport_daily_report/script/domains/weekly_plan/auto_weekly.bat)

Task Scheduler launcher, 2 entries:
- T5 12:00: `python auto_weekly.py --finalize`

#### [MODIFY] [auto_nso_watch.bat](file:///g:/My%20Drive/DOCS/transport_daily_report/script/domains/nso/auto_nso_watch.bat)

Thêm Step 3: sau NSO scan + generate → trigger weekly plan kickoff:
```bat
REM Step 3: Kickoff weekly plan draft (Tuesday only)
if "%DOW%"=="Tuesday" (
    python script/domains/weekly_plan/auto_weekly.py --kickoff
)
```

---

### Phase 3: Update workflow + prompt

#### [MODIFY] [weekly-plan.md](file:///g:/My%20Drive/DOCS/transport_daily_report/.agents/workflows/weekly-plan.md)

Trim 215 → ~65 lines. Thêm auto commands, bỏ duplicate NSO logic (đã có trong prompt).

#### [MODIFY] [weekly-plan.md](file:///g:/My%20Drive/DOCS/transport_daily_report/agents/prompts/weekly-plan.md)

Trim 183 → ~80 lines. Giữ: NSO rules, kiểm kê logic, Excel format. Bỏ: auto_inventory_watch details (move vào workflow).

---

## Tóm tắt files

| Action | File | Ghi chú |
|--------|------|---------|
| NEW | `script/domains/weekly_plan/export.py` | Move từ dashboard/ |
| NEW | `script/domains/weekly_plan/auto_weekly.py` | Automation: kickoff + finalize |
| NEW | `script/domains/weekly_plan/auto_weekly.bat` | Task Scheduler launcher |
| MODIFY | `script/domains/nso/auto_nso_watch.bat` | Thêm T3 kickoff trigger |
| MODIFY | `script/dashboard/auto_inventory_watch.py` | Update export path |
| MODIFY | `script/dashboard/deploy.py` | Update export path (nếu cần) |
| DELETE | `script/dashboard/export_weekly_plan.py` | Replaced by domain version |
| MODIFY | `.agents/workflows/weekly-plan.md` | Trim + thêm auto commands |
| MODIFY | `agents/prompts/weekly-plan.md` | Trim + organize |

---

## Task Scheduler Setup

| Task | Trigger | Command |
|------|---------|---------|
| `KFM_WeeklyPlanFinalize` (NEW) | T5 12:00 | `auto_weekly.bat --finalize` |
| `KFM_NsoScan` (existing) | T2+T3 09:00 | `auto_nso_watch.bat` (đã có kickoff trigger) |
| `KFM_InventoryWatch` (existing) | T2 07:00 | Không đổi |

---

## Verification Plan

### Automated
```powershell
# 1. Test export sau khi move script
python -u script/domains/weekly_plan/export.py
# Expected: weekly_plan.json updated, no import errors

# 2. Test auto_inventory_watch vẫn hoạt động
python -u script/dashboard/auto_inventory_watch.py --backup --dry-run
# Expected: no path errors, diff output OK

# 3. Test kickoff mode
python -u script/domains/weekly_plan/auto_weekly.py --kickoff --force --dry-run
# Expected: finds Excel W+1, logs "Draft ready"

# 4. Test finalize mode
python -u script/domains/weekly_plan/auto_weekly.py --finalize --force --dry-run
# Expected: logs finalize flow without deploying
```

### Manual
- User chạy `python -u script/domains/weekly_plan/auto_weekly.py --kickoff --force` → check dashboard tab Lịch Tuần updated
- User confirm Telegram notification format đúng
- User test T5 flow: chạy `--finalize --force` → check final deploy
