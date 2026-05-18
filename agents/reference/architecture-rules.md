# ARCHITECTURE RULES
# ==================
# These rules govern how the data pipeline interacts with domain logic.
# Violation of these rules will cause KPI drift and incorrect reports.

---

## 1. Domain Immutability

The following directories contain **LOCKED BUSINESS LOGIC**:

```
script/domains/*       ← PROTECTED
agents/prompts/*       ← DOMAIN SPECIFICATIONS
agents/workflows/*     ← EXECUTION CONTRACTS
```

### Allowed changes to domains:
- ✅ Add adapter/wrapper for datasource injection
- ✅ Add caching layer
- ✅ Add scheduling/orchestration
- ✅ Runtime optimization (e.g. faster file read)
- ✅ Fix bugs that produce incorrect output

### Forbidden changes:
- ❌ Changing KPI formulas
- ❌ Changing KHO_MAP or warehouse mapping rules
- ❌ Changing barcode classification logic
- ❌ Changing business grouping behavior
- ❌ Changing report output semantics
- ❌ Changing NSO logic
- ❌ Changing performance scoring

---

## 2. Pipeline Architecture

```
DB / APIs / Files
    ↓
Extractors (script/data_pipeline/extractors/)
    ↓
Bronze (raw, unvalidated)
    ↓
Contract Validators (script/data_pipeline/contracts/)
    ↓
Silver (validated, LOCKED)
    ↓
Adapters (output files at EXISTING paths in EXISTING formats)
    ↓
EXISTING DOMAIN LOGIC (script/domains/*)
    ↓
Dashboard / Mail / Telegram
```

### Key principle:
> Pipeline outputs files in the **SAME format** at the **SAME paths** that domains already read.
> Domains see no difference between pipeline-generated and manually-placed files.

---

## 3. Contract Validation

Every extractor output MUST pass contract validation before silver promotion:

```
contracts/
├── daily_transfer.contract.json     ← Transfer xlsx schema
├── daily_schedule.contract.json     ← KRC/DRY/THIT_CA schedule
├── daily_yeu_cau.contract.json      ← Yêu cầu chuyển
├── performance_trips.contract.json  ← Trip data
└── inventory.contract.json          ← Inventory data
```

Contract validates:
- Required columns (names + types)
- Warehouse code values
- Barcode format
- Null handling rules
- Row count minimums

---

## 4. Golden Output Tests

Before any migration goes live, snapshot current report output:

```
tests/golden/
├── daily_report_YYYYMMDD.json      ← Full KPI output
├── performance_YYYYMM.json         ← Performance report
└── inventory_YYYYMMDD.json         ← Inventory output
```

Regression test: `OLD_FLOW_OUTPUT == NEW_PIPELINE_OUTPUT`

If any of these differ (KPI, totals, warehouse mapping, classification):
→ **FAIL. Do not deploy.**

---

## 5. Migration Checklist

Before switching any data source:

- [ ] Read domain's workflow MD (`agents/workflows/`)
- [ ] Read domain's prompt MD (`agents/prompts/`)
- [ ] Run golden output comparison
- [ ] Verify contract validation passes
- [ ] Confirm output at existing file paths
- [ ] Test with `--date` for at least 3 different days (weekday, weekend, Monday)

---

## 6. Data Source Registry

| Domain | Source | Path | Format |
|---|---|---|---|
| daily/transfer | `G:\...\transfer\transfer_DDMMYYYY.xlsx` | xlsx, 41 columns | See contract |
| daily/yeu_cau | `G:\...\yeu_cau_chuyen_hang_thuong\*.xlsx` | xlsx | See contract |
| daily/krc_schedule | `KRC_SHEET_URL` (Google Sheet) | xlsx export | See contract |
| daily/kfm_schedule | `KFM_SHEET_URL` (Google Sheet) | xlsx export | See contract |
| daily/kh_dong | `G:\...\KH HÀNG ĐÔNG\*.xlsx` | xlsx | Local only |
| daily/kh_mat | `G:\...\KH HÀNG MÁT\*.xlsx` | xlsx | Local only |
| daily/kh_meat | `G:\...\KH MEAT\*.xlsx` | xlsx | Local only |
| daily/master_weight | `Sản phẩm thường - Thông tin cơ bản.xlsx` | xlsx | barcode → weight(g) |
| daily/master_aba | `Master Data.xlsx` | xlsx | barcode → ĐÔNG/MÁT |
