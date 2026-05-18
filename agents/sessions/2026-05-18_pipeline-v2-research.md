# Session: Pipeline V2 — DB Research & Architecture
- **Date**: 2026-05-18
- **Agent**: Antigravity (Gemini)
- **Duration**: ~2 hours
- **Conversation ID**: d48d619d-cefc-42d1-9c43-4345bb42753c

---

## Objective
Migrate daily report data sources from file-based (Google Sheet/xlsx) to DB-first (StarRocks/ClickHouse) while preserving ALL domain logic.

## What Was Done

### Phase 1a: Pipeline Infrastructure ✅
- Created `script/data_pipeline/` with extractors, validators, state_manager
- `run.py` entry point, JSON schema contracts, silver locking

### Phase 1b: DB Research ✅
- Mapped all ClickHouse/StarRocks tables to daily report needs
- Confirmed `krc_dashboard_delivery_schedule` has 3 sources: KRC, DRY, THIT_CA
- Confirmed `kf_transfer_mart` has item-level transfer data (61K/day)
- Confirmed `kf_product_static` has barcode + weight (`base_net_weight`)

### Phase 1c: Branch ID Mapping ✅
Verified by exact row-count matching (17/05/2026):

```python
BRANCH_MAP = {
    "5fdc170ebd89c10006f15b7c": "KHO RAU CỦ",          # → KRC
    "61d4ffa72997ae0007f5ad19": "KHO ABA QUÁ CẢNH",    # → ĐÔNG/MÁT
    "639d80531a37c70007cbb7bf": "KHO ABA MIỀN ĐÔNG",   # → THỊT CÁ
}
```

### Phase 1d: Architecture Rules ✅
Created `agents/reference/architecture-rules.md`:
- Domain immutability (NEVER modify KHO_MAP, KPI formulas, etc.)
- Pipeline = data provider only
- Contract validation before silver
- Golden output regression tests

### Critical Corrections
- ❌ Initially modified `generate.py` with `--source` flag → **REVERTED**
- ✅ Correct approach: pipeline outputs xlsx at same paths, domain reads unchanged

## Key Decisions

1. **KSL-Sáng/Tối**: Keep reading from local `yeu_cau_chuyen_hang_thuong` file (DB timing doesn't meet 8:00 cutoff)
2. **KH ĐÔNG/MÁT schedule**: Keep local files (no DB source found)
3. **Transfer ĐÔNG/MÁT split**: Uses barcode classification from ABA Master Data xlsx, col E

## DB Connections

| DB | Host | User | Password | Database |
|---|---|---|---|---|
| StarRocks | 103.147.122.56:9030 | kfm_scm_lam_nguyen | QPYZfjWWhJcHNi5ab5Au | kfm_scm |
| ClickHouse | 103.140.248.114:32015 | scm_lam | xukco1-roghaB-fuqfum | kdb |

## Next Steps (Phase 2)

1. **2a: Domain contracts** — JSON schema for transfer xlsx columns (41 cols), schedule format
2. **2b: Golden output snapshot** — Run generate.py, capture KPI output as regression baseline
3. **2c: Adapter** — Build DB→xlsx writer that outputs at existing `TRANSFER_LOCAL` path

## Files Changed
- `agents/reference/architecture-rules.md` — NEW
- `.agents/workflows/daily-report.md` — Added architecture-rules reference
- `script/data_pipeline/*` — Pipeline infrastructure (Phase 1a, from prior session)
- `script/domains/daily/generate.py` — REVERTED (no changes)

## Blockers
- None. All DB access confirmed working.
