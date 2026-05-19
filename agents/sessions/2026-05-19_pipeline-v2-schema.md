# Session: Pipeline V2 — Schema Mapping & Trip Reminder
**Date**: 2026-05-19  
**Status**: ✅ Complete  

## Objective
Map ClickHouse/StarRocks table schemas to daily report requirements + build trip reminder bot.

## Completed

### Phase 2a: DB Schema Investigation
- Queried all 4 source tables with live data (hôm nay 19/05/2026)
- Confirmed `kf_transfer_mart` schema — 42 columns, ~88K rows/day
- Confirmed `krc_dashboard_delivery_schedule` — 5 sources (KRC, DRY, THIT_CA, DONG_MAT, DONG_LANH)
- Confirmed `kf_trip_locations_items` — status=3 is "completed", 0.01% date errors
- Confirmed `kf_product_static` — 100% join coverage with transfer data
- Discovered `KHO DRY` (`6234219eb35d1d00073793ab`) as 4th branch (9K rows/day)
- Created `config/data_sources.json` — machine-readable registry
- Created `agents/reference/data-sources.md` — human-readable reference

### Confirmed Business Rules
| Rule | Decision |
|------|----------|
| Transfer filter | `deleted=0 AND status!=6` |
| Quantity column | `transfer_quantity` only (ignore `received_quantity`) |
| Branch scope | 4 kho chính, bỏ 192 liên siêu thị |
| Schedule sources | KRC, DRY, THIT_CA, DONG_MAT (mát), DONG_LANH (đông) |
| KSL yêu cầu chuyển | Giữ file local (DB timing ko kịp cutoff 8:00) |
| Trip completed | `t_status = 3` |
| Trip actual time | `tl_arrival` (time only), ngày từ `t_departure` |
| Trip date filter | `toYear(t_departure) BETWEEN 2023 AND 2027` |

### Phase 2b: Golden Output Snapshot
- `output/state/history.json` already has 65 days of KPI baseline data
- No additional work needed — existing history IS the golden output

### Phase 2c: Trip Reminder Bot
- Created `script/telegram/trip_reminder.py`
- Queries ClickHouse for incomplete trips (status 1, 2) from previous week
- Compact summary format (by date + kho) for large numbers, detail for small
- Telegram personal chat (`chat_id: 5782090339`)
- Registered Windows Task Scheduler: `KFM\TripReminder` — every Monday 8:00 AM
- Batch file: `run-trip-reminder.bat`
- Config: `config/trip_reminder_task.xml`, `config/telegram.json` (trip_reminder entry)

## Files Created/Modified
- `config/data_sources.json` — NEW (machine-readable data source registry)
- `agents/reference/data-sources.md` — NEW (human-readable reference)
- `script/telegram/trip_reminder.py` — NEW (Monday 8AM reminder bot)
- `run-trip-reminder.bat` — NEW (batch launcher)
- `config/trip_reminder_task.xml` — NEW (Task Scheduler config)
- `config/telegram.json` — MODIFIED (added trip_reminder entry)

## Next Steps
1. **DB→xlsx Adapter** — Build adapter in `script/data_pipeline/adapters/` to transform DB JSON → legacy xlsx format
2. **Integration test** — Run adapter output through `generate.py` and compare with golden baseline
3. **Switchover** — Enable `--source db` mode in generate.py to use DB-backed data
