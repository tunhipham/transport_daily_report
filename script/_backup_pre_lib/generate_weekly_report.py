"""
generate_weekly_report.py - Aggregate daily data into a weekly summary report
Usage: python script/generate_weekly_report.py [--week W12/2026] [--send]

Reads history.json and aggregates Mon-Sun data for the specified week.
If --week is not given, defaults to the most recent COMPLETE week.
"""
import os, sys, json, argparse
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REPORT_KHOS = ["KRC", "THỊT CÁ", "ĐÔNG MÁT", "KSL-SÁNG", "KSL-TỐI"]
KHO_COLORS = {"KRC": "#4caf50", "THỊT CÁ": "#e53935", "ĐÔNG MÁT": "#1e88e5",
              "KSL-SÁNG": "#ff9800", "KSL-TỐI": "#9c27b0"}

DAY_NAMES_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def load_history():
    path = os.path.join(BASE, "output", "history.json")
    if not os.path.exists(path):
        print(f"  ❌ history.json not found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.loads(f.read())


def get_week_range(week_str):
    """Parse 'W12/2026' → (monday_date, sunday_date, week_num, year)."""
    parts = week_str.upper().replace("W", "").split("/")
    week_num = int(parts[0])
    year = int(parts[1])
    # ISO week: Monday of week 1 contains Jan 4
    jan4 = datetime(year, 1, 4)
    start_of_w1 = jan4 - timedelta(days=jan4.isoweekday() - 1)
    monday = start_of_w1 + timedelta(weeks=week_num - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday, week_num, year


def find_latest_complete_week(history):
    """Find the most recent complete week (Mon-Sun) with at least 5 days of data."""
    dates = set()
    for h in history:
        dt = datetime.strptime(h["date"], "%d/%m/%Y")
        dates.add(dt.date())

    today = datetime.now().date()
    # Start from last Sunday and go backwards
    last_sunday = today - timedelta(days=(today.isoweekday() % 7))
    if last_sunday == today:
        last_sunday -= timedelta(days=7)

    for attempt in range(10):
        sunday = last_sunday - timedelta(weeks=attempt)
        monday = sunday - timedelta(days=6)
        week_dates = [monday + timedelta(days=i) for i in range(7)]
        days_with_data = sum(1 for d in week_dates if d in dates)
        if days_with_data >= 5:
            iso_year, iso_week, _ = monday.isocalendar()
            return f"W{iso_week}/{iso_year}"

    return None


def aggregate_week(history, monday, sunday):
    """Aggregate daily entries for Mon-Sun into weekly totals."""
    week_entries = []
    for h in history:
        dt = datetime.strptime(h["date"], "%d/%m/%Y")
        if monday <= dt <= sunday:
            week_entries.append(h)

    if not week_entries:
        return None, []

    # Sort by date
    week_entries.sort(key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y"))

    # Aggregate totals
    result = {
        "total_sthi": 0,
        "total_items": 0,
        "total_xe": 0,
        "total_tons": 0,
        "days_count": len(week_entries),
        "khos": {kho: {"san_luong_tan": 0, "sl_items": 0, "sl_xe": 0, "sthi": 0}
                 for kho in REPORT_KHOS},
    }

    for entry in week_entries:
        result["total_sthi"] += entry.get("total_sthi", 0)
        result["total_items"] += entry.get("total_items", 0)
        result["total_xe"] += entry.get("total_xe", 0)
        result["total_tons"] += entry.get("total_tons", 0)
        for kho in REPORT_KHOS:
            kdata = entry.get("khos", {}).get(kho, {})
            result["khos"][kho]["san_luong_tan"] += kdata.get("san_luong_tan", 0)
            result["khos"][kho]["sl_items"] += kdata.get("sl_items", 0)
            result["khos"][kho]["sl_xe"] += kdata.get("sl_xe", 0)

    # Estimate per-kho STHI from proportions (not stored per-kho in some entries)
    total_items_all = sum(result["khos"][k]["sl_items"] for k in REPORT_KHOS)
    if total_items_all > 0:
        for kho in REPORT_KHOS:
            ratio = result["khos"][kho]["sl_items"] / total_items_all
            result["khos"][kho]["sthi"] = round(result["total_sthi"] * ratio)

    return result, week_entries


def build_all_weeks_history(history):
    """Group all daily entries by ISO week and return list of aggregated weekly dicts."""
    from collections import defaultdict
    week_groups = defaultdict(list)
    for h in history:
        dt = datetime.strptime(h["date"], "%d/%m/%Y")
        iso_year, iso_week, _ = dt.isocalendar()
        key = (iso_year, iso_week)
        week_groups[key].append(h)

    weekly_history = []
    for (iso_year, iso_week), entries in sorted(week_groups.items()):
        # Get monday date for this ISO week
        jan4 = datetime(iso_year, 1, 4)
        start_of_w1 = jan4 - timedelta(days=jan4.isoweekday() - 1)
        monday = start_of_w1 + timedelta(weeks=iso_week - 1)
        sunday = monday + timedelta(days=6)

        agg, _ = aggregate_week(entries, monday, sunday)
        if agg:
            agg["week_label"] = f"W{iso_week}"
            agg["date_range"] = f"{monday.strftime('%d/%m')}–{sunday.strftime('%d/%m')}"
            weekly_history.append(agg)

    return weekly_history


def _fmt_delta_inline(today_v, compare_v):
    if compare_v is None or compare_v == 0:
        return "—"
    pct = (today_v - compare_v) / compare_v * 100
    if pct > 0:
        return f'<span style="color:#4caf50;font-weight:700">▲ +{pct:.1f}%</span>'
    elif pct < 0:
        return f'<span style="color:#ef5350;font-weight:700">▼ {pct:.1f}%</span>'
    return '<span style="color:#8a8f9a">— 0%</span>'


def _build_weekly_trend_svg(weekly_history, metric_key, total_key, title, fmt_fn):
    """Build SVG trend chart where each bar = one week's aggregated total."""
    chart_w = 780
    chart_h = 280
    pad_l = 60
    pad_r = 25
    pad_t = 25
    pad_b = 65

    plot_w = chart_w - pad_l - pad_r
    plot_h = chart_h - pad_t - pad_b

    n = len(weekly_history)
    if n == 0:
        return ""

    total_vals = [w[total_key] for w in weekly_history]
    max_val = max(total_vals) * 1.15 if max(total_vals) > 0 else 1

    svg = [f'<svg width="{chart_w}" height="{chart_h}" xmlns="http://www.w3.org/2000/svg">']

    # Grid lines
    for i in range(5):
        y = pad_t + plot_h * i / 4
        v = max_val * (4 - i) / 4
        svg.append(f'<line x1="{pad_l}" y1="{y:.0f}" x2="{chart_w-pad_r}" y2="{y:.0f}" stroke="#3a3f4a" stroke-width="0.5"/>')
        svg.append(f'<text x="{pad_l-5}" y="{y+4:.0f}" text-anchor="end" font-size="13" font-weight="700" fill="#b0b5c0">{fmt_fn(v)}</text>')

    inner_margin = plot_w / n * 0.5 if n > 1 else 0

    def xpos(i):
        return pad_l + inner_margin + (i * (plot_w - 2 * inner_margin) / max(n - 1, 1)) if n > 1 else pad_l + plot_w / 2

    def ypos(v):
        return pad_t + plot_h * (1 - v / max_val) if max_val > 0 else pad_t + plot_h

    # Bars
    bar_w = min((plot_w - 2 * inner_margin) / n * 0.55, 80) if n > 1 else 60
    for i, tv in enumerate(total_vals):
        x = xpos(i) - bar_w / 2
        y = ypos(tv)
        h = pad_t + plot_h - y
        svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="rgba(255,255,255,0.45)" stroke="rgba(255,255,255,0.60)" stroke-width="0.8"/>')

    # Kho lines
    has_kho_data = any(
        w.get("khos", {}).get(kho, {}).get(metric_key, 0) > 0
        for w in weekly_history for kho in REPORT_KHOS
    )
    if has_kho_data:
        for kho in REPORT_KHOS:
            color = KHO_COLORS[kho]
            kho_vals = [w.get("khos", {}).get(kho, {}).get(metric_key, 0) for w in weekly_history]
            pts = [(xpos(i), ypos(v)) for i, v in enumerate(kho_vals)]
            if len(pts) > 1:
                polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                svg.append(f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>')
            for x, y in pts:
                svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" stroke="#1e2029" stroke-width="1"/>')

    # Total dashed line + labels
    total_pts = [(xpos(i), ypos(v)) for i, v in enumerate(total_vals)]
    if len(total_pts) > 1:
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in total_pts)
        svg.append(f'<polyline points="{polyline}" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="2" stroke-dasharray="6,3" stroke-linejoin="round"/>')
    for i, (x, y) in enumerate(total_pts):
        v = total_vals[i]
        svg.append(f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" font-size="14" font-weight="800" fill="#ffffff">{fmt_fn(v)}</text>')

    # X-axis labels (week labels)
    for i, w in enumerate(weekly_history):
        x = xpos(i)
        svg.append(f'<text x="{x:.1f}" y="{pad_t+plot_h+18:.0f}" text-anchor="middle" font-size="14" font-weight="800" fill="#f0c060">{w["week_label"]}</text>')
        svg.append(f'<text x="{x:.1f}" y="{pad_t+plot_h+32:.0f}" text-anchor="middle" font-size="11" font-weight="600" fill="#8a8f9a">{w["date_range"]}</text>')

    # Legend
    leg_y = chart_h - 10
    leg_items = list(REPORT_KHOS) + ["TOTAL"]
    leg_colors = [KHO_COLORS[k] for k in REPORT_KHOS] + ["rgba(255,255,255,0.7)"]
    total_leg_w = len(leg_items) * 100
    leg_start = (chart_w - total_leg_w) / 2
    for j, (lk, lc) in enumerate(zip(leg_items, leg_colors)):
        lx = leg_start + j * 100
        if lk == "TOTAL":
            svg.append(f'<line x1="{lx:.0f}" y1="{leg_y}" x2="{lx+16:.0f}" y2="{leg_y}" stroke="{lc}" stroke-width="1.5" stroke-dasharray="4,2"/>')
        else:
            svg.append(f'<line x1="{lx:.0f}" y1="{leg_y}" x2="{lx+16:.0f}" y2="{leg_y}" stroke="{lc}" stroke-width="2"/>')
            svg.append(f'<circle cx="{lx+8:.0f}" cy="{leg_y}" r="2.5" fill="{lc}"/>')
        svg.append(f'<text x="{lx+20:.0f}" y="{leg_y+5:.0f}" font-size="12" font-weight="700" fill="#c8ccd0">{lk}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


def build_weekly_html(result, week_entries, week_label, date_range_str, prev_week_result, weekly_history=None):
    """Build HTML for weekly report."""
    total = result
    days = result["days_count"]

    # Summary cards
    cards_html = f"""
    <div class="cards">
      <div class="card"><div class="card-val">{total['total_tons']:.2f}</div><div class="card-lbl">TỔNG TẤN</div></div>
      <div class="card"><div class="card-val">{total['total_xe']}</div><div class="card-lbl">TỔNG XE</div></div>
      <div class="card"><div class="card-val">{total['total_sthi']}</div><div class="card-lbl">TỔNG SIÊU THỊ</div></div>
      <div class="card"><div class="card-val">{total['total_items']:,.0f}</div><div class="card-lbl">TỔNG ITEMS</div></div>
      <div class="card"><div class="card-val">{days}</div><div class="card-lbl">SỐ NGÀY</div></div>
    </div>"""

    # Averages card
    avg_tons = total['total_tons'] / days if days > 0 else 0
    avg_xe = total['total_xe'] / days if days > 0 else 0
    avg_items = total['total_items'] / days if days > 0 else 0
    avg_sthi = total['total_sthi'] / days if days > 0 else 0

    avg_html = f"""
    <div class="cards avg-cards">
      <div class="card avg"><div class="card-val avg-val">{avg_tons:.1f}</div><div class="card-lbl">TB TẤN/NGÀY</div></div>
      <div class="card avg"><div class="card-val avg-val">{avg_xe:.0f}</div><div class="card-lbl">TB XE/NGÀY</div></div>
      <div class="card avg"><div class="card-val avg-val">{avg_sthi:.0f}</div><div class="card-lbl">TB STHI/NGÀY</div></div>
      <div class="card avg"><div class="card-val avg-val">{avg_items:,.0f}</div><div class="card-lbl">TB ITEMS/NGÀY</div></div>
    </div>"""

    # Table rows
    rows_html = ""
    for kho in REPORT_KHOS:
        kd = total["khos"][kho]
        tan = kd["san_luong_tan"]
        items = kd["sl_items"]
        xe = kd["sl_xe"]
        sthi = kd["sthi"]
        txe = tan / xe if xe > 0 else 0
        ist = items / sthi if sthi > 0 else 0
        stxe = sthi / xe if xe > 0 else 0
        kgst = (tan * 1000) / sthi if sthi > 0 else 0
        color = KHO_COLORS.get(kho, '#666')
        rows_html += f"""    <tr>
      <td class="kho"><span class="dot" style="background:{color}"></span>{kho}</td>
      <td class="number">{sthi:,}</td>
      <td class="number">{items:,.0f}</td>
      <td class="number">{xe:,}</td>
      <td class="number">{tan:,.2f}</td>
      <td class="number kpi">{txe:.2f}</td>
      <td class="number kpi">{ist:,.0f}</td>
      <td class="number kpi">{stxe:.1f}</td>
      <td class="number kpi">{kgst:,.1f}</td>
    </tr>
"""

    # Totals
    txe_t = total['total_tons'] / total['total_xe'] if total['total_xe'] > 0 else 0
    ist_t = total['total_items'] / total['total_sthi'] if total['total_sthi'] > 0 else 0
    stxe_t = total['total_sthi'] / total['total_xe'] if total['total_xe'] > 0 else 0
    kgst_t = (total['total_tons'] * 1000) / total['total_sthi'] if total['total_sthi'] > 0 else 0

    # Donut chart
    donut_segments = []
    if total['total_tons'] > 0:
        cumulative = 0
        for kho in REPORT_KHOS:
            pct = total["khos"][kho]["san_luong_tan"] / total["total_tons"] * 100
            donut_segments.append((kho, pct, cumulative, KHO_COLORS.get(kho, '#666')))
            cumulative += pct

    donut_labels = ""
    stops = []
    for kho, pct, cum, color in donut_segments:
        stops.append(f"{color} {cum:.1f}% {cum+pct:.1f}%")
        donut_labels += f'<div class="leg-item"><span class="leg-color" style="background:{color}"></span>{kho} {pct:.1f}%</div>\n'
    donut_gradient = ", ".join(stops) if stops else "#555 0% 100%"

    # Trend charts — week-over-week comparison
    if not weekly_history:
        weekly_history = []
    tan_svg = _build_weekly_trend_svg(weekly_history, "san_luong_tan", "total_tons", "TREND TẤN THEO TUẦN", lambda v: f"{v:.0f}")
    items_svg = _build_weekly_trend_svg(weekly_history, "sl_items", "total_items", "TREND ITEMS THEO TUẦN", lambda v: f"{v/1000:.0f}K" if v >= 1000 else f"{v:.0f}")
    xe_svg = _build_weekly_trend_svg(weekly_history, "sl_xe", "total_xe", "TREND XE THEO TUẦN", lambda v: f"{v:.0f}")

    # WoW comparison notes
    tan_note = ""
    items_note = ""
    xe_note = ""
    if prev_week_result:
        pw = prev_week_result
        tan_note = f'<div class="cm-note">Tuần này: <b>{total["total_tons"]:.2f}</b> tấn &nbsp;·&nbsp; vs Tuần trước: {_fmt_delta_inline(total["total_tons"], pw["total_tons"])}</div>'
        items_note = f'<div class="cm-note">Tuần này: <b>{total["total_items"]:,.0f}</b> items &nbsp;·&nbsp; vs Tuần trước: {_fmt_delta_inline(total["total_items"], pw["total_items"])}</div>'
        xe_note = f'<div class="cm-note">Tuần này: <b>{total["total_xe"]:,}</b> xe &nbsp;·&nbsp; vs Tuần trước: {_fmt_delta_inline(total["total_xe"], pw["total_xe"])}</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #1e2029;
    display: inline-flex; flex-direction: column; align-items: center;
    padding: 28px 28px 36px; font-family: 'Segoe UI', Arial, sans-serif;
  }}
  .title {{
    background: linear-gradient(135deg, #1a4a6e, #2a6a9e);
    color: #fff; font-size: 26px; font-weight: bold;
    letter-spacing: 0.5px; padding: 18px 44px;
    text-align: center; border-radius: 10px; margin-bottom: 6px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.4);
  }}
  .subtitle {{
    font-size: 17px; color: #8a8f9a; margin-bottom: 18px;
    text-align: center; font-weight: 600;
  }}
  .cards {{
    display: flex; gap: 14px; margin-bottom: 14px;
  }}
  .card {{
    background: #282c38; border: 1px solid #3a3f4a; border-radius: 12px;
    padding: 14px 28px; text-align: center; min-width: 140px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }}
  .card-val {{ font-size: 30px; font-weight: 800; color: #38b854; }}
  .card-lbl {{ font-size: 13px; color: #8a8f9a; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .avg-cards .card {{ background: #1e2840; border-color: #2a4060; }}
  .avg-val {{ color: #7ab8f5 !important; font-size: 26px !important; }}
  .report {{
    border-collapse: collapse; font-size: 18px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.4); border-radius: 8px;
    overflow: hidden; margin-bottom: 20px;
  }}
  .report th, .report td {{
    border: 1px solid #3a3f4a; padding: 13px 20px;
    text-align: center; white-space: nowrap;
  }}
  .report thead th {{
    background: #1e3050; color: #7ab8f5;
    font-weight: 700; font-size: 16px;
    padding: 12px 20px; line-height: 1.3;
    text-transform: uppercase; letter-spacing: 0.3px;
  }}
  .report thead th.kpi-header {{
    background: #1e3050; color: #7ab8f5;
  }}
  .report thead .group-header {{
    font-size: 18px; letter-spacing: 0.5px; padding: 10px 20px;
  }}
  .report tbody td {{
    background: #252830; color: #d8dbe0;
    font-size: 18px; font-weight: 500;
  }}
  .report tbody tr:nth-child(even) td {{ background: #2a2d38; }}
  .report tbody td.kho {{
    font-weight: 700; text-align: left; padding-left: 18px;
    color: #e8eaef; font-size: 18px;
  }}
  .report tbody td.kpi {{
    color: #d8dbe0;
  }}
  .report .total-row td {{
    background: #1e3050; font-weight: 700;
    color: #7ab8f5; font-size: 18px;
    border-top: 2px solid #2a6a9e;
  }}
  .report .total-row td.kpi {{
    color: #7ab8f5;
  }}
  .number {{ font-variant-numeric: tabular-nums; }}
  .dot {{
    display: inline-block; width: 12px; height: 12px;
    border-radius: 50%; margin-right: 8px; vertical-align: middle;
  }}
  .charts {{
    display: flex; flex-direction: column; gap: 20px; align-items: stretch;
  }}
  .chart-box {{
    border: 1px solid #3a3f4a; border-radius: 12px; padding: 20px;
    background: #252830; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }}
  .chart-title {{
    font-size: 17px; font-weight: 700; color: #f0c060;
    text-align: center; margin-bottom: 14px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .donut-wrap {{
    display: flex; align-items: center; gap: 22px;
  }}
  .donut {{
    width: 180px; height: 180px; border-radius: 50%;
    background: conic-gradient({donut_gradient});
    position: relative; box-shadow: 0 0 20px rgba(0,0,0,0.3);
  }}
  .dhole {{
    position: absolute; top: 38px; left: 38px;
    width: 104px; height: 104px; border-radius: 50%;
    background: #252830; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }}
  .dhole-val {{ font-size: 28px; font-weight: 800; color: #ffffff; }}
  .dhole-lbl {{ font-size: 14px; color: #b0b5c0; text-transform: uppercase; font-weight: 700; }}
  .legend {{ font-size: 17px; color: #e8eaef; font-weight: 700; }}
  .leg-item {{ margin: 7px 0; display: flex; align-items: center; gap: 9px; white-space: nowrap; }}
  .leg-color {{ width: 16px; height: 16px; border-radius: 3px; flex-shrink: 0; }}
  .trend-box {{ min-width: 780px; }}
  .cm-note {{
    font-size: 16px; color: #d0d4da; text-align: center;
    padding: 8px 0 2px; font-weight: 500; line-height: 1.5;
  }}
</style></head>
<body>
<div class="title">BÁO CÁO TUẦN {week_label}</div>
<div class="subtitle">{date_range_str}</div>
{cards_html}
{avg_html}
<table class="report">
  <thead>
    <tr>
      <th rowspan="2">KHO</th>
      <th colspan="4" class="group-header">CHỈ TIÊU CHÍNH (CẢ TUẦN)</th>
      <th colspan="4" class="group-header kpi-header">CHỈ SỐ HIỆU SUẤT</th>
    </tr>
    <tr>
      <th>SỐ LƯỢNG<br>SIÊU THỊ</th><th>SỐ LƯỢNG<br>ITEMS</th>
      <th>SỐ LƯỢNG<br>XE</th><th>SẢN LƯỢNG<br>(TẤN)</th>
      <th class="kpi-header">TẤN/XE</th><th class="kpi-header">ITEMS<br>/SIÊU THỊ</th>
      <th class="kpi-header">SIÊU THỊ<br>/XE</th><th class="kpi-header">KG<br>/SIÊU THỊ</th>
    </tr>
  </thead>
  <tbody>
{rows_html}    <tr class="total-row">
      <td>TOTAL</td>
      <td class="number">{total['total_sthi']:,}</td>
      <td class="number">{total['total_items']:,.0f}</td>
      <td class="number">{total['total_xe']:,}</td>
      <td class="number">{total['total_tons']:,.2f}</td>
      <td class="number kpi">{txe_t:.2f}</td>
      <td class="number kpi">{ist_t:,.0f}</td>
      <td class="number kpi">{stxe_t:.1f}</td>
      <td class="number kpi">{kgst_t:,.1f}</td>
    </tr>
  </tbody>
</table>
<div class="charts">
  <div class="chart-box">
    <div class="chart-title">% ĐÓNG GÓP SẢN LƯỢNG</div>
    <div class="donut-wrap">
      <div class="donut"><div class="dhole"><span class="dhole-val">{total['total_tons']:,.1f}</span><span class="dhole-lbl">Tấn</span></div></div>
      <div class="legend">
{donut_labels}      </div>
    </div>
  </div>
  <div class="chart-box trend-box">
    <div class="chart-title">TREND SẢN LƯỢNG THEO TUẦN (TẤN)</div>
    {tan_svg}
    {tan_note}
  </div>
  <div class="chart-box trend-box">
    <div class="chart-title">TREND SỐ LƯỢNG ITEMS THEO TUẦN</div>
    {items_svg}
    {items_note}
  </div>
  <div class="chart-box trend-box">
    <div class="chart-title">TREND SỐ LƯỢNG XE THEO TUẦN</div>
    {xe_svg}
    {xe_note}
  </div>
</div>
</body></html>"""


def export_report_image(html_content, output_path):
    from playwright.sync_api import sync_playwright

    html_file = os.path.join(os.path.dirname(output_path), "_weekly_report_temp.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1600, "height": 2800},
            device_scale_factor=3,
        )
        page = context.new_page()
        page.goto(f"file:///{html_file.replace(os.sep, '/')}")
        page.wait_for_load_state("networkidle")

        body = page.query_selector("body")
        body.screenshot(path=output_path, type="png")
        browser.close()

    os.remove(html_file)
    print(f"  ✅ Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate weekly transport report")
    parser.add_argument("--week", help="Week to report, e.g. W12/2026 (default: latest complete week)")
    parser.add_argument("--send", action="store_true", help="Send to Telegram after generating")
    args = parser.parse_args()

    print("=" * 60)
    print("  WEEKLY REPORT")
    print("=" * 60)

    history = load_history()
    print(f"\n📊 History: {len(history)} daily entries")

    # Determine week
    if args.week:
        week_str = args.week
    else:
        week_str = find_latest_complete_week(history)
        if not week_str:
            print("  ❌ No complete week found in history!")
            sys.exit(1)

    monday, sunday, week_num, year = get_week_range(week_str)
    week_label = f"W{week_num}/{year}"
    date_range_str = f"{monday.strftime('%d/%m/%Y')} → {sunday.strftime('%d/%m/%Y')}"

    print(f"\n📅 Week: {week_label} ({date_range_str})")

    # Aggregate current week
    result, week_entries = aggregate_week(history, monday, sunday)
    if not result:
        print(f"  ❌ No data found for {week_label}!")
        sys.exit(1)

    print(f"  → {result['days_count']} days with data")
    print(f"  → {result['total_xe']} xe, {result['total_sthi']} STHI, {result['total_tons']:.2f} tấn")

    # Previous week for comparison
    prev_monday = monday - timedelta(days=7)
    prev_sunday = sunday - timedelta(days=7)
    prev_result, _ = aggregate_week(history, prev_monday, prev_sunday)
    if prev_result:
        prev_iso = prev_monday.isocalendar()
        print(f"  → Tuần trước (W{prev_iso[1]}): {prev_result['total_xe']} xe, {prev_result['total_tons']:.2f} tấn")

    # Build weekly history for trend charts
    weekly_history = build_all_weeks_history(history)
    print(f"  → {len(weekly_history)} weeks in history: {', '.join(w['week_label'] for w in weekly_history)}")

    # Build HTML
    print(f"\n🖼️  Rendering weekly report...")
    html = build_weekly_html(result, week_entries, week_label, date_range_str, prev_result, weekly_history)

    output_path = os.path.join(BASE, "output", f"BAO_CAO_TUAN_{week_label.replace('/', '_')}.png")
    export_report_image(html, output_path)

    print(f"\n📌 Review report tại: {output_path}")

    if args.send:
        # Re-use daily report's Telegram sending if available
        try:
            sys.path.insert(0, os.path.join(BASE, "script"))
            from generate_report import send_telegram
            send_telegram(output_path, f"📊 Báo cáo tuần {week_label}\n{date_range_str}")
            print("  ✅ Sent to Telegram!")
        except Exception as e:
            print(f"  ⚠️ Could not send to Telegram: {e}")

    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
