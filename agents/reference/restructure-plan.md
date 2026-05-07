# 🔄 Restructure Plan — Dual-Mode Architecture

> **Mục tiêu**: Tái cấu trúc project để vận hành được **cả 2 mode**:
> - 🤖 **Có Antigravity** → slash commands, AI orchestration
> - 👤 **Không có AI** → bat files, Metabase, manual run

---

## Phase 1: Restructure + Manual Source (LÀM TRƯỚC)

> [!IMPORTANT]
> Chỉ đổi cấu trúc folder + tạo tools. **KHÔNG đổi data source** — vẫn dùng Google Sheets/Drive như hiện tại.

### 1.1 Cấu trúc thư mục mới

```
transport_daily_report/
│
├── .agents/workflows/              ← Entry points (slash commands) — GIỮA NGUYÊN
│
├── agents/                         ← AI Agent config — GIỮ NGUYÊN
│   ├── role.md
│   ├── prompts/
│   └── reference/
│
├── config/                         ← 🔒 Config & credentials — GIỮ NGUYÊN
│
├── data/                           ← 📦 All data
│   ├── raw/                        ←   Fetched data (daily/, inventory/, nso/)
│   ├── processed/                  ←   Cleaned data
│   ├── master/                     ←   ⬅ RENAME từ data/shared/ + di chuyển JSON
│   │   ├── master_schedule.json    ←   (từ data/)
│   │   ├── dsst_cache.json         ←   (từ data/)
│   │   ├── nso_stores.json         ←   (từ data/)
│   │   └── Master Data.xlsx        ←   (từ data/shared/)
│   ├── cache/                      ←   NEW: SQLite cho Phase 2
│   └── state/                      ←   ⬅ MOVE từ output/state/
│       └── sent_messages.json
│
├── src/                            ← ⬅ RENAME từ script/
│   ├── lib/                        ←   Shared libraries — GIỮ NGUYÊN
│   │   ├── __init__.py
│   │   ├── sources.py
│   │   └── telegram.py
│   │
│   ├── domains/                    ←   Business logic — GIỮ NGUYÊN structure
│   │   ├── daily/generate.py
│   │   ├── performance/
│   │   │   ├── generate.py
│   │   │   ├── fetch_monthly.py
│   │   │   ├── fetch_weekly.py
│   │   │   ├── export_sla_weekly.py
│   │   │   ├── analyze_store_metrics.py
│   │   │   └── generate_ro_tote.py
│   │   ├── inventory/
│   │   │   ├── generate.py
│   │   │   └── generate_weekly.py
│   │   ├── nso/
│   │   │   ├── generate.py
│   │   │   ├── nso_master.py
│   │   │   ├── fetch_nso_mail.py
│   │   │   ├── inject_mail_text.py
│   │   │   ├── nso_remind.py
│   │   │   └── _save_dsst.py
│   │   └── weekly_plan/
│   │       ├── generate_excel.py
│   │       └── finalize.py
│   │
│   ├── compose/                    ←   Mail compose + inject — GIỮ NGUYÊN
│   │   ├── auto_compose.py
│   │   ├── compose_mail.py
│   │   └── inject_haraworks.py
│   │
│   ├── dashboard/                  ←   Dashboard export/deploy — GIỮ NGUYÊN
│   │   ├── export_data.py
│   │   ├── export_weekly_plan.py
│   │   └── deploy.py
│   │
│   └── orchestrator/               ←   Pipeline — GIỮ NGUYÊN
│       └── pipeline.py
│
├── output/                         ← 📊 Generated outputs — CLEAN UP
│   ├── reports/                    ←   ⬅ RENAME từ output/artifacts/
│   │   ├── daily/
│   │   ├── performance/
│   │   ├── inventory/
│   │   ├── nso/
│   │   └── weekly transport plan/
│   ├── exports/                    ←   NEW: Excel/CSV riêng
│   ├── dashboard/                  ←   GIỮ NGUYÊN
│   ├── mail/                       ←   GIỮ NGUYÊN
│   └── logs/                       ←   GIỮ NGUYÊN
│
├── tools/                          ← 🛠️ NEW: User-facing entry points
│   ├── start-metabase.bat          ←   (move từ C:\metabase\)
│   ├── start-dashboard.bat         ←   NEW: Serve dashboard tại :8080
│   ├── run-daily.bat               ←   NEW: Chạy daily report
│   ├── run-performance.bat         ←   NEW: Chạy performance report
│   ├── run-inventory.bat           ←   NEW: Chạy inventory report
│   ├── run-all.bat                 ←   NEW: Chạy hết
│   └── tasks/                      ←   Windows Task Scheduler XMLs
│       ├── auto_compose_task.xml
│       ├── auto_inventory_task.xml
│       └── auto_nso_task.xml
│
├── scratch/                        ← 🧪 MOVE scratch_* files vào đây
│
├── backups/                        ← GIỮ NGUYÊN
├── docs/                           ← GIỮ NGUYÊN
└── README.md
```

### 1.2 Mapping cũ → mới

| Cũ | Mới | Ghi chú |
|----|-----|---------|
| `script/` | `src/` | Rename toàn bộ |
| `script/lib/` | `src/lib/` | Giữ nguyên nội dung |
| `script/domains/` | `src/domains/` | Giữ nguyên nội dung |
| `script/compose/` | `src/compose/` | Giữ nguyên nội dung |
| `script/dashboard/` | `src/dashboard/` | Giữ nguyên nội dung |
| `script/orchestrator/` | `src/orchestrator/` | Giữ nguyên nội dung |
| `script/scratch_*.py` | `scratch/` | Dọn sạch script/ |
| `data/shared/` | `data/master/` | Rename + gom master data |
| `data/*.json` (root) | `data/master/` | Di chuyển schedule, cache |
| `output/artifacts/` | `output/reports/` | Rename rõ nghĩa hơn |
| `output/state/` | `data/state/` | State = data, không phải output |
| `config/*.xml` (tasks) | `tools/tasks/` | Gom task scheduler configs |

### 1.3 Import paths cần fix

> [!WARNING]
> Đây là bước **rủi ro nhất**. Tất cả `sys.path` references và relative imports sẽ break.

```python
# CŨ (trong mọi generate.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "script"))
from lib.sources import ...
from lib.telegram import ...

# MỚI — chỉ đổi "script" → "src"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
from lib.sources import ...
from lib.telegram import ...
```

**Files cần update import path:**

| File | Import cần fix |
|------|---------------|
| `src/domains/daily/generate.py` | `sys.path` → `"src"` |
| `src/domains/performance/generate.py` | `sys.path` → `"src"` |
| `src/domains/performance/fetch_monthly.py` | `sys.path` → `"src"` |
| `src/domains/performance/fetch_weekly.py` | `sys.path` → `"src"` |
| `src/domains/performance/export_sla_weekly.py` | `sys.path` → `"src"` |
| `src/domains/inventory/generate.py` | `sys.path` → `"src"` |
| `src/domains/inventory/generate_weekly.py` | `sys.path` → `"src"` |
| `src/domains/nso/generate.py` | `sys.path` → `"src"` |
| `src/domains/nso/fetch_nso_mail.py` | `sys.path` → `"src"` |
| `src/domains/nso/nso_master.py` | `sys.path` → `"src"` |
| `src/domains/weekly_plan/generate_excel.py` | `sys.path` → `"src"` |
| `src/compose/auto_compose.py` | `sys.path` → `"src"` |
| `src/compose/compose_mail.py` | `sys.path` → `"src"` |
| `src/compose/inject_haraworks.py` | `sys.path` → `"src"` |
| `src/dashboard/export_data.py` | `sys.path` → `"src"` |
| `src/dashboard/deploy.py` | `sys.path` → `"src"` |
| `src/orchestrator/pipeline.py` | path refs |

**Output path refs cần fix:**

```python
# Tìm tất cả ref đến "artifacts" → đổi sang "reports"
# Tìm tất cả ref đến "output/state" → đổi sang "data/state"
# Tìm tất cả ref đến "data/shared" → đổi sang "data/master"
```

### 1.4 Workflow files cần update

| File | Thay đổi |
|------|----------|
| `.agents/workflows/daily-report.md` | `script/` → `src/` |
| `.agents/workflows/compose-mail.md` | `script/` → `src/` |
| `.agents/workflows/backup-inject.md` | `script/` → `src/` |
| `.agents/workflows/performance-report.md` | `script/` → `src/` |
| `.agents/workflows/inventory.md` | `script/` → `src/` |
| `.agents/workflows/nso-scan.md` | `script/` → `src/` |
| `.agents/workflows/weekly-plan.md` | `script/` → `src/` |
| `agents/role.md` | Cập nhật folder tree |
| `agents/reference/architecture.md` | Cập nhật toàn bộ |
| `README.md` | Cập nhật folder tree |

### 1.5 Tools (bat files)

```bat
@REM === tools/run-daily.bat ===
@echo off
title Daily Report Runner
cd /d "G:\My Drive\DOCS\transport_daily_report"

echo ============================================
echo   Running Daily Report...
echo ============================================
python src\domains\daily\generate.py

echo.
echo   Done! Opening report...
start "" "output\reports\daily"
pause
```

```bat
@REM === tools/start-dashboard.bat ===
@echo off
title Dashboard Server (port 8080)
cd /d "G:\My Drive\DOCS\transport_daily_report\output\dashboard"

echo ============================================
echo   Dashboard: http://localhost:8080
echo ============================================
python -m http.server 8080
```

### 1.6 Execution Order

```
Step 1: Backup hiện tại
  git add -A && git commit -m "pre-restructure snapshot"

Step 2: Rename script/ → src/
  git mv script src

Step 3: Di chuyển files
  git mv data/shared data/master
  git mv data/*.json data/master/
  git mv output/artifacts output/reports
  mkdir data/state
  git mv output/state/* data/state/
  mkdir tools/tasks
  git mv config/*.xml tools/tasks/
  mkdir scratch
  git mv src/scratch_*.py scratch/

Step 4: Fix imports (batch find-replace)
  Tất cả file .py: "script" → "src" trong sys.path
  Tất cả file .py: "artifacts" → "reports" trong output paths
  Tất cả file .py: "data/shared" → "data/master"
  Tất cả file .py: "output/state" → "data/state"

Step 5: Fix workflows + docs
  Tất cả .md trong .agents/workflows/: "script/" → "src/"

Step 6: Tạo tools/*.bat

Step 7: Test
  python src/domains/daily/generate.py → verify output
  tools/run-daily.bat → verify bat runner
  Metabase → verify queries still work

Step 8: Commit
  git add -A && git commit -m "restructure: script/ → src/, tools/, cleanup"
```

---

## Phase 2: Auto ETL + Offline Cache (LÀM SAU)

> [!NOTE]
> Chỉ bắt đầu Phase 2 khi Phase 1 đã stable, tất cả domains chạy đúng với cấu trúc mới.

### 2.1 SQLite Cache Layer

```
data/cache/
└── local.db              ← SQLite database
    ├── daily_summary       (from output/state/history.json)
    ├── performance_data    (from performance fetch)
    ├── inventory_data      (from inventory reconciliation)
    └── trip_data           (from ClickHouse kf_trip_locations_items)
```

**Script mới:**

```
src/etl/
├── export_sqlite.py       ← Đọc processed data → ghi SQLite
├── fetch_clickhouse.py    ← Query ClickHouse → save local
└── fetch_starrocks.py     ← Query StarRocks → save local (nếu cần)
```

### 2.2 Metabase SQLite Connection

```
Metabase → Add Database → SQLite
  Path: G:\My Drive\DOCS\transport_daily_report\data\cache\local.db
  → Query offline khi ClickHouse/StarRocks down
```

### 2.3 Windows Task Scheduler

```
tools/tasks/
├── auto_daily_report.xml     ← Chạy run-daily.bat lúc 7:00 AM
├── auto_export_sqlite.xml    ← Chạy export_sqlite.py sau mỗi report
├── auto_dashboard_serve.xml  ← Keep dashboard server alive
└── auto_compose.xml          ← Compose mail theo schedule (đã có)
```

### 2.4 Scheduler Install

```bat
@REM === tools/install-tasks.bat ===
@echo off
echo Installing scheduled tasks...
schtasks /create /xml "tools\tasks\auto_daily_report.xml" /tn "KFM\DailyReport" /f
schtasks /create /xml "tools\tasks\auto_export_sqlite.xml" /tn "KFM\ExportSQLite" /f
echo Done!
pause
```

---

## Dual-Mode Architecture

```
                    ┌─────────────────────────┐
                    │     src/domains/        │
                    │     src/lib/            │  ← Code chung
                    │     src/compose/        │    (cả 2 mode dùng)
                    │     src/dashboard/      │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                                     ▼
    ┌────────────────────┐              ┌────────────────────┐
    │  🤖 Mode: AI       │              │  👤 Mode: Manual   │
    │                    │              │                    │
    │  .agents/          │              │  tools/            │
    │    workflows/      │              │    run-daily.bat   │
    │    (slash commands)│              │    run-all.bat     │
    │                    │              │    start-dash.bat  │
    │  agents/           │              │                    │
    │    prompts/        │              │  Metabase :3000    │
    │    role.md         │              │    (query trực tiếp │
    │                    │              │     hoặc SQLite)   │
    │  + Debug           │              │                    │
    │  + Refactor        │              │  Dashboard :8080   │
    │  + Complex logic   │              │    (static HTML)   │
    └────────────────────┘              └────────────────────┘
```

### Mapping 3 Roles → Folders

| Role | Folders | Mode |
|------|---------|------|
| 🔍 **Analysis & Gap Fix** | `agents/prompts/`, `agents/reference/`, `data/master/` | 🤖 AI only |
| 🔧 **Development & Refactor** | `src/lib/`, `src/domains/`, `src/etl/` | 🤖 AI only |
| 🔄 **Execution & Deploy** | `tools/`, `src/deploy/`, `output/` | 🤖 AI + 👤 Manual |

---

## Checklist

### Phase 1

- [x] Backup + git commit ✅ (07/05/2026)
- [x] `scratch_*.py` → `scratch/` ✅ 12 files moved
- [x] Tạo `tools/*.bat` ✅ 7 bat files
- [x] Dashboard server verified ✅ localhost:8080
- [x] Dashboard rebuild ✅ 4/4 tabs active
- [ ] `data/shared/` → `data/master/` + gom JSON
- [ ] `config/*.xml` → `tools/tasks/`
- [ ] Update `agents/role.md`
- [ ] Update `agents/reference/architecture.md`
- [ ] Update `README.md`
- [ ] Test: `tools/run-daily.bat` (bạn double-click thử)
- [ ] Test: Metabase queries

> **CANCELLED**: `script/` → `src/` (giữ nguyên `script/`)
> **CANCELLED**: `output/artifacts/` → `output/reports/` (giữ nguyên, tránh break refs)
> **CANCELLED**: SQLite cache (không cần)

### Phase 2 (sau khi Phase 1 stable)

- [ ] Tạo scheduler XMLs
- [ ] `tools/install-tasks.bat`
- [ ] Auto ETL từ ClickHouse/StarRocks (nếu cần)
