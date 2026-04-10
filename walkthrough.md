# Walkthrough: Transport Daily Report — Trend Chart Enhancements

## Overview
Replaced the text-based commentary table with visual trend charts for Items, Xe, and Tấn per warehouse, stacked vertically for a clean dashboard layout.

## Changes Made

### 1. Trend Charts per Kho (Items + Xe)
- Added `_build_trend_svg()` — reusable SVG chart renderer with bars (total) + colored lines (per kho)
- Charts: **Trend Tấn** · **Trend Items** · **Trend Xe** — each with kho breakdown lines + comparison notes

### 2. Comparison Notes (vs Hôm qua + vs LFL)
- Added `_fmt_delta_inline()` for colored ▲/▼ delta display
- Each chart shows: `Hôm nay: <value> · vs Hôm qua: ▲/▼ X% · vs LFL: ▲/▼ X%`

### 3. Historical Data Backfill
- Old history entries (13/03–25/03) lacked `sl_items`/`sl_xe` per kho
- Backfilled via tonnage proportion: `items_kho ≈ total_items × (tan_kho / total_tan)`
- Chart now shows kho lines for full 14-day range

### 4. Layout Restructure
- Removed "NHẬN XÉT TỰ ĐỘNG" title
- Stacked all charts vertically: **% Đóng góp → Trend Tấn → Trend Items → Trend Xe**
- Removed old `.commentary` wrapper — charts now flow in single `.charts` column

### 5. Robustness
- `_build_trend_svg()` skips kho lines when all values are 0 (handles missing data gracefully)
- Removed corrupted history entry (26/03/2026 partial load from KFM timeout)

## Files Modified
- [generate_report.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/generate_report.py) — main changes
- [history.json](file:///c:/Users/admin/Downloads/transport_daily_report/output/history.json) — backfilled per-kho data

## Final Report

![Report 26/03/2026](file:///c:/Users/admin/Downloads/transport_daily_report/output/BAO_CAO_26032026.png)

## Verification
- All data sources loaded successfully (150 xe, 528 STHI, 436,575 items, 149.59 tấn)
- All 3 trend charts render with kho breakdown lines and comparison notes
- Backed up to `G:\My Drive\DOCS\transport_daily_report\`
