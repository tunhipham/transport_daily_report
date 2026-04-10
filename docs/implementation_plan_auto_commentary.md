# Add Auto Commentary Section to Daily Report

Add an automatic "NHẬN XÉT" (commentary) section below the existing charts in the report image. This section includes:
1. A comparison overview table with columns: Hôm nay, Hôm qua, LFL (cùng thứ tuần trước), TB ngày thường, and % change vs yesterday
2. AI-generated bullet-point insights (sản lượng, hiệu suất, kho breakdown, trends)

## Proposed Changes

### Report Script

#### [MODIFY] [generate_report.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/generate_report.py)

**1. Add `generate_commentary(result, history)` function (~line 500, before `build_report_html`):**

- Takes today's `result` dict and `history` list
- Finds yesterday's data and LFL data (same weekday last week, i.e. 7 days ago) from history
- Calculates averages across all weekday entries in history (excluding weekends if total < 130T)
- Builds an HTML table with rows: Tổng Tấn, Tổng Xe, Tổng Siêu Thị, Tổng Items, Tấn/Xe — each with columns: Hôm nay | Hôm qua | Δ vs HQ | LFL (tuần trước) | Δ vs LFL | TB ngày thường
- Generates bullet-point insights:
  - Overall production level vs average
  - Tấn/Xe efficiency analysis
  - Top kho changes vs yesterday
  - Multi-day trend detection (3+ days declining/increasing)
- Returns HTML string

**2. Update `build_report_html()` (~line 798):**

- Call `generate_commentary(result, history)` to get commentary HTML
- Insert it after the charts `</div>` and before `</body>`
- Add matching CSS styles (dark theme, same font/color palette)

## Verification Plan

### Automated Tests

Run the report generation for today and visually verify the output:

```
python -u script/generate_report.py --date 26/03/2026
```

Then open the output image `output/BAO_CAO_26032026.png` to verify the commentary section is visible and correct.
