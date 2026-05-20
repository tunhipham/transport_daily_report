# Session: Pipeline V2 — DB Migration + Realtime Dashboard
**Date**: 2026-05-19  
**Status**: ✅ Complete — chờ test mai  

## Objective
Migrate daily reporting from file-based to DB-first architecture + setup realtime dashboard.

## Completed Today

### Phase 2a: DB Schema Investigation
- Queried all 4 source tables with live data (hôm nay 19/05/2026)
- Confirmed `kf_transfer_mart` schema — 42 columns, ~88K rows/day
- Confirmed `krc_dashboard_delivery_schedule` — 5 sources (KRC, DRY, THIT_CA, DONG_MAT, DONG_LANH)
- Confirmed `__cdc_kfm_kf_inventories_kf_trips` — StarRocks, trip status/driver
- Confirmed `kf_product_static` — 100% join coverage with transfer data
- Created `config/data_sources.json` — machine-readable registry
- Created `agents/reference/data-sources.md` — human-readable reference

### Phase 2b: Daily Realtime Pipeline
- Integrated StarRocks schedule query into `generate.py` (`_read_schedule_from_db`)
- Integrated ClickHouse transfer query into `generate.py` (`_read_transfer_from_db`)
- `--source auto` mode: DB-first, file fallback
- Regression test: <1% variance DB vs File (timing differences)

### Phase 2c: Smart Sync Orchestrator
- `sync_realtime.py` — fingerprint-based change detection:
  - Transfer: `COUNT + MAX(raw_created_at) + SUM(transfer_quantity)`
  - Schedule: `COUNT + MAX(updated_at)`
  - Catches INSERT, DELETE, AND UPDATE (~1s check)
- Process lock (`.sync.lock`) prevents concurrent writes
- Stale lock auto-remove after 10 min (crash recovery)
- Hash check on output → skip deploy if data unchanged

### Phase 2d: Lock / Silver Snapshot
- 8AM cutoff → `silver/{DDMMYYYY}/lock.json`
- Post-lock: sync SKIP, dashboard frozen
- `history.json` entry frozen for official report

### Phase 2e: Dashboard Auto-Refresh
- JS polling every 5 min in `docs/index.html`
- Smart reload: only refreshes active tab data, no flicker

### Phase 2f: Trip Performance Flow
- `trip_reminder.py` — T2+T3 8AM Telegram remind
  - Queries StarRocks for incomplete trips (status 1,2)
  - Shows: trip code + driver + PT codes + status
- `trip_cutoff.py` — T3 9AM cutoff
  - Scheduler: `--notify-only` → Telegram notification only (no GUI hang)
  - Manual: `run-trip-cutoff.bat` → Notepad popup → decide → generate
  - Decisions saved: `trip_decisions/W{n}_{date}.json`
  - `performance/generate.py` reads decisions → override trip status

### Phase 2g: Gemini Review Fixes
- ✅ COUNT(*) → fingerprint (catches UPDATEs)
- ✅ Notepad popup → Telegram notify (scheduler safe)
- ✅ Process lock (race condition prevention)

## Scheduled Tasks

| Task | Schedule | Script | Next Run |
|------|----------|--------|----------|
| `KFM\SyncRealtime` | 15 min (06-22h) | sync_realtime.py | 20/05 06:00 |
| `KFM\TripReminder` | T2+T3 08:00 | trip_reminder.py | 25/05 08:00 |
| `KFM\TripCutoff` | T3 09:00 | trip_cutoff.py --notify-only | 26/05 09:00 |

## Key Files Modified/Created

| File | Action |
|------|--------|
| `script/data_pipeline/sync_realtime.py` | Rewritten: smart fingerprint sync |
| `script/data_pipeline/trip_cutoff.py` | Created: cutoff + Notepad + Telegram |
| `script/telegram/trip_reminder.py` | Rewritten: StarRocks + T2/T3 dual |
| `script/domains/daily/generate.py` | Modified: DB source integration |
| `script/domains/performance/generate.py` | Modified: trip decisions injection |
| `docs/index.html` | Modified: auto-refresh JS |
| `config/sync_realtime_task.xml` | Created |
| `config/trip_reminder_task.xml` | Created |
| `config/trip_cutoff_task.xml` | Created |
| `agents/reference/system-overview.md` | Created: full system doc |
| `tools/run-trip-cutoff.bat` | Created |

## Manual Dependencies (Not Realtime)

| Data | Reason |
|------|--------|
| yeu_cau_chuyen xlsx | External collaborator, no DB |
| Thịt Cá (BÁO CÁO GIAO HÀNG) | ABA logistics riêng, không trong KFM trip |
| Inventory, NSO, Weekly Plan | Manual workflow phù hợp |

## Tomorrow Test Plan
- [ ] Verify SyncRealtime triggers at 06:00
- [ ] Check fingerprint skip behavior (data unchanged → skip)
- [ ] Verify data changes → generate → deploy → dashboard updates
- [ ] Confirm 8AM cutoff lock works
- [ ] Check sync log: `output/logs/sync_2026-05-20.log`
