# KFM Logistics System — Full Overview
> Cập nhật: 19/05/2026 16:51

---

## 📁 Folder Structure

```
transport_daily_report/
│
├── config/                              🔧 CẤU HÌNH
│   ├── data_sources.json                # DB registry + branch mapping (KRC, ĐÔNG MÁT, THỊT CÁ...)
│   ├── mcp_clickhouse.json              # ClickHouse credentials
│   ├── mcp_starrocks.json               # StarRocks credentials
│   ├── telegram.json                    # Bot tokens + chat IDs
│   ├── telegram_client.json             # Telethon API (group management)
│   ├── mail_schedule.json               # Haraworks auto-compose
│   ├── external_access.json             # External collaborator config
│   ├── sync_realtime_task.xml           # Scheduler: smart sync mỗi 15 phút
│   ├── trip_reminder_task.xml           # Scheduler: T2+T3 8AM remind
│   └── trip_cutoff_task.xml             # Scheduler: T3 9AM cutoff
│
├── script/                              📜 CODE
│   ├── data_pipeline/                   # ⚡ DB + Orchestration
│   │   ├── config.py                    #   load_clickhouse_config / load_starrocks_config
│   │   ├── sync_realtime.py             #   🔄 Smart sync (COUNT check → generate → deploy)
│   │   ├── trip_cutoff.py               #   ✂️ T3 cutoff (Notepad → decide → generate perf)
│   │   ├── run.py                       #   Legacy pipeline runner
│   │   ├── validators.py                #   Data validation helpers
│   │   ├── adapters/                    #   DB → file format adapters
│   │   ├── contracts/                   #   Data contracts
│   │   └── extractors/                  #   DB extractors
│   │
│   ├── domains/                         # 🏢 Business logic per domain
│   │   ├── daily/generate.py            #   Daily report (3300+ lines)
│   │   ├── performance/generate.py      #   Trip SLA / on-time / route compliance
│   │   ├── inventory/generate.py        #   Đối soát tồn kho KFM vs ABA
│   │   ├── nso/generate.py              #   New Store Opening tracker
│   │   └── weekly_plan/generate.py      #   Lịch về hàng siêu thị
│   │
│   ├── dashboard/deploy.py              # 🚀 Export → docs/ → GitHub Pages
│   │
│   ├── telegram/                        # 📱 Telegram automation
│   │   ├── trip_reminder.py             #   T2+T3 8AM incomplete trip remind
│   │   ├── batch_nso.py                 #   NSO notifications
│   │   ├── manage_group.py              #   Create/manage groups
│   │   └── mention_watcher.py           #   @mention watcher
│   │
│   ├── compose/                         # ✉️ Email auto-compose (Haraworks)
│   ├── lib/                             # 🛠 Shared utilities
│   └── external/                        # 🔗 External data management
│
├── docs/                                # 🌐 GitHub Pages Dashboard
│   ├── index.html                       #   Dashboard UI (auto-refresh 5 min)
│   └── data/                            #   JSON data files
│       ├── daily.json
│       ├── performance.json
│       ├── inventory.json
│       ├── nso.json
│       └── weekly.json
│
├── tools/                               # 🔨 Batch files (manual triggers)
│   ├── run-sync-realtime.bat
│   ├── run-trip-cutoff.bat
│   ├── run-trip-reminder.bat
│   ├── run-daily.bat
│   ├── run-performance.bat
│   ├── run-inventory.bat
│   ├── run-nso-scan.bat
│   ├── run-weekly-plan.bat
│   └── run-backup-inject.bat
│
├── output/state/                        # 💾 State management
│   ├── history.json                     #   65-day daily KPI history
│   ├── trip_cache_T{mm}.json            #   Monthly trip data (locked per file)
│   ├── .sync_state.json                 #   Last known DB counts + deploy hash
│   ├── silver/{DDMMYYYY}/lock.json      #   Cutoff freeze per date
│   └── trip_decisions/W{n}_{date}.json  #   Trip cutoff audit trail
│
└── agents/reference/                    # 📖 Documentation
    ├── project.md                       #   Architecture master doc
    └── data-sources.md                  #   DB table reference
```

---

## 🗄 Data Sources

### Databases

| DB | Host | Dùng cho |
|----|------|----------|
| **ClickHouse** | `103.140.248.114:32015` | Transfer (PT), Product weights |
| **StarRocks** | `103.140.248.114:39030` | Schedule (STHI), Trips |

### Tables

| Table | DB | Chứa gì |
|-------|-----|---------|
| `kf_transfer_mart` | ClickHouse | Phiếu chuyển hàng (75K+ rows/ngày) |
| `kf_product_static` | ClickHouse | Barcode → weight, name |
| `krc_dashboard_delivery_schedule` | StarRocks | Lịch giao hàng (750+ rows/ngày) |
| `__cdc_kfm_kf_inventories_kf_trips` | StarRocks | Trip status, driver, dates |

### File Dependencies (Manual)

| File | Đường dẫn | Cập nhật bởi |
|------|-----------|-------------|
| yeu_cau_chuyen | `G:\My Drive\DOCS\DAILY\yeu_cau_chuyen_hang_thuong\` | Download manual |
| Trip xlsx | `G:\My Drive\DOCS\DAILY\DS chi tiet chuyen xe\T{mm}.{yy}\` | Hệ thống KFM xuất |
| BÁO CÁO GIAO HÀNG (Thịt Cá) | `output/state/monthly_plan_T{mm}.json` | Manual (ABA logistics riêng) |
| ABA Master | `ABA Master Data.xlsx` | Manual |
| Master TL | Google Sheets (online) | Manual |

> [!NOTE]
> **Thịt Cá** (KHO ABA MIỀN ĐÔNG) dùng logistics riêng của ABA, không nằm trong KFM trip system.
> Trip reminder / trip cutoff **không bao gồm** Thịt Cá.
> Data Thịt Cá phải nhập manual từ BÁO CÁO GIAO HÀNG → `monthly_plan_T{mm}.json`.

---

## ⚙️ Nguyên Lý Hoạt Động

### 1. Smart Sync — Daily Report (Realtime)

```
Mỗi 15 phút (06:00 - 22:00):

  ┌──────────────────────────────────────┐
  │  1. FINGERPRINT CHECK (~1s)          │
  │     Transfer: COUNT + MAX(created)   │
  │               + SUM(quantity)        │
  │     Schedule: COUNT + MAX(updated)   │
  │                                      │
  │  Bắt: INSERT, DELETE, VÀ UPDATE      │
  │  (status đổi, quantity sửa)          │
  └──────────────┬───────────────────────┘
                 │
          Fingerprint thay đổi?
          ┌──────┴──────┐
          │             │
         YES           NO
          │             │
          ▼             ▼
  ┌───────────┐   ⏭ SKIP
  │ 2. FULL   │   (không tốn CPU)
  │ GENERATE  │
  │ (~5-30s)  │
  │           │
  │ DB query  │
  │ validate  │
  │ calc KPI  │
  │ save JSON │
  └─────┬─────┘
        │
  Output hash thay đổi?
  ┌──────┴──────┐
  │             │
 YES           NO
  │             │
  ▼             ▼
  ┌───────────┐  ⏭ SKIP
  │ 3. DEPLOY │  (save counts,
  │ (~10-30s) │   skip deploy)
  │           │
  │ git push  │
  │ → GitHub  │
  │   Pages   │
  └─────┬─────┘
        │
  ┌─────┴─────┐
  │ Save      │
  │ state:    │
  │ counts +  │
  │ hash      │
  └───────────┘
```

**Tại sao smart sync?**
- Query 75K rows mỗi 15 phút = tốn tài nguyên
- Fingerprint check chỉ ~1s, không tải data
- Bắt cả INSERT, DELETE, **VÀ UPDATE** (COUNT đơn giản sẽ miss UPDATE)
- Trung bình: **96 lần check/ngày × 1s = 96s tổng CPU/ngày**
- vs. full query mỗi lần: 96 × 30s = 48 phút CPU/ngày

**Anti-crash:**
- Process lock (`.sync.lock`) ngăn 2 sync chạy cùng lúc
- Stale lock auto-remove sau 10 phút (crash recovery)

### 2. Data Flow — Daily Report

```
                    ┌──────────────────┐
                    │   ClickHouse     │
                    │ kf_transfer_mart │──── 75K rows
                    └────────┬─────────┘     │
                             │               │
                    ┌────────┴─────────┐     │
                    │    StarRocks     │     │
                    │ krc_dashboard_   │     │
                    │ delivery_schedule│── 750 rows
                    └────────┬─────────┘     │
                             │               │
    ┌─────────────┐          │               │
    │ yeu_cau     │          │               │
    │ xlsx (local)│──────────┤               │
    └─────────────┘          │               │
                             ▼               │
                    ┌────────────────┐       │
                    │  generate.py   │ ◄─────┘
                    │                │
                    │ --source auto: │
                    │  DB first      │
                    │  file fallback │
                    │                │
                    │ Business Logic:│
                    │  KHO_MAP       │
                    │  ĐÔNG/MÁT split│
                    │  KSL Sáng/Tối  │
                    └───────┬────────┘
                            │
               ┌────────────┼────────────┐
               │            │            │
               ▼            ▼            ▼
          ┌─────────┐  ┌─────────┐  ┌─────────┐
          │ KPI PNG │  │ history │  │Telegram │
          │         │  │ .json   │  │ (8AM)   │
          └─────────┘  └────┬────┘  └─────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  deploy.py    │
                    │  → docs/data/ │
                    │  → git push   │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Dashboard    │
                    │  (GitHub      │
                    │   Pages)      │
                    │               │
                    │  auto-refresh │
                    │  mỗi 5 phút  │
                    └───────────────┘
```

### 3. Lock / Silver Snapshot

```
NGÀY 19/05:

06:00 ──── Sync bắt đầu ──────────────────────────────
  │   COUNT check → data mới → generate → deploy
  │   Dashboard: hiện số mới nhất (realtime)
  │
07:00 ──── COUNT lại → thêm data → generate → deploy
  │   Dashboard: cập nhật
  │
08:00 ──── CUTOFF ─────────────────────────────────────
  │   ✅ Lưu silver/19052026/lock.json
  │   ✅ Gửi Telegram (số final)
  │   ✅ history.json entry = FROZEN
  │
08:15 ──── Sync check → LOCKED → ⏭ SKIP
  │   Dashboard: giữ nguyên số 8AM
  │
  ... (skip cho hết ngày)
  │
22:00 ──── Sync tắt ───────────────────────────────────

NGÀY 20/05:
06:00 ──── New day → reset state → bắt đầu query ngày 20
           Lock ngày 19 vẫn còn → KHÔNG query lại ngày 19
```

**Silver snapshot = lightweight:**
- `lock.json` (~1KB): timestamp + hash → audit trail
- `history.json`: 65 ngày KPI tổng hợp → dashboard chart
- Không lưu raw 75K rows → tiết kiệm disk

### 4. Trip Performance — Weekly Flow

```
TUẦN W20 (12/05 → 18/05):

Trong tuần: Trips hoàn thành tự động → trip_cache_T05.json
            (incremental: chỉ đọc file xlsx MỚI, lock file cũ)

T2 25/05  08:00 ─── Trip Reminder (lần 1) ──────────
  │  StarRocks query: trips status IN (1,2)
  │  Telegram: "9 trips chưa hoàn thành"
  │  → Bạn dzí siêu thị hoàn thành trip
  │
T3 26/05  08:00 ─── Trip Reminder (lần 2) ──────────
  │  ⚠️ "CUTOFF 09:00 — xử lý trước khi generate"
  │
T3 26/05  09:00 ─── Trip Cutoff (auto) ──────────────
  │  Task Scheduler → query trips → Telegram notification:
  │     "✂️ Trip Cutoff Ready — W20"
  │     "9 trips chưa hoàn thành"
  │     "👉 Chạy run-trip-cutoff.bat"
  │
  │  Khi bạn sẵn sàng → chạy run-trip-cutoff.bat:
  │  1. Query trips chưa xong
  │  2. Notepad popup:
  │     ┌─────────────────────────────────────┐
  │     │ # GIỮ dòng = cho on-time           │
  │     │ # XÓA dòng = bỏ                    │
  │     │                                     │
  │     │ TRIP0000051625 | Phạm Hoàng Phúc    │
  │     │ TRIP0000051904 | Huỳnh Phúc         │
  │     └─────────────────────────────────────┘
  │  3. Save + đóng Notepad
  │  4. Lưu decisions: W20_2026-05-26.json
  │  5. generate.py đọc decisions:
  │     - "giữ" → trip_status = "Hoàn thành"
  │     - "bỏ" → loại khỏi report
  │  6. Generate performance report
  │  7. Deploy dashboard
  │
  ▼
  📊 Sếp họp → xem dashboard performance tab
```

### 5. Dashboard Auto-Refresh

```javascript
// docs/index.html — chạy mỗi 5 phút
setInterval(async () => {
    const resp = await fetch('data/daily.json?t=' + Date.now());
    const hash = computeHash(resp);
    if (hash !== lastHash) {
        loadTab(currentTab);  // reload tab data, no full page refresh
    }
}, 5 * 60 * 1000);
```

- **Không full reload** → không flicker
- Chỉ refresh tab data khi JSON thay đổi
- Cache-busting: `?t=timestamp`

---

## ⏰ Scheduled Tasks

| Task | Schedule | Script | Mô tả |
|------|----------|--------|-------|
| `KFM\SyncRealtime` | Mỗi 15 phút (06-22h) | `sync_realtime.py` | COUNT check → generate → deploy |
| `KFM\TripReminder` | T2+T3 08:00 | `trip_reminder.py` | Telegram remind trips chưa xong |
| `KFM\TripCutoff` | T3 09:00 | `trip_cutoff.py` | Notepad decide → generate perf |
| `KFM_InventoryWatch` | (existing) | inventory watcher | Inventory file watcher |

---

## 🔒 State Files

| File | Chứa gì | Lifetime |
|------|---------|----------|
| `.sync_state.json` | Last DB counts + deploy hash | Overwrite mỗi sync |
| `history.json` | 65-day KPI (STHI, PT, XE, Tons) | Rolling 65 ngày |
| `silver/{date}/lock.json` | Cutoff freeze + hash | Vĩnh viễn (~1KB/ngày) |
| `trip_cache_T{mm}.json` | Monthly trip rows (locked per file) | 1 file/tháng (~200KB) |
| `trip_decisions/W{n}.json` | Keep/exclude decisions | Vĩnh viễn (~2KB/tuần) |

**Tổng disk**: ~500KB/tháng — không cần cleanup.

---

## 📊 Domain Status

| Domain | Realtime? | Data Source | Sync |
|--------|-----------|-------------|------|
| **Daily** | ✅ Mỗi 15 phút | DB (auto) + file fallback | Smart sync |
| **Performance** | ✅ Weekly (T3 cutoff) | File + DB decisions | trip_cutoff.py |
| **Inventory** | ❌ Manual | File local | run-inventory.bat |
| **NSO** | ❌ Manual | Telegram scan | run-nso-scan.bat |
| **Weekly Plan** | ❌ Manual | master_schedule.json | run-weekly-plan.bat |

---

## 🛠 Manual Workflows

| Batch File | Khi nào dùng |
|-----------|-------------|
| `run-sync-realtime.bat` | Test sync thủ công |
| `run-trip-cutoff.bat` | Trip cutoff ngoài schedule |
| `run-trip-reminder.bat` | Test remind thủ công |
| `run-daily.bat` | Generate daily thủ công (full, có file) |
| `run-performance.bat` | Generate performance thủ công |
| `run-inventory.bat` | Inventory report |
| `run-nso-scan.bat` | NSO mail scan → deploy |
| `run-weekly-plan.bat` | Weekly plan → deploy |
| `run-backup-inject.bat` | Inject data sau cutoff |
