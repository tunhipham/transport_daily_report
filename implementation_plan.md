# Implementation Plan: Trend Chart Visualizations for Daily Report

## Goal
Replace the text commentary table with visual trend charts showing Items, Xe, and Tấn per warehouse over 14 days, with automated comparison insights.

## Proposed Changes

### Report Generator (`generate_report.py`)

#### Reusable SVG Chart Builder
- `_build_trend_svg(history, result, metric_key, total_key, title, fmt_fn)` — renders SVG with:
  - Gray translucent bars for total values
  - Colored polylines per kho (KRC, THỊT CÁ, ĐÔNG MÁT, KSL-SÁNG, KSL-TỐI)
  - Dashed white line for total trend
  - Value labels on bars, legend row at bottom
  - Graceful skip when per-kho data is all zeros

#### Comparison Note Generator
- `_fmt_delta_inline()` — colored ▲ green / ▼ red percentage deltas
- `generate_commentary()` returns `{tan_note, extra_charts}` dict with:
  - Tấn note (injected below existing Tấn chart)
  - Items + Xe chart HTML blocks

#### Layout Changes
- `.charts` container: `flex-direction: column` (vertical stack)
- Order: % Đóng góp → Trend Tấn → Trend Items → Trend Xe
- No wrapper/title — charts flow naturally

### History Data (`history.json`)
- Backfill `sl_items`/`sl_xe` per kho for entries 13/03–25/03
- Formula: `items_kho = total_items × (tan_kho / total_tan)`
- New entries (from 26/03 onward) store actual per-kho values

## Verification
- Run `python -u script/generate_report.py --date 26/03/2026`
- Confirm all 3 charts render with kho lines and comparison notes
- Confirm no flat-line artifacts for historical dates
