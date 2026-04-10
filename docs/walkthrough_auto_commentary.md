# Auto Commentary — Walkthrough

## What Was Done

Added an **"NHẬN XÉT TỰ ĐỘNG"** (Auto Commentary) section to the daily transport report image, rendered below the existing charts.

### Comparison Table (8 columns)
| Chỉ Tiêu | Hôm Nay | Hôm Qua | Δ vs Hôm Qua | LFL | Δ vs LFL | TB Ngày Thường | Δ vs TB Ngày Thường |

- **LFL** = Same weekday last week (Like-For-Like)
- **TB Ngày Thường** = Average of normal weekdays (total_tons > 130)
- Delta columns show ▲/▼ with color coding (green/red)

### AI Insights (4 categories)
1. Overall production vs average
2. Tấn/Xe efficiency analysis
3. Significant warehouse-level changes vs yesterday (>10% and >2T)
4. LFL comparison & multi-day trend detection (3+ consecutive days)

## Files Changed

- [generate_report.py](file:///c:/Users/admin/Downloads/transport_daily_report/script/generate_report.py) — Added `generate_commentary()` function (~100 lines) and CSS styles

## Verification

Report generated and verified for 26/03/2026:

![Final report with commentary](file:///c:/Users/admin/Downloads/transport_daily_report/output/BAO_CAO_26032026.png)

- ✅ Table shows all 8 columns with correct data
- ✅ Delta arrows color-coded (red ▼ for decrease, green ▲ for increase)
- ✅ 4 bullet insights generated correctly
- ✅ Image captures full content (viewport 1600×1800 at 3× scale)
