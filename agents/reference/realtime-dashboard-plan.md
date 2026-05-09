# ⚡ Real-time Dashboard — Implementation Plan

> **Created**: 08/05/2026  
> **Status**: Planning → Ready to implement  
> **Supersedes**: `data-pipeline-plan.md` (Phase 1+2 concepts), `restructure-plan.md` (Phase 2 ETL)  
> **Goal**: Dashboard tự động cập nhật mỗi 15-30 phút, data từ StarRocks + ClickHouse

---

## 0. Connectivity — ĐÃ VERIFIED

> [!TIP]
> **Không cần WireGuard/VPN.** Cả 2 DB đều public IP, đã test OK (08/05/2026 15:29 UTC).

| Service | Endpoint | Protocol | Status |
|---|---|---|---|
| **StarRocks** | `103.147.122.56:9030` | MySQL (pymysql) | ✅ Online, < 1s |
| **ClickHouse** | `103.140.248.114:32015` | HTTP API (requests) | ✅ Online, < 1s |

**Config files** (đã có):
- `config/mcp_starrocks.json` — host, port, user, password, database (`kfm_scm`)
- `config/mcp_clickhouse.json` — base_url, params (user, password, database `kdb`)

---

## 1. Data Inventory — Đã Audit & Verified

### 1.1 StarRocks (`kfm_scm`) — Real-time CDC

| Table | Nội dung | Volume/ngày | Freshness | Dùng cho |
|---|---|---|---|---|
| `krc_dashboard_delivery_schedule` | **Lịch giao TẤT CẢ KHO** (KRC, DRY, ĐÔNG_MÁT, ĐÔNG_LANH, THIT_CA) | ~700-800 rows/ngày | ~15 phút | **Daily**: STHI data |
| `__cdc_kfm_kf_inventories_kf_transfer_items` | Phiếu chuyển hàng | ~3,000-3,500/ngày | **Realtime CDC** (phút) | **Daily**: PT data |
| `__cdc_kfm_kf_inventories_kf_trips` | Chuyến xe | ~140-160/ngày | **Realtime CDC** | **Performance**: Trip analysis |
| `__cdc_kfm_kf_inventories_kf_trips_locations_items` | Chi tiết trip | ~thousands | Realtime CDC | **Performance**: Item-level |
| `krc_dashboard_barcodes` | Barcode info | Static | — | Lookup |
| `krc_dashboard_delivery_receipts` | Biên nhận | Event-driven | — | Future |

> [!IMPORTANT]
> **Discovery**: `krc_dashboard_delivery_schedule` chứa data **5 kho** (không chỉ KRC!)
> Columns: `ngay, source, diem_den, gio_den_dk, tuyen, tg_thuc_te, nvt, gio_load, gio_di`
> → **Thay thế cả Google Sheets LẪN local KH files** cho STHI!

**Data verified 08/05/2026:**
```
KRC:       173 rows
DRY:       125 rows  
ĐÔNG_MÁT:  175 rows
ĐÔNG_LANH:  80 rows
THIT_CA:   173 rows
Ngày mai (09/05): DONG_LANH=90, DRY=32 (đang được cập nhật)
```

### 1.2 ClickHouse (`kdb`) — Batch/Static

| Table | Nội dung | Volume | Refresh | Dùng cho |
|---|---|---|---|---|
| `kf_product_static` | Barcode → weight/unit | 28,898 SP | Stable | **Daily**: Master TL lookup |
| `kf_branch_location` | Danh sách ST + vị trí | 257 active | Weekly | **NSO/DSST**: Store lookup |
| `kf_transfer_mart` | Item-level transfer detail | ~100K/ngày (50M+ total) | Realtime | **Performance Phase 2** |
| `dict_dry_allocation_schedule` | DRY allocation | — | — | Future |

### 1.3 File-based (vẫn cần)

| Data | Source | Domain | Auto? |
|---|---|---|---|
| Yêu cầu chuyển hàng (KSL) | Local xlsx (`yeu_cau_chuyen_hang/`) | Daily (KSL PT) | ⚠️ File watcher |
| Đối soát tồn kho | Local xlsx (`ton_aba/doi_soat/`) | Inventory | ❌ Manual |
| NSO schedules | Telegram email scan | NSO | ❌ Event-driven |
| Master schedule | `data/master_schedule.json` | Weekly Plan | ❌ Manual |
| ABA barcode classification | Local `Master Data.xlsx` | Daily (ĐÔNG/MÁT split) | ⚠️ Kiểm tra StarRocks có không |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNC DAEMON (Task Scheduler)                  │
│                    Mỗi 15 phút, 06:00-22:00                    │
│                    sync_realtime.py                              │
└──────────┬──────────────────────────────────────────────────────┘
           │
    ┌──────▼──────┐    ┌──────────────┐    ┌──────────────┐
    │  StarRocks   │    │  ClickHouse   │    │ Local Files   │
    │  krc_schedule│    │  product_     │    │ yeu_cau.xlsx  │
    │  transfer_   │    │  static       │    │ (KSL only)    │
    │  items       │    │  (cached)     │    │               │
    │  kf_trips    │    │               │    │               │
    └──────┬───────┘    └──────┬────────┘    └──────┬────────┘
           │                   │                     │
    ┌──────▼───────────────────▼─────────────────────▼────────┐
    │                    BRONZE LAYER                           │
    │  storage/bronze/{DDMMYYYY}/                              │
    │  ├── schedule.json     (krc_dashboard_delivery_schedule) │
    │  ├── transfer.json     (kf_transfer_items)               │
    │  ├── trips.json        (kf_trips)                        │
    │  ├── yeu_cau.json      (local file, if exists)           │
    │  └── fetch_log.json    (timestamps, row counts)          │
    └──────────────────────────┬──────────────────────────────┘
                               │ validate
    ┌──────────────────────────▼──────────────────────────────┐
    │                    SILVER LAYER                           │
    │  storage/silver/{DDMMYYYY}/                              │
    │  ├── schedule.json     (validated, normalized)            │
    │  ├── transfer.json     (validated, with weight lookup)    │
    │  ├── trips.json        (validated)                        │
    │  └── lock.json         (🔒 timestamp, hash, version)     │
    └──────────────────────────┬──────────────────────────────┘
                               │ 
    ┌──────────────────────────▼──────────────────────────────┐
    │                    REPORT ENGINE                          │
    │  generate.py (modified to read silver/)                   │
    │  ├── Calculate KPI (STHI, PT, Xe, Tấn per kho)          │
    │  ├── Update output/state/history.json                    │
    │  └── Export docs/data/daily.json                         │
    └──────────────────────────┬──────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────┐
    │                    DEPLOY                                 │
    │  ├── git push → GitHub Pages (delay ~1-2 min)            │
    │  ├── Local HTTP :8080 (instant)                          │
    │  └── Telegram (only on final lock, ~19:00)               │
    └─────────────────────────────────────────────────────────┘
```

### Dashboard Auto-refresh

```javascript
// docs/index.html — thêm vào cuối
setInterval(async () => {
  const resp = await fetch('data/daily.json?t=' + Date.now());
  const newData = await resp.json();
  if (newData._hash !== window._lastHash) {
    window._lastHash = newData._hash;
    renderDailyTab(newData);  // re-render
    showToast('📊 Data mới!');
  }
}, 5 * 60 * 1000); // mỗi 5 phút
```

---

## 3. Timeline Vận Hành — Một Ngày

```
 05:00  ═══════════════════════════════════════════════════════
        CDC bắt đầu nhận transfer_items ngày mới
        
 06:00  ▶ SYNC #1  
        ├── StarRocks: krc_schedule D+1 (có thể chưa đủ)
        ├── StarRocks: transfer_items D (đang tăng)  
        └── Dashboard: partial report, badge "⏳ đang cập nhật"

 09:00  ▶ SYNC #2-4 (mỗi 15 phút)
        ├── transfer_items tăng dần (~50%)
        ├── KH files bắt đầu upload
        └── trips xuất hiện

 12:00  ▶ DRY Tối check_time
        ├── krc_schedule: DRY source có data D
        └── transfer_items ~60%

 15:00  ▶ DRY Sáng + ĐÔNG MÁT check_time  
        ├── krc_schedule: D+1 data sẵn sàng (DRY, ĐÔNG MÁT)
        └── transfer_items ~80%

 17:00  ▶ KRC + THỊT CÁ check_time
        ├── krc_schedule: ALL kho D+1 sẵn sàng
        └── transfer_items ~95%

 19:00  ▶ FINAL LOCK
        ├── transfer_items ~100%
        ├── Lock silver/ → lock.json
        ├── Generate final report
        ├── Send Telegram
        └── Deploy dashboard (final version)

 22:00  ═══════════════════════════════════════════════════════
        Scheduler ngừng. Restart 06:00 ngày hôm sau.
```

### Per-Domain Schedule

| Domain | Trigger | Interval | Active Hours | Data Sources | Deploy |
|---|---|---|---|---|---|
| **Daily** | Scheduler | 15 min | 06:00-22:00 | StarRocks + ClickHouse + local | Dashboard + TG (on lock) |
| **Performance** | Scheduler | 1x/ngày | 07:00 | StarRocks kf_trips + krc_schedule | Dashboard |
| **Inventory** | File watcher | 1 hour | 07:00-18:00 | Local xlsx (ton_aba/) | Dashboard + TG |
| **NSO** | On logon | 1x/logon | — | Telegram IMAP | Dashboard |
| **Weekly Plan** | Manual | On demand | — | master_schedule.json | Dashboard + TG |

---

## 4. Implementation Phases

### Phase 0: Storage + Config (Day 1)

```
transport_daily_report/
├── storage/                     ← MỚI
│   ├── .gitignore
│   ├── bronze/{DDMMYYYY}/       ← Raw fetch
│   ├── silver/{DDMMYYYY}/       ← Validated + locked
│   ├── master/                  ← Cached reference data  
│   │   ├── products.json        ← {barcode: weight_grams}
│   │   └── sync_state.json
│   └── logs/
│
├── data_pipeline/               ← MỚI
│   ├── __init__.py
│   ├── config.py                ← Load DB configs + storage paths
│   ├── sync_realtime.py         ← Main entry: mỗi 15 phút
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── _base.py             ← Extractor interface
│   │   ├── sr_schedule.py       ← StarRocks krc_dashboard_delivery_schedule
│   │   ├── sr_transfer.py       ← StarRocks kf_transfer_items  
│   │   ├── sr_trips.py          ← StarRocks kf_trips
│   │   ├── ch_products.py       ← ClickHouse kf_product_static
│   │   └── file_yeu_cau.py      ← Local yeu_cau xlsx
│   └── validators.py            ← Validate before promote to silver
```

**Tasks:**
- [ ] Create `storage/` directory structure + `.gitignore`
- [ ] Create `data_pipeline/__init__.py`, `config.py`
- [ ] Create `_base.py` extractor interface

### Phase 1: Extractors (Day 1-2)

**`sr_schedule.py`** — Lịch giao hàng (ALL kho)
```python
# Query StarRocks krc_dashboard_delivery_schedule
# WHERE ngay = '{target_date}'
# GROUP BY source → map source to report_kho:
#   KRC → KRC
#   DRY → KSL-SÁNG / KSL-TỐI (dựa vào gio_den_dk)
#   DONG_MAT → ĐÔNG MÁT  
#   DONG_LANH → ĐÔNG (subset)
#   THIT_CA → THỊT CÁ
# Output: [{kho, diem_den, tuyen, gio_den_dk}]
```

**`sr_transfer.py`** — Phiếu chuyển hàng
```python
# Query StarRocks __cdc_kfm_kf_inventories_kf_transfer_items
# WHERE DATE(created_at) = '{target_date}'
# Map from_branch_name → report_kho (KHO_MAP)
# Join with products.json for weight
# Output: [{kho, barcode, sl, tl_grams}]
```

**`ch_products.py`** — Master data (barcode → weight)
```python
# Query ClickHouse kf_product_static
# SELECT base_barcode, base_net_weight WHERE base_net_weight > 0
# Cache to storage/master/products.json
# Refresh: weekly hoặc khi cache > 7 days
# Output: {barcode: weight_grams}
```

**`sr_trips.py`** — Chuyến xe
```python
# Query StarRocks __cdc_kfm_kf_inventories_kf_trips
# WHERE DATE(created_at) = '{target_date}'
# Output: [{trip_id, route, status, timestamps}]
```

**`file_yeu_cau.py`** — KSL yêu cầu (file-based)
```python
# Scan YECAU_LOCAL for today's file
# Parse xlsx → [{kho: KSL-SÁNG/TỐI, barcode, sl, tl_grams}]
# Fallback khi StarRocks không có KSL data
```

**Tasks:**
- [ ] Implement `sr_schedule.py` + test with today's data
- [ ] Implement `sr_transfer.py` + verify row counts vs file
- [ ] Implement `ch_products.py` + compare with Google Sheet master
- [ ] Implement `sr_trips.py`
- [ ] Implement `file_yeu_cau.py` (adapt from existing code)

### Phase 2: Sync Engine (Day 2-3)

**`sync_realtime.py`** — Main orchestrator
```python
"""
Entry: python -m data_pipeline.sync_realtime [--date DD/MM/YYYY] [--force]
Runs every 15 min via Task Scheduler.
"""
def sync(date_str=None, force=False):
    date_str = date_str or tomorrow()  # D+1 for schedule
    date_tag = date_str.replace('/', '')
    
    # 1. Check if already locked
    if is_locked(date_tag) and not force:
        log(f"🔒 {date_tag} already locked, skip")
        return
    
    # 2. Refresh master if stale (> 7 days)
    if master_stale(days=7):
        ch_products.extract()
    master_tl = load_master()
    
    # 3. Extract all sources
    schedule_data = sr_schedule.extract(date_str)
    transfer_data = sr_transfer.extract(today(), master_tl)
    yeu_cau_data = file_yeu_cau.extract(today(), master_tl)
    trips_data = sr_trips.extract(today())
    
    # 4. Save bronze
    save_bronze(date_tag, {
        'schedule': schedule_data,
        'transfer': transfer_data,
        'yeu_cau': yeu_cau_data,
        'trips': trips_data,
    })
    
    # 5. Compare hash with last silver
    if not force and hash_unchanged(date_tag):
        log("No changes detected, skip report")
        return
    
    # 6. Validate + promote to silver
    promote_to_silver(date_tag)
    
    # 7. Generate report (only if data changed)
    generate_daily_from_silver(date_tag)
    
    # 8. Export dashboard JSON
    export_dashboard_data()
    
    # 9. Deploy
    deploy_dashboard()
    
    # 10. Lock if past cutoff (19:00)
    if past_cutoff():
        lock(date_tag)
        send_telegram_final()
```

**Tasks:**
- [ ] Implement `sync_realtime.py`
- [ ] Implement hash comparison (skip when no changes)
- [ ] Implement bronze → silver promotion with validation
- [ ] Implement lock mechanism

### Phase 3: Modify generate.py (Day 3)

```python
# Modify script/domains/daily/generate.py

def read_sthi_data(date_str, date_for_file, date_tag=None):
    """Silver-first: try storage/silver/ before Google Sheets."""
    silver_path = os.path.join(STORAGE, 'silver', date_tag, 'schedule.json')
    if os.path.exists(silver_path):
        print("  → STHI from silver/ (StarRocks)")
        return load_sthi_from_silver(silver_path)
    # Fallback: existing Google Sheets logic (unchanged)
    ...

def read_pt_data(date_str, master_tl, barcode_type=None):
    """Silver-first: try storage/silver/ before file xlsx."""
    silver_path = os.path.join(STORAGE, 'silver', date_tag, 'transfer.json')
    if os.path.exists(silver_path):
        print("  → PT from silver/ (StarRocks)")
        return load_pt_from_silver(silver_path)
    # Fallback: existing file logic (unchanged)
    ...
```

**Tasks:**
- [ ] Add silver-first logic to `read_sthi_data()`
- [ ] Add silver-first logic to `read_pt_data()`
- [ ] Add silver-first logic to `load_master_data()`
- [ ] Verify output matches existing reports

### Phase 4: Task Scheduler + Dashboard Refresh (Day 3-4)

**Windows Task Scheduler XML:**
```xml
<!-- sync_realtime_task.xml -->
<Task>
  <Triggers>
    <CalendarTrigger>
      <Repetition>
        <Interval>PT15M</Interval>
        <Duration>PT16H</Duration>
      </Repetition>
      <StartBoundary>2026-05-09T06:00:00</StartBoundary>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>-m data_pipeline.sync_realtime</Arguments>
      <WorkingDirectory>g:\My Drive\DOCS\transport_daily_report</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**Dashboard auto-refresh** (add to `docs/index.html`):
```javascript
// Auto-refresh data every 5 minutes
let _lastHash = null;
setInterval(async () => {
  try {
    const r = await fetch('data/daily.json?t=' + Date.now());
    const d = await r.json();
    if (d._hash && d._hash !== _lastHash) {
      _lastHash = d._hash;
      // Re-render daily tab
      if (typeof renderDaily === 'function') renderDaily(d);
      // Update "last updated" indicator
      document.querySelector('.meta-time').textContent = d._updated || '';
    }
  } catch(e) { /* silent */ }
}, 5 * 60 * 1000);
```

**Tasks:**
- [ ] Create Task Scheduler XML
- [ ] Create `tools/install-sync-task.bat`
- [ ] Add auto-refresh JS to dashboard
- [ ] Add "Last updated" indicator to topbar

---

## 5. Verification Plan

### Correctness Check

```
1. Run sr_schedule.py for today → compare row count with Google Sheet KRC
2. Run sr_transfer.py for today → compare with file transfer_08052026.xlsx
3. Run full sync_realtime.py → verify silver/ output
4. Run generate.py (silver-first) → compare KPI with manual run
5. Delete silver/ → verify fallback to Google Sheets/files
6. Run with --force → verify re-fetch works
```

### Data Mapping Verification

| Source (StarRocks) | Field | Maps to | Report field |
|---|---|---|---|
| `krc_schedule.source = 'KRC'` | diem_den | KRC | STHI count |
| `krc_schedule.source = 'DRY'` | diem_den + gio_den_dk | KSL-SÁNG/TỐI | STHI count |
| `krc_schedule.source = 'DONG_MAT'` | diem_den | ĐÔNG / MÁT | STHI count |
| `krc_schedule.source = 'THIT_CA'` | diem_den | THỊT CÁ | STHI count |
| `transfer_items.from_branch_name` | KHO_MAP | report_kho | PT items/tons |
| `kf_trips` | route, timestamps | — | Performance metrics |

### Open Questions (to verify during implementation)

- [ ] `krc_schedule` source `DONG_LANH` vs `DONG_MAT` — cần check overlap hay separate?
- [ ] `transfer_items` — column names trên CDC table khác với `kf_transfer_items` view?
- [ ] `krc_schedule.tg_thuc_te` — actual arrival time? Dùng cho Performance on-time?
- [ ] KSL `yeu_cau` data — có trên StarRocks không hay chỉ file?

---

## 6. Retention & Cleanup

| Layer | Retention | Size/ngày | Cleanup |
|---|---|---|---|
| Bronze | 7 ngày | ~200KB | Auto-delete |
| Silver | 90 ngày | ~200KB | Auto-delete |
| Master (products) | Latest only | ~500KB | Overwrite |
| Logs | 30 ngày | ~5KB | Auto-delete |

---

## 7. Related Documents

| File | Status | Notes |
|---|---|---|
| `data-pipeline-plan.md` | **Superseded** by this doc | Original Phase 1+2 concepts — extractors + bronze/silver design reused here |
| `restructure-plan.md` | **Partially done** | Phase 1 (tools/) done ✅. Phase 2 ETL → replaced by this realtime approach |
| `architecture.md` | **Needs update** after implementation | Add StarRocks/ClickHouse to data flow diagram |
