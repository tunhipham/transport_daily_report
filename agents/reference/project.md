# 📋 KFM Logistics — Project Master Document

> **Single source of truth** cho toàn bộ hệ thống.
> Agent mới vào đọc file này → biết ngay: kiến trúc gì, pending gì, làm tiếp gì.
>
> **Supersedes**: `architecture.md`, `restructure-plan.md`, `data-pipeline-plan.md`, `realtime-dashboard-plan.md`, `external-folder-dashboard.md`, `weekly-plan-automation.md`

---

## 0. Session State — Agent Handoff
x`
> [!IMPORTANT]
> **Mỗi agent session PHẢI đọc section này trước.** Nó cho biết session trước làm gì, pending gì.
> Sau khi hoàn thành task → **CẬP NHẬT section này** trước khi kết thúc.

### Current State

```
Last updated: 2026-05-15T23:16 (by: tunhipham — planning session)
Phase: PRE-IMPLEMENTATION
Next action: Implement Phase A (Task Registry + Runner)
```

### Session Log

| # | Date | Agent/User | Task | Result | Pending |
|---|------|-----------|------|--------|---------|
| 1 | 15/05/2026 | tunhipham | Research Multica + Design ops layer | ✅ Design approved | Implement Phase A |

### Active Blockers

| ID | Blocker | Affects | Since |
|----|---------|---------|-------|
| — | (none) | — | — |

### Data Pipeline Status

| Layer | Status | Notes |
|-------|--------|-------|
| Bronze/Silver storage | 📝 Planned | Not yet created |
| StarRocks extractors | 📝 Planned | Connectivity verified ✅ |
| ClickHouse extractors | 📝 Planned | Connectivity verified ✅ |
| Realtime sync daemon | 📝 Planned | — |

---

## 1. System Overview

### 1.1 What This System Does

Hệ thống automation logistics cho KFM warehouse: fetch data → generate reports → deploy dashboard → send notifications. Chạy **dual-mode** (AI agent hoặc manual bat files).

### 1.2 Folder Structure (Target v2)

> [!IMPORTANT]
> **3 tầng chính**: `workspace/` (code, git tracked) → `runtime/` (data, gitignored) → `snapshots/` (frozen versions)
> `.agents/` và `tools/` giữ ở root vì convention + UX.

```
transport_daily_report/
│
├── .agents/workflows/                   ← Slash commands (giữ root — Gemini convention)
│   ├── daily-report.md
│   ├── sync-and-report.md
│   ├── performance-report.md
│   ├── inventory.md
│   ├── nso-scan.md
│   ├── weekly-plan.md
│   ├── compose-mail.md
│   ├── backup-inject.md
│   └── telegram-group.md
│
├── workspace/                           ← ⭐ CODE + CONFIG (git tracked)
│   │
│   ├── data_pipeline/                   ← ETL PIPELINE
│   │   ├── __init__.py
│   │   ├── run.py                         Pipeline entry point
│   │   ├── config.py                      DB config loader
│   │   ├── validators.py                  Schema validation
│   │   ├── extractors/                    Data extractors
│   │   │   ├── _base.py                     Base interface
│   │   │   ├── starrocks_transfer.py        PT Transfer (CDC)
│   │   │   ├── starrocks_trips.py           Trip details (CDC)
│   │   │   ├── clickhouse_master.py         Master barcode→weight
│   │   │   ├── clickhouse_schedules.py      Lịch giao
│   │   │   ├── clickhouse_transfer_mart.py  Transfer mart
│   │   │   ├── file_yeu_cau.py              Yêu cầu KSL (local)
│   │   │   └── file_kh_meat.py              KH MEAT (local)
│   │   └── contracts/                     ⭐ Schema / interfaces
│   │       ├── transfer.schema.json
│   │       ├── trip.schema.json
│   │       ├── inventory.schema.json
│   │       └── state.schema.json
│   │
│   ├── script/
│   │   ├── domains/                       📊 Business logic (5 domains)
│   │   │   ├── daily/generate.py
│   │   │   ├── performance/generate.py
│   │   │   ├── inventory/generate.py
│   │   │   ├── nso/scan.py
│   │   │   └── weekly_plan/finalize.py
│   │   │
│   │   ├── lib/                           🔧 Shared library
│   │   │   ├── sources.py                   Data source helpers
│   │   │   ├── telegram.py                  Telegram send utilities
│   │   │   ├── logger.py                    Structured logging
│   │   │   └── state_manager.py             ⭐ State + locking
│   │   │
│   │   ├── orchestrator/                  🎯 Session management
│   │   │   ├── run_all.py                   Session runner
│   │   │   ├── dependency_graph.py          Task dependencies
│   │   │   └── retry_handler.py             Retry logic
│   │   │
│   │   ├── dashboard/                     🚀 Export + deploy
│   │   │   ├── export_data.py
│   │   │   ├── deploy.py
│   │   │   └── export_weekly_plan.py
│   │   │
│   │   ├── compose/                       ✉️ Mail automation
│   │   ├── telegram/                      📱 Group management
│   │   ├── external/                      👥 External contributor
│   │   ├── deprecated/                    🔒 Old business logic
│   │   └── experimental/                  🧪 WIP / thử nghiệm
│   │
│   ├── config/                            🔑 Credentials & configs
│   │   ├── mcp_starrocks.json
│   │   ├── mcp_clickhouse.json
│   │   ├── telegram.json
│   │   ├── mail_schedule.json
│   │   └── env.example
│   │
│   ├── agents/                            🤖 AI context
│   │   ├── role.md
│   │   ├── prompts/                         Per-domain knowledge
│   │   └── reference/
│   │       └── project.md                   ★ THIS FILE
│   │
│   ├── tests/                             🧪 Test scaffold (future)
│   │   ├── pipeline/
│   │   ├── domains/
│   │   └── integration/
│   │
│   └── README.md
│
├── runtime/                             ← ♻️ GENERATED / RUNTIME (gitignored)
│   │
│   ├── storage/                           Bronze/Silver data layers
│   │   ├── bronze/{DDMMYYYY}/               Raw extracted data
│   │   ├── silver/{DDMMYYYY}/               Validated + lockable ★
│   │   ├── master/                          Latest master data
│   │   └── logs/                            Pipeline logs
│   │
│   ├── output/                            Domain outputs
│   │   ├── state/                           ★ JSON state (domain bridge)
│   │   ├── artifacts/{domain}/              PNG/HTML per domain
│   │   ├── mail/                            Composed mail HTML
│   │   └── logs/                            Execution logs
│   │
│   └── ingest/                            External input (Drive sync, manual drops)
│       ├── daily/                           Xlsx từ Google Drive
│       ├── transfer/                        Phiếu chuyển xlsx
│       ├── yeu_cau/                         Yêu cầu chuyển hàng
│       └── nso/                             NSO mail data
│
├── snapshots/                           ← 📦 FROZEN VERSIONS
│   ├── {descriptive_name}/                vd: 2026_Q2_stable, pre_restructure
│   └── ...
│
├── tools/                               ← 🔨 Bat files (giữ root — dễ double-click)
│   ├── run-daily.bat
│   ├── run-performance.bat
│   ├── run-inventory.bat
│   ├── run-weekly-plan.bat
│   ├── run-nso-scan.bat
│   ├── run-backup-inject.bat
│   ├── run-telegram-group.bat
│   ├── start-dashboard.bat
│   └── ...
│
├── docs/                                ← 🌐 GitHub Pages dashboard
│   ├── index.html                         SPA (6 tabs)
│   ├── data/*.json                        Dashboard data
│   └── external/                          External contributor tabs
│       ├── nhap_xuat_dm.html
│       └── claim_aba.html
│
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

### 1.3 Design Principles

1. **Domain Independence** — Mỗi domain chạy độc lập, không import domain khác
2. **State as Contract** — Domains giao tiếp qua JSON trong `output/state/`
3. **Single Source of Truth** — Master data, config chỉ có 1 bản
4. **Silver-first, File-fallback** — Ưu tiên DB (StarRocks/ClickHouse), fallback file xlsx
5. **Fail-safe Isolation** — 1 domain fail → các domain khác + dashboard vẫn chạy

---

## 2. Task Registry

> Lấy cảm hứng từ Multica: mọi task đều có owner, dependencies, status, schedule — nhìn 1 chỗ biết hết.

### 2.1 All Tasks

| ID | Name | Domain | Trigger | Script | Owner |
|----|------|--------|---------|--------|-------|
| `daily-report` | Báo Cáo Ngày | daily | scheduled 07:00 | `script/domains/daily/generate.py` | tunhipham |
| `compose-mail` | Soạn Mail Giao Hàng | compose | scheduled 15:30 | `script/compose/auto_compose.py` | tunhipham |
| `backup-inject` | Inject Mail Backup | compose | manual | `script/compose/inject_haraworks.py` | tunhipham |
| `inventory-daily` | Đối Soát Tồn Kho | inventory | manual/slash | `script/domains/inventory/generate.py` | tunhipham |
| `performance-monthly` | Báo Cáo Hiệu Suất | performance | manual/slash | `script/domains/performance/generate.py` | tunhipham |
| `nso-scan` | Quét NSO Store | nso | manual/slash | `script/domains/nso/generate.py` | tunhipham |
| `weekly-plan` | Lịch Về Hàng Tuần | weekly_plan | manual/slash | `script/domains/weekly_plan/generate_excel.py` | tunhipham |
| `telegram-group` | Quản Lý TG Group | telegram | manual/slash | `script/telegram/manage_group.py` | tunhipham |
| `update-nhap-xuat-dm` | Update Nhập/Xuất ĐM | external | manual | `script/external/deploy.py` | ThanhPhammm111 |
| `update-claim-aba` | Update Claim ABA | external | manual | `script/external/deploy.py` | ThanhPhammm111 |
| `deploy-dashboard` | Deploy Dashboard | dashboard | post-task | `script/dashboard/deploy.py` | tunhipham |

### 2.2 Dependencies

```
daily-report ──→ compose-mail
daily-report ──→ deploy-dashboard
nso-scan ──→ telegram-group
nso-scan ──→ weekly-plan (T3 kickoff)
[all domains] ──→ deploy-dashboard
```

### 2.3 Tools ↔ Workflows ↔ Scripts Mapping

| BAT file | Slash command | Script |
|----------|--------------|--------|
| `tools/run-daily.bat` | `/daily-report` | `script/domains/daily/generate.py` |
| `tools/run-performance.bat` | `/performance-report` | `script/domains/performance/generate.py` |
| `tools/run-inventory.bat` | `/inventory` | `script/domains/inventory/generate.py` |
| `tools/run-weekly-plan.bat` | `/weekly-plan` | `script/domains/weekly_plan/generate_excel.py` |
| `tools/run-backup-inject.bat` | `/backup-inject` | `script/compose/inject_haraworks.py` |
| `tools/run-telegram-group.bat` | `/telegram-group` | `script/telegram/manage_group.py` |
| `tools/start-dashboard.bat` | — | `python -m http.server 8080` |

---

## 3. Data Flow

### 3.1 Current Flow (File-based)

```
Sources (Google Sheets/Drive/Local xlsx)
    │
    ▼
script/domains/{domain}/generate.py
    │
    ├──→ output/state/*.json          (domain bridge)
    ├──→ output/artifacts/{domain}/   (PNG/HTML → Telegram)
    │
    ▼
script/dashboard/export_data.py
    │
    ▼
docs/data/*.json → deploy.py → GitHub Pages
```

### 3.2 Target Flow — DB Pipeline (daily + performance ONLY)

> [!IMPORTANT]
> **Hiện tại chỉ 2 domain dùng DB**: Daily Report + Performance.
> Các domain khác (inventory, NSO, weekly plan) vẫn file-based.

#### Daily Report Pipeline — Cutoff 08:00 mỗi ngày

```
                    ┌──────────────────────────┐
                    │  07:45 Task Scheduler     │
                    │  trigger fetch            │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ StarRocks (CDC)  │  │ StarRocks (CDC)  │  │ Local xlsx       │
│ kf_transfer_items│  │ krc_dashboard_   │  │ KH MEAT, ĐÔNG,   │
│ (phiếu chuyển D) │  │ delivery_schedule│  │ MÁT, Yêu cầu    │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
    ┌────▼─────────────────────▼──────────────────────▼────┐
    │  BRONZE  runtime/storage/bronze/{DDMMYYYY}/          │
    └────────────────────────┬─────────────────────────────┘
                             │ validate (contracts/*.schema.json)
    ┌────────────────────────▼─────────────────────────────┐
    │  SILVER  runtime/storage/silver/{DDMMYYYY}/  🔒      │
    └────────────────────────┬─────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────┐
    │  08:00 CUTOFF → generate.py → 5 PNG + HTML           │
    │  → Telegram → export → deploy dashboard              │
    │  → lock silver/{DDMMYYYY}/ (readonly)                │
    └──────────────────────────────────────────────────────┘
```

#### Performance Report Pipeline — 2 Cutoffs (weekly cycle)

```
┌─────────────────────────────────────────────────────────────┐
│  CUTOFF 1 — Thứ 2 (Monday) 08:00                           │
│                                                             │
│  StarRocks: kf_trips (T2→CN tuần trước)                    │
│       │                                                     │
│       ▼                                                     │
│  Scan incomplete trips (missing completion_time)            │
│       │                                                     │
│       ▼                                                     │
│  📱 Alert Telegram: "X trips chưa hoàn thành"              │
│  → Ops xử lý manual trong T2-T3                            │
└─────────────────────────────────────────────────────────────┘
                             │
                        T2-T3 gap
                      (ops resolve)
                             │
┌────────────────────────────▼────────────────────────────────┐
│  CUTOFF 2 — Thứ 3 (Tuesday) 08:00                          │
│                                                             │
│  StarRocks: kf_trips (final, should be complete now)        │
│       │                                                     │
│       ▼                                                     │
│  generate.py → performance report                           │
│  ┌─────────────────────────────────────────────┐            │
│  │ Trips vẫn chưa hoàn thành?                  │            │
│  │ → Option A: Exclude + flag "⚠️ incomplete"  │            │
│  │ → Option B: Dùng last known status + badge  │            │
│  └─────────────────────────────────────────────┘            │
│       │                                                     │
│       ▼                                                     │
│  📱 Telegram + 🌐 Dashboard deploy                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Data Sources Inventory

| Data | Current Source | DB Replacement | Phase |
|------|--------------|----------------|-------|
| PT Transfer | `transfer_*.xlsx` | StarRocks `kf_transfer_items` (CDC) | Pipeline |
| Master barcode→weight | Google Sheet 8MB | ClickHouse `kf_product_static` 28K rows | Pipeline |
| Lịch giao ALL kho | Google Sheets (KRC/KFM) + local xlsx | StarRocks `krc_dashboard_delivery_schedule` | Pipeline |
| Yêu cầu chuyển hàng (KSL) | Local xlsx | ❌ Not on DB — keep file | Pipeline |
| Trip details | — | StarRocks `kf_trips` (CDC) | Pipeline |
| KH MEAT (THỊT CÁ) | Local xlsx | ❌ Keep manual | Always file |
| Đối soát tồn kho | Local xlsx | ❌ Manual | Always file |
| NSO schedules | Telegram email scan | ❌ Event-driven | Always Telegram |

### 3.4 DB Connectivity (Verified ✅)

| Service | Endpoint | Config |
|---------|----------|--------|
| StarRocks | `103.147.122.56:9030` (MySQL) | `config/mcp_starrocks.json` |
| ClickHouse | `103.140.248.114:32015` (HTTP) | `config/mcp_clickhouse.json` |

---

## 4. Domain Reference (Quick)

### Daily Report
- **Script**: `script/domains/daily/generate.py`
- **DB Sources**: StarRocks `kf_transfer_items` (phiếu chuyển), `krc_dashboard_delivery_schedule` (lịch giao KRC)
- **Local Sources (fallback)**: KH THỊT CÁ, KH ĐÔNG, KH MÁT, Yêu cầu KSL — local xlsx
- **Cutoff**: ⏰ **08:00 mỗi ngày** (D+1)
- **Schedule**: Task Scheduler trigger 07:45 → fetch → generate → send 08:00
- **Outputs**: `output/state/history.json`, `output/artifacts/daily/` (5 PNG + 1 HTML)
- **Sends**: Telegram (5 PNG + HTML) → Dashboard deploy
- **Infra**: ⚠️ **Cần local machine BẬT** (vì còn local xlsx). Khi 100% DB → chuyển VPS được.

### Performance Report
- **Script**: `script/domains/performance/generate.py`
- **DB Source**: StarRocks `kf_trips` (CDC) — 100% từ DB, KHÔNG cần local file
- **Trip cache**: `output/trip_cache_T{mm}.json` (incremental)
- **Kho mapping**: KRC, QCABA→ĐÔNG MÁT, KSL→Sáng/Tối, SLKT→KSL-Tối
- **Sub-kho**: ĐÔNG MÁT → ĐÔNG/MÁT (by "Loại rổ" column)
- **Cutoff 1**: ⏰ **Thứ 2 08:00** — scan incomplete trips → alert Telegram
- **Cutoff 2**: ⏰ **Thứ 3 08:00** — generate full report → Telegram + dashboard
- **Incomplete trip handling**: Exclude + flag "⚠️" hoặc dùng last known status
- **Infra**: ✅ **Có thể chạy trên VPS** (100% DB, không local dependency)

### Inventory
- **Script**: `script/domains/inventory/generate.py`
- **Source**: Local xlsx (ton_aba/doi_soat/)
- **Pressure Score**: 14-day performance, Days Cover, ĐÔNG/MÁT thresholds

### NSO
- **Script**: `script/domains/nso/generate.py`
- **Source**: Telegram email scan → merge to master
- **DSST matching**: LCS ≥10 + ≥70% — see KI `nso-data-integrity`

### Weekly Plan
- **Script**: `script/domains/weekly_plan/generate_excel.py`
- **Auto**: T3 kickoff (after NSO scan) → T5 finalize (12:00-13:30)
- **Master**: `data/master_schedule.json`

### Compose Mail
- **Script**: `script/compose/auto_compose.py` → `compose_mail.py` → `inject_haraworks.py`
- **Method**: JS base64 + `setData()` (primary), clipboard paste (fallback)
- **Schedule**: DRY Tối 12:00, DRY Sáng+ĐM 15:00, KRC+TC 17:00, cutoff 19:00
- **Rule**: Compose kho → inject ngay → compose kho tiếp (KHÔNG compose hết rồi inject)

### External (ThanhPhammm111)
- **Files**: `docs/external/nhap_xuat_dm.html`, `docs/external/claim_aba.html`
- **Deploy**: PR-based → GitHub Actions auto-approve+merge
- **Whitelist**: CHỈ 2 file trên. Sửa file khác → BLOCK

---

## 5. Dashboard

### Tabs (Current)
1. Daily — Báo cáo ngày (KPI cards + charts)
2. Inventory — Đối soát tồn kho
3. Performance — Hiệu suất tháng
4. NSO — Store openings
5. Weekly Plan — Lịch tuần
6. External — Nhập/Xuất ĐM + Claim ABA

### Design System
- Colors: HSL tokens, dark mode via CSS variables
- Kho colors: KRC `#2196F3`, DRY `#FF9800`, ĐÔNG MÁT `#00BCD4`, THỊT CÁ `#E91E63`, KFM `#4CAF50`
- Font: Inter, monospace: JetBrains Mono
- Tables: compact, zebra, sticky header, tabular-nums
- Charts: Chart.js + datalabels plugin
- Self-contained HTML, works offline

---

## 6. Implementation Roadmap

> [!IMPORTANT]
> **Thứ tự thực hiện tối ưu token**: mỗi phase là 1 session, output rõ ràng, agent tiếp theo đọc Session State → biết làm tiếp gì.

### Phase A — Task Registry + Runner (1 session)

**Mục đích**: Tạo management layer — mọi task có trạng thái, dependency, log.

**Deliverables**:
1. `data/ops/task_registry.json` — registry 11 tasks (from §2)
2. `script/ops/runner.py` — chạy task by ID, check deps, log result
3. `script/ops/status.py` — print status table
4. `tools/run-ops-status.bat` — quick status check

**Runner concept**:
```python
# python script/ops/runner.py daily-report
# 1. Load task_registry.json
# 2. Check depends_on → warn if dependency not success
# 3. Set status="running", save
# 4. subprocess.run(task.script)
# 5. Set last_run, last_result (success/failed), save
```

**Acceptance**: `python script/ops/status.py` → prints table of all 11 tasks with status.

---

### Phase B — Ops Dashboard Tab (1 session)

**Mục đích**: Nhìn tổng quan hệ thống trên dashboard.

**Deliverables**:
1. `script/ops/export_ops.py` — export `task_registry.json` → `docs/data/ops.json`
2. Tab "🎛️ OPS" trong `docs/index.html`:
   - Status cards (✅ success / ❌ failed / ⏳ pending / 🔄 running)
   - Task timeline (last runs, chronological)
   - Dependency graph (mermaid or canvas)
   - Owner summary (tunhipham vs ThanhPhammm111)
3. Integrate into `deploy.py`

**Acceptance**: Dashboard tab OPS shows real task status from registry.

---

### Phase C — Data Pipeline Foundation (1-2 sessions)

**Mục đích**: DB-first data fetching, bronze/silver layers.

**Deliverables**:
1. `storage/` directory: `bronze/`, `silver/`, `master/`, `logs/`
2. `data_pipeline/config.py` — DB config loader
3. `data_pipeline/extractors/_base.py` — Extractor interface
4. `data_pipeline/extractors/sr_schedule.py` — StarRocks lịch giao
5. `data_pipeline/extractors/sr_transfer.py` — StarRocks phiếu chuyển
6. `data_pipeline/extractors/ch_products.py` — ClickHouse master barcode→weight
7. `data_pipeline/extractors/file_yeu_cau.py` — Local xlsx KSL

**Acceptance**: `python -m data_pipeline.run --date DD/MM/YYYY` → bronze + silver populated, row counts match file sources.

---

### Phase D — Silver-first Generate + Sync Daemon (1-2 sessions)

**Mục đích**: Daily report đọc từ DB, auto-sync mỗi 15 phút.

**Deliverables**:
1. Modify `generate.py` — silver-first logic (read silver/ → fallback file)
2. `data_pipeline/sync_realtime.py` — orchestrator (extract → bronze → silver → generate → export → deploy)
3. Hash comparison — skip report if data unchanged
4. Lock mechanism — `silver/{date}/lock.json` at cutoff 19:00
5. Task Scheduler XML for 15-min sync (06:00-22:00)
6. Dashboard auto-refresh JS (5-min interval)

**Acceptance**: Dashboard auto-updates every 15 min with DB data. Delete silver/ → fallback to files works.

---

### Phase E — Weekly Plan Automation (1 session)

**Mục đích**: Auto weekly plan lifecycle.

**Deliverables**:
1. `script/domains/weekly_plan/auto_weekly.py` — kickoff (T3) + finalize (T5)
2. Modify `auto_nso_watch.bat` — trigger kickoff after NSO scan
3. Task Scheduler for T5 finalize
4. Telegram notifications

---

### Phase F — Full Integration (1 session)

**Mục đích**: Wire everything together.

**Deliverables**:
1. All bat files route through `runner.py`
2. Auto-update task_registry on every run
3. OPS dashboard tab shows live data
4. Cleanup old reference MDs (archive to `agents/reference/_archive/`)

---

## 7. Operational Timeline

### 7.1 Daily Cycle — Mỗi Ngày

```
05:00  ═══ CDC bắt đầu nhận data ngày mới ══════════════════

07:45  ▶ DAILY REPORT: Task Scheduler trigger
         Fetch DB: transfer + KRC schedule (ngày D)
         Fetch local: KH MEAT, ĐÔNG, MÁT, Yêu cầu
08:00  ── DAILY REPORT CUTOFF ──
         ★ Generate 5 PNG + HTML
         ★ Send Telegram
         ★ Export → deploy dashboard
         ★ Lock silver/{D}/ (readonly)

12:00  ▶ COMPOSE: DRY Tối compose check
14:00  ── DRY Tối CUTOFF ──
15:00  ▶ COMPOSE: DRY Sáng + ĐÔNG MÁT compose check
16:30  ── DRY Sáng CUTOFF ──
17:00  ▶ COMPOSE: KRC + THỊT CÁ compose check
19:00  ── COMPOSE FINAL LOCK ──
22:00  ═══ Scheduler ngừng ═══════════════════════════════════
```

### 7.2 Weekly Cycle — Performance Report

```
═══════════════════ TUẦN N ═════════════════════════════════

T2 (Mon) 08:00  ▶ PERF SCAN
                  Query StarRocks kf_trips: T2→CN tuần (N-1)
                  Lọc trips chưa hoàn thành
                  📱 Alert Telegram:
                  "⚠️ X trips chưa có completion_time"
                  "Cần xử lý trước T3 08:00"

T2-T3           ▶ OPS RESOLVE
                  Ops team xử lý incomplete trips:
                  - Liên hệ tài xế/kho confirm
                  - Update trạng thái trên hệ thống
                  - Hoặc mark as exception

T3 (Tue) 08:00  ── PERF CUTOFF ──
                  ★ Fetch final trip data
                  ★ Generate performance report
                  ★ Handle remaining incompletes (exclude + flag)
                  ★ Send Telegram + deploy dashboard

════════════════════════════════════════════════════════════
```

### 7.3 Infrastructure — Bật Máy Hay Không?

| Task | DB dependency | Local file dependency | Kết luận |
|------|--------------|----------------------|----------|
| **Daily Report** | ✅ StarRocks (transfer, KRC) | ⚠️ CÒN (KH MEAT, ĐÔNG, MÁT, Yêu cầu) | ⚠️ **Cần local machine** |
| **Performance** | ✅ StarRocks (trips) — 100% | ❌ Không cần | ✅ **Chạy VPS được** |
| Compose Mail | — | ✅ Cần browser (Haraworks) | ⚠️ **Cần local machine** |
| Inventory | — | ✅ Local xlsx | ⚠️ **Cần local machine** |
| NSO Scan | — | Telegram event | Manual trigger |
| Weekly Plan | — | master_schedule.json | Manual trigger |

**Phương án cho Daily Report (cần local machine):**

| Option | Mô tả | Pros | Cons |
|--------|--------|------|------|
| **A. Sleep + Wake** | Machine sleep, Task Scheduler wake 07:45 | Đơn giản, không tốn tiền | Phải để máy ở chế độ Sleep (không Shutdown) |
| **B. Always On** | Máy bật 24/7 | Đảm bảo chạy | Tốn điện |
| **C. Migrate to DB** | Chuyển KH MEAT/ĐÔNG/MÁT lên DB | Giải phóng khỏi local | Cần upload pipeline + thời gian |
| **D. Drive API** | Fetch local xlsx qua Google Drive API từ VPS | VPS chạy tự do | Cần setup Drive API + service account |

**Phương án cho Performance (100% DB):**

| Option | Mô tả | Pros | Cons |
|--------|--------|------|------|
| **A. VPS cron** | Cheap VPS ($5/mo) + cron T2+T3 08:00 | Không cần bật máy, luôn chạy | Tốn ~$5/tháng |
| **B. GitHub Actions** | Scheduled workflow T2+T3 | Free (public repo) | DB phải accessible từ GitHub network |
| **C. Local Task Scheduler** | Giống daily report | Đơn giản | Cần bật máy |

---

## 8. Architecture Diagrams

### Dual-Mode Architecture

```
                    ┌────────────────────────────┐
                    │    task_registry.json        │
                    │  (tasks, owners, deps,       │
                    │   schedules, status)          │
                    └─────────────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  🤖 AI Mode      │   │  👤 Manual Mode  │   │  📊 Dashboard    │
│  .agents/        │   │  tools/*.bat     │   │  Tab: OPS        │
│  workflows/      │   │  runner.py       │   │  Status board    │
│  (slash commands)│   │                  │   │  Timeline        │
└──────────────────┘   └──────────────────┘   └──────────────────┘
          │                       │                       ▲
          └───────────────────────┤───────────────────────┘
                                  ▼
                    ┌────────────────────────────┐
                    │    script/domains/           │  Business Logic
                    │    script/compose/           │  (KHÔNG ĐỔI)
                    │    script/external/          │
                    └────────────────────────────┘
```

### Data Pipeline Architecture

```
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐
│ StarRocks (CDC) │  │ ClickHouse   │  │ Local Files  │
└────────┬────────┘  └──────┬───────┘  └──────┬───────┘
         │                  │                  │
    ┌────▼──────────────────▼──────────────────▼────┐
    │              EXTRACTORS                        │
    │  sr_schedule · sr_transfer · ch_products       │
    │  sr_trips · file_yeu_cau · file_kh_meat       │
    └────────────────────┬──────────────────────────┘
                         │
    ┌────────────────────▼──────────────────────────┐
    │  BRONZE  storage/bronze/{DDMMYYYY}/            │
    │  (raw, unvalidated)                            │
    └────────────────────┬──────────────────────────┘
                         │ validate + promote
    ┌────────────────────▼──────────────────────────┐
    │  SILVER  storage/silver/{DDMMYYYY}/  🔒        │
    │  (validated, locked at cutoff)                  │
    └────────────────────┬──────────────────────────┘
                         │
    ┌────────────────────▼──────────────────────────┐
    │  REPORT ENGINE  generate.py (silver-first)     │
    │  → output/state/ → export → deploy → Dashboard │
    └───────────────────────────────────────────────┘
```

---

## 9. Config Reference

### DB Connections
- StarRocks: `config/mcp_starrocks.json` — `kfm_scm` database
- ClickHouse: `config/mcp_clickhouse.json` — `kdb` database

### Telegram Bots
- Daily: `config/telegram.json`
- Inventory: `config/telegram_inventory.json`
- NSO: `config/telegram_nso.json`

### Mail
- Schedule: `config/mail_schedule.json`
- Haraworks login: SC012433
- Edge profile: `$HOME\.edge_automail\`

### Data Paths
- Google Drive sync: `G:\My Drive\DOCS\DAILY\`
- Transfer files: `G:\My Drive\DOCS\DAILY\transfer\`
- Yêu cầu files: `G:\My Drive\DOCS\DAILY\yeu_cau_chuyen_hang_thuong\`

---

## 10. Retention & Cleanup

| Layer | Retention | Size/day |
|-------|-----------|----------|
| Bronze | 7 days | ~200KB |
| Silver | 90 days | ~200KB (P1), ~5MB (P2) |
| Master (products) | Latest only | ~500KB |
| Logs | 30 days | ~5KB |
| output/artifacts/ | 30 days | varies |

---

## 11. Rules & Gotchas

### External Contributor Rules
- ✅ CHỈ sửa `docs/external/nhap_xuat_dm.html` + `docs/external/claim_aba.html`
- ❌ KHÔNG thêm file mới, KHÔNG sửa `docs/index.html`
- Deploy qua PR → GitHub Actions auto-approve+merge

### Compose Mail Rules
- Compose kho → inject ngay → compose kho tiếp
- Script KHÔNG BAO GIỜ click nút Gửi
- Backup từ terminal: luôn dùng JS base64 (clipboard fail khác session)

### NSO Data Integrity
- See KI `nso-data-integrity` for full rules
- DSST matching: LCS ≥10 + ≥70%
- Single source of truth, no old data modification, lock after validation

### Performance Gotchas
- HÀNG MÁT folder path có dấu tiếng Việt → Unicode escape
- SLKT = KSL-Tối (luôn)
- Sub-kho ĐÔNG/MÁT phân biệt bằng "Loại rổ" column
- KSL session: ref_time.hour < 15 → Sáng, else → Tối

---

## 12. Checklist — Overall Progress

### ✅ Done
- [x] Dashboard SPA 6 tabs (Daily, Inventory, Perf, NSO, Weekly, External)
- [x] 15 bat files in tools/
- [x] 10 slash command workflows
- [x] External contributor PR pipeline
- [x] Telegram group management automation
- [x] Pressure score system for inventory
- [x] DB connectivity verified (StarRocks + ClickHouse)

### 🔲 Phase A — Task Registry + Runner
- [ ] Create `data/ops/task_registry.json`
- [ ] Create `script/ops/runner.py`
- [ ] Create `script/ops/status.py`
- [ ] Create `tools/run-ops-status.bat`
- [ ] Test: `python script/ops/status.py` shows all tasks

### 🔲 Phase B — Ops Dashboard Tab
- [ ] Create `script/ops/export_ops.py`
- [ ] Add OPS tab to `docs/index.html`
- [ ] Integrate into deploy pipeline
- [ ] Test: dashboard shows task status

### 🔲 Phase C — Data Pipeline Foundation
- [ ] Create `storage/` directories + `.gitignore`
- [ ] Create `data_pipeline/` package
- [ ] Implement extractors (sr_schedule, sr_transfer, ch_products, file_yeu_cau)
- [ ] Verify: row counts match file sources

### 🔲 Phase D — Silver-first + Sync Daemon
- [ ] Modify `generate.py` silver-first logic
- [ ] Create `sync_realtime.py`
- [ ] Hash comparison + lock mechanism
- [ ] Task Scheduler XML (15-min)
- [ ] Dashboard auto-refresh JS
- [ ] Verify: fallback to files when silver/ missing

### 🔲 Phase E — Weekly Plan Automation
- [ ] Create `auto_weekly.py` (kickoff + finalize)
- [ ] Wire into NSO + Task Scheduler
- [ ] Test T3 kickoff + T5 finalize flow

### 🔲 Phase F — Full Integration
- [ ] All bat files → runner.py
- [ ] Auto-update registry on every run
- [ ] OPS tab live data
- [ ] Archive old reference MDs

---

## 13. How To Use This Document

### For AI Agent (new session)
1. Read **§0 Session State** → know what's pending
2. Read **§2 Task Registry** → know all tasks
3. Read relevant **§4 Domain Reference** for your task
4. Do work
5. **UPDATE §0** before ending session

### For Manual User
1. Read **§2.3** → find bat file for your task
2. Run bat file OR slash command
3. Check **§7 Timeline** for compose schedule

### For External Contributor (Thanh)
1. Read **§11 Rules** → external contributor section
2. Only modify whitelisted files
3. Use `/update-external` workflow
