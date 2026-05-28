# -*- coding: utf-8 -*-
"""
delivery_report_image.py — Generate delivery report HTML + pilot image & send via Telegram
============================================================================================
Main report: HTML page deployed to GitHub Pages → send link + summary caption
Pilot report (HTP/SCV): small image sent directly

Schedules:
  - KRC (day D) + KSL-Tối (day D-1): 09:00
  - ĐÔNG (day D): 16:30
  - MÁT (day D): 16:30
  - KSL-Sáng (day D): 15:00

Usage:
  python script/telegram/delivery_report_image.py --kho KRC --date 2026-05-28
  python script/telegram/delivery_report_image.py --kho KSL-Tối --date 2026-05-27
  python script/telegram/delivery_report_image.py --kho KRC --pilot --dry-run
"""
import os, sys, json, argparse, subprocess
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE, "docs")
DELIVERY_DIR = os.path.join(DOCS_DIR, "delivery")
OUTPUT_DIR = os.path.join(BASE, "output", "delivery_images")
PERF_JSON = os.path.join(DOCS_DIR, "data", "performance.json")
TG_CONFIG = os.path.join(BASE, "config", "telegram.json")

GITHUB_PAGES_BASE = "https://tunhipham.github.io/transport_daily_report/delivery"

PILOT_STORES = ["HTP", "SCV"]

# ── Color Palette (image) ──
BG_COLOR = (30, 30, 46)
HEADER_BG = (42, 42, 60)
ROW_EVEN = (35, 35, 50)
ROW_ODD = (30, 30, 46)
TITLE_BG = (20, 20, 35)
BORDER_COLOR = (58, 58, 76)
TEXT_COLOR = (224, 224, 224)
HEADER_TEXT = (240, 192, 96)
GREEN = (16, 185, 129)
RED = (239, 68, 68)
ORANGE = (249, 115, 22)
CYAN = (34, 211, 238)
WHITE = (255, 255, 255)
DIM_TEXT = (160, 160, 180)
TRIP_BG = (25, 25, 40)

KHO_ACCENTS = {
    "KRC": (108, 166, 255),
    "ĐÔNG": (76, 175, 80),
    "MÁT": (129, 212, 250),
    "KSL-Sáng": (255, 217, 102),
    "KSL-Tối": (196, 155, 255),
    "THỊT CÁ": (255, 159, 90),
}

KHO_ACCENT_HEX = {
    "KRC": "#6CA6FF",
    "ĐÔNG": "#4CAF50",
    "MÁT": "#81D4FA",
    "KSL-Sáng": "#FFD966",
    "KSL-Tối": "#C49BFF",
    "THỊT CÁ": "#FF9F5A",
}


# ── Fonts (for pilot image) ──
def get_fonts():
    return {
        "title": ImageFont.truetype("arialbd.ttf", 22),
        "subtitle": ImageFont.truetype("arial.ttf", 16),
        "header": ImageFont.truetype("arialbd.ttf", 15),
        "cell": ImageFont.truetype("arial.ttf", 14),
        "cell_bold": ImageFont.truetype("arialbd.ttf", 14),
        "trip_label": ImageFont.truetype("arialbd.ttf", 13),
        "small": ImageFont.truetype("arial.ttf", 12),
        "summary": ImageFont.truetype("arialbd.ttf", 18),
    }


# ── Data Loading ──
def load_tracking():
    with open(PERF_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tracking", {})


def get_kho_rows(tracking, kho, date_iso):
    dates_data = tracking.get("dates", {})
    day_data = dates_data.get(date_iso, {})
    return day_data.get(kho, [])


def sort_rows(rows):
    """Sort by trip then plan_time."""
    rows = list(rows)
    rows.sort(key=lambda r: (r.get("trip", ""), r.get("plan_time", "") or "23:59"))
    return rows


def group_by_trip(rows):
    """Group rows by trip, preserving order."""
    trips = {}
    trip_order = []
    for r in rows:
        tid = r.get("trip", "—")
        if tid not in trips:
            trips[tid] = {"plate": r.get("plate", ""), "driver": r.get("driver", ""), "rows": []}
            trip_order.append(tid)
        trips[tid]["rows"].append(r)
    return trips, trip_order


def calc_summary(rows):
    """Calculate summary stats."""
    total_giao = sum((r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0) for r in rows)
    total_nhan = sum((r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0) for r in rows)
    done = sum(1 for r in rows if r.get("arrival"))
    pending = len(rows) - done
    diff = total_nhan - total_giao
    return {
        "total_giao": total_giao,
        "total_nhan": total_nhan,
        "done": done,
        "pending": pending,
        "diff": diff,
        "total": len(rows),
    }


def format_date_vn(date_iso):
    parts = date_iso.split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return date_iso


def get_day_name(date_iso):
    weekdays = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    return weekdays[dt.weekday()]


def build_caption(kho, date_iso, summary, html_url=None, pilot_label=""):
    """Build Telegram caption with summary stats."""
    date_vn = format_date_vn(date_iso)
    day_name = get_day_name(date_iso)
    diff = summary["diff"]

    if diff == 0:
        status = "✅ ĐỦ"
    elif diff < 0:
        status = f"🔴 THIẾU {abs(diff)}"
    else:
        status = f"🟡 DƯ {diff}"

    lines = [
        f"📦 <b>Báo Cáo Giao Hàng — {kho}{pilot_label}</b>",
        f"📅 {day_name}, {date_vn}",
        f"",
        f"🚛 <b>{summary['done']}</b>/{summary['total']} điểm đã giao",
        f"📤 Giao: <b>{summary['total_giao']:,}</b>  →  📥 Nhận: <b>{summary['total_nhan']:,}</b>",
        f"📊 {status}",
    ]

    if html_url:
        lines.append(f"")
        lines.append(f"🔗 <a href=\"{html_url}\">Xem chi tiết</a>")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# HTML Report Generation
# ══════════════════════════════════════════════════════════════
def generate_html_report(kho, date_iso, rows):
    """Generate a standalone HTML report page with dark theme."""
    rows = sort_rows(rows)
    trips, trip_order = group_by_trip(rows)
    summary = calc_summary(rows)
    date_vn = format_date_vn(date_iso)
    day_name = get_day_name(date_iso)
    accent = KHO_ACCENT_HEX.get(kho, "#22D3EE")
    now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
    is_thitca = kho == "THỊT CÁ"

    diff = summary["diff"]
    if diff == 0:
        diff_html = '<span style="color:#10b981">✅ ĐỦ</span>'
    elif diff < 0:
        diff_html = f'<span style="color:#ef4444">🔴 THIẾU {abs(diff)}</span>'
    else:
        diff_html = f'<span style="color:#f97316">🟡 DƯ {diff}</span>'

    # Build table rows
    table_rows = ""
    stt = 0
    for trip_id in trip_order:
        td = trips[trip_id]
        trip_giao = sum((r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0) for r in td["rows"])
        trip_nhan = sum((r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0) for r in td["rows"])
        trip_done = sum(1 for r in td["rows"] if r.get("arrival"))

        if is_thitca:
            trip_col = 4
        else:
            trip_col = 7

        table_rows += f'''<tr class="trip-row">
  <td colspan="{trip_col}">
    <span class="trip-id">🚚 {trip_id}</span>
    <span class="trip-meta">{td["plate"]} • {td["driver"]}</span>
    <span class="trip-stats">✅{trip_done}/{len(td["rows"])} | G:{trip_giao} N:{trip_nhan}</span>
  </td>
</tr>\n'''

        for r in td["rows"]:
            stt += 1
            giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
            nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
            d = nhan - giao

            if d == 0 and giao > 0:
                st_cls, st_txt = "ok", "Đủ"
            elif d < 0:
                st_cls, st_txt = "bad", f"Thiếu {abs(d)}"
            elif d > 0:
                st_cls, st_txt = "warn", f"Dư {d}"
            else:
                st_cls, st_txt = "na", "—"

            arrival = r.get("arrival", "")
            arr_cls = "arr-done" if arrival else "arr-pending"
            arr_txt = arrival if arrival else "—"
            plan_txt = r.get("plan_time", "") or "—"

            row_cls = "even" if stt % 2 == 0 else "odd"

            if is_thitca:
                table_rows += f'''<tr class="{row_cls}">
  <td class="tc">{stt}</td>
  <td class="dest"><b>{r.get("dest", "—")}</b></td>
  <td class="tc">{plan_txt}</td>
  <td class="tc {arr_cls}">{arr_txt}</td>
</tr>\n'''
            else:
                table_rows += f'''<tr class="{row_cls}">
  <td class="tc">{stt}</td>
  <td class="dest"><b>{r.get("dest", "—")}</b></td>
  <td class="tc">{plan_txt}</td>
  <td class="tc {arr_cls}">{arr_txt}</td>
  <td class="tc">{giao if giao else "—"}</td>
  <td class="tc">{nhan if nhan else "—"}</td>
  <td class="tc st-{st_cls}">{st_txt}</td>
</tr>\n'''

    # Thitca header
    if is_thitca:
        thead = '''<tr><th>STT</th><th>Siêu Thị</th><th>Dự Kiến</th><th>Đến ST</th></tr>'''
    else:
        thead = '''<tr><th>STT</th><th>Siêu Thị</th><th>Dự Kiến</th><th>Đến ST</th><th>Giao</th><th>Nhận</th><th>Thiếu/Đủ</th></tr>'''

    html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Báo Cáo Giao Hàng — {kho} {date_vn}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:#1E1E2E; color:#E0E0E0; font-family:'Segoe UI',Arial,sans-serif; font-size:14px; padding:0 }}

  .header {{ background:#14141F; padding:16px 20px 12px; border-bottom:3px solid {accent} }}
  .header h1 {{ font-size:20px; color:{accent}; margin-bottom:4px }}
  .header .sub {{ color:#A0A0B4; font-size:13px }}
  .header .ts {{ float:right; color:#666; font-size:11px; margin-top:-32px }}

  .summary {{ background:#2A2A3C; padding:14px 20px; display:flex; gap:20px; flex-wrap:wrap; align-items:center; border-bottom:1px solid #3A3A4C }}
  .summary .s-item {{ display:flex; align-items:center; gap:6px }}
  .summary .s-val {{ font-weight:700; font-size:16px }}
  .summary .s-label {{ color:#A0A0B4; font-size:12px }}
  .summary .green {{ color:#10b981 }}
  .summary .red {{ color:#ef4444 }}
  .summary .white {{ color:#fff }}

  .search-bar {{ padding:10px 20px; background:#1E1E2E; display:flex; gap:8px; flex-wrap:wrap }}
  .search-bar input {{ background:#2A2A3C; border:1px solid #3A3A4C; color:#E0E0E0; border-radius:6px; padding:6px 12px; font-size:13px; width:200px }}
  .search-bar input::placeholder {{ color:#666 }}

  .wrap {{ overflow-x:auto; padding:0 }}
  table {{ width:100%; border-collapse:collapse; font-size:13px }}
  thead {{ position:sticky; top:0; z-index:2 }}
  th {{ background:#2A2A3C; color:#F0C060; padding:10px 8px; font-weight:700; text-align:center; border-bottom:2px solid {accent}; white-space:nowrap }}
  td {{ padding:8px 8px; border-bottom:1px solid #2A2A3C }}
  .tc {{ text-align:center }}
  .dest {{ font-weight:600; white-space:nowrap }}
  .even {{ background:#23233A }}
  .odd {{ background:#1E1E2E }}

  .trip-row {{ background:#16162A !important }}
  .trip-row td {{ padding:8px 12px; border-bottom:1px solid #3A3A4C }}
  .trip-id {{ color:{accent}; font-weight:700; font-size:12px; font-family:monospace }}
  .trip-meta {{ color:#A0A0B4; font-size:12px; margin-left:10px }}
  .trip-stats {{ float:right; color:#888; font-size:12px }}

  .arr-done {{ color:#10b981; font-weight:600 }}
  .arr-pending {{ color:#ef4444; font-weight:600 }}

  .st-ok {{ color:#10b981; font-weight:600 }}
  .st-bad {{ color:#ef4444; font-weight:600 }}
  .st-warn {{ color:#f97316; font-weight:600 }}
  .st-na {{ color:#666 }}

  .footer {{ background:#14141F; padding:12px 20px; text-align:center; color:#666; font-size:11px; border-top:2px solid {accent} }}

  @media(max-width:600px) {{
    .summary {{ padding:10px 12px; gap:12px }}
    .search-bar {{ padding:8px 12px }}
    .search-bar input {{ width:45% }}
    th, td {{ padding:6px 4px; font-size:12px }}
    .trip-meta {{ display:none }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>📦 Báo Cáo Giao Hàng — {kho}</h1>
  <div class="sub">{day_name}, {date_vn}</div>
  <div class="ts">Cập nhật: {now_str}</div>
</div>

<div class="summary">
  <div class="s-item"><span>🚛</span><span class="s-val white">{len(trips)}</span><span class="s-label">trip</span></div>
  <div class="s-item"><span>✅</span><span class="s-val green">{summary["done"]}</span><span class="s-label">đã giao</span></div>
  <div class="s-item"><span>❌</span><span class="s-val red">{summary["pending"]}</span><span class="s-label">chưa giao</span></div>
  <div class="s-item"><span>📤</span><span class="s-val white">{summary["total_giao"]:,}</span><span class="s-label">giao</span></div>
  <div class="s-item"><span>📥</span><span class="s-val white">{summary["total_nhan"]:,}</span><span class="s-label">nhận</span></div>
  <div class="s-item">{diff_html}</div>
</div>

<div class="search-bar">
  <input type="text" id="searchTrip" placeholder="🔍 Tìm Trip ID..." onkeyup="filterRows()">
  <input type="text" id="searchSthi" placeholder="🔍 Tìm Siêu Thị..." onkeyup="filterRows()">
</div>

<div class="wrap">
<table>
<thead>{thead}</thead>
<tbody id="tbody">
{table_rows}
</tbody>
</table>
</div>

<div class="footer">KFM Command Center • {summary["total"]} điểm giao • {len(trips)} chuyến</div>

<script>
function filterRows() {{
  const tq = document.getElementById('searchTrip').value.toLowerCase();
  const sq = document.getElementById('searchSthi').value.toLowerCase();
  let currentTrip = '';
  let tripVisible = false;
  const rows = document.querySelectorAll('#tbody tr');

  // Two passes: first mark data rows, then show/hide trip headers
  const tripRows = [];
  const dataRows = [];
  rows.forEach(r => {{
    if (r.classList.contains('trip-row')) {{
      tripRows.push({{ el: r, dataRows: [] }});
    }} else if (tripRows.length) {{
      tripRows[tripRows.length - 1].dataRows.push(r);
    }}
  }});

  tripRows.forEach(tr => {{
    const tripText = tr.el.textContent.toLowerCase();
    let anyVisible = false;
    tr.dataRows.forEach(dr => {{
      const dest = dr.querySelector('.dest');
      const destText = dest ? dest.textContent.toLowerCase() : '';
      const match = tripText.includes(tq) && destText.includes(sq);
      dr.style.display = match ? '' : 'none';
      if (match) anyVisible = true;
    }});
    tr.el.style.display = anyVisible ? '' : 'none';
  }});
}}
</script>
</body>
</html>'''

    os.makedirs(DELIVERY_DIR, exist_ok=True)
    kho_safe = kho.replace("-", "").replace(" ", "_")
    fname = f"{kho_safe}_{date_iso}.html"
    fpath = os.path.join(DELIVERY_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)

    url = f"{GITHUB_PAGES_BASE}/{fname}"
    print(f"  🌐 HTML saved: {fpath}")
    print(f"  🔗 URL: {url}")
    return fpath, url


# ══════════════════════════════════════════════════════════════
# Pilot Image Generation (small — only HTP/SCV)
# ══════════════════════════════════════════════════════════════
def generate_pilot_image(kho, date_iso, all_rows):
    """Generate a small image for pilot stores only."""
    fonts = get_fonts()
    pilot_rows = [r for r in all_rows if r.get("dest", "") in PILOT_STORES]
    if not pilot_rows:
        return None

    pilot_rows = sort_rows(pilot_rows)
    trips, trip_order = group_by_trip(pilot_rows)
    accent = KHO_ACCENTS.get(kho, CYAN)
    date_vn = format_date_vn(date_iso)
    day_name = get_day_name(date_iso)

    cols = [("STT", 50), ("Siêu Thị", 100), ("Dự Kiến", 80), ("Đến ST", 80), ("Giao", 65), ("Nhận", 65), ("Thiếu/Đủ", 90)]
    PADDING_X = 20
    ROW_HEIGHT = 32
    HEADER_HEIGHT = 36
    TITLE_HEIGHT = 70
    TRIP_ROW_HEIGHT = 30
    SUMMARY_HEIGHT = 50
    FOOTER_HEIGHT = 35

    total_width = sum(c[1] for c in cols) + PADDING_X * 2
    num_data_rows = len(pilot_rows)
    num_trip_headers = len(trips)
    content_height = TITLE_HEIGHT + SUMMARY_HEIGHT + HEADER_HEIGHT + num_trip_headers * TRIP_ROW_HEIGHT + num_data_rows * ROW_HEIGHT + FOOTER_HEIGHT + 20

    img = Image.new("RGB", (total_width, content_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    draw.rectangle([(0, 0), (total_width, TITLE_HEIGHT)], fill=TITLE_BG)
    draw.rectangle([(0, 0), (total_width, 4)], fill=accent)
    title = f"📦 PILOT — {kho} ({', '.join(PILOT_STORES)})"
    draw.text((PADDING_X, 14), title, fill=accent, font=fonts["title"])
    draw.text((PADDING_X, 42), f"{day_name}, {date_vn}", fill=DIM_TEXT, font=fonts["subtitle"])
    now_str = datetime.now().strftime("%H:%M %d/%m")
    ts_bbox = draw.textbbox((0, 0), now_str, font=fonts["small"])
    draw.text((total_width - PADDING_X - (ts_bbox[2] - ts_bbox[0]), 46), now_str, fill=DIM_TEXT, font=fonts["small"])

    y = TITLE_HEIGHT

    # Summary
    summary = calc_summary(pilot_rows)
    draw.rectangle([(0, y), (total_width, y + SUMMARY_HEIGHT)], fill=HEADER_BG)
    sx = PADDING_X
    for text, color in [
        (f"✅ {summary['done']}/{summary['total']}", GREEN),
        (f"  📤 {summary['total_giao']}", WHITE),
        (f" → 📥 {summary['total_nhan']}", WHITE),
    ]:
        draw.text((sx, y + 16), text, fill=color, font=fonts["summary"])
        bbox = draw.textbbox((0, 0), text, font=fonts["summary"])
        sx += bbox[2] - bbox[0]
    y += SUMMARY_HEIGHT

    # Header
    draw.rectangle([(0, y), (total_width, y + HEADER_HEIGHT)], fill=HEADER_BG)
    draw.line([(0, y + HEADER_HEIGHT - 1), (total_width, y + HEADER_HEIGHT - 1)], fill=accent, width=2)
    x = PADDING_X
    for col_name, col_w in cols:
        bbox = draw.textbbox((0, 0), col_name, font=fonts["header"])
        tw = bbox[2] - bbox[0]
        draw.text((x + (col_w - tw) // 2, y + 10), col_name, fill=HEADER_TEXT, font=fonts["header"])
        x += col_w
    y += HEADER_HEIGHT

    # Rows
    stt = 0
    for trip_id in trip_order:
        td = trips[trip_id]
        draw.rectangle([(0, y), (total_width, y + TRIP_ROW_HEIGHT)], fill=TRIP_BG)
        draw.line([(0, y), (total_width, y)], fill=BORDER_COLOR)
        trip_giao = sum((r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0) for r in td["rows"])
        trip_nhan = sum((r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0) for r in td["rows"])
        draw.text((PADDING_X + 5, y + 8), f"🚚 {trip_id} | {td['plate']} | {td['driver']}", fill=accent, font=fonts["trip_label"])
        ts_text = f"G:{trip_giao} N:{trip_nhan}"
        ts_bbox = draw.textbbox((0, 0), ts_text, font=fonts["trip_label"])
        draw.text((total_width - PADDING_X - (ts_bbox[2] - ts_bbox[0]) - 5, y + 8), ts_text, fill=DIM_TEXT, font=fonts["trip_label"])
        y += TRIP_ROW_HEIGHT

        for r in td["rows"]:
            stt += 1
            row_bg = ROW_EVEN if stt % 2 == 0 else ROW_ODD
            draw.rectangle([(0, y), (total_width, y + ROW_HEIGHT)], fill=row_bg)
            draw.line([(0, y + ROW_HEIGHT - 1), (total_width, y + ROW_HEIGHT - 1)], fill=BORDER_COLOR)

            giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
            nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
            d = nhan - giao
            if d == 0 and giao > 0:
                st_txt, st_col = "Đủ", GREEN
            elif d < 0:
                st_txt, st_col = f"Thiếu {abs(d)}", RED
            elif d > 0:
                st_txt, st_col = f"Dư {d}", ORANGE
            else:
                st_txt, st_col = "—", DIM_TEXT

            arrival = r.get("arrival", "")
            arr_col = GREEN if arrival else RED
            arr_txt = arrival or "—"
            plan_txt = r.get("plan_time", "") or "—"

            cell_values = [
                (str(stt), TEXT_COLOR), (r.get("dest", "—"), WHITE), (plan_txt, DIM_TEXT),
                (arr_txt, arr_col), (str(giao) if giao else "—", TEXT_COLOR),
                (str(nhan) if nhan else "—", TEXT_COLOR), (st_txt, st_col),
            ]
            x = PADDING_X
            for ci, ((_, col_w), (val, color)) in enumerate(zip(cols, cell_values)):
                font = fonts["cell_bold"] if ci == 1 else fonts["cell"]
                bbox = draw.textbbox((0, 0), val, font=font)
                draw.text((x + (col_w - (bbox[2] - bbox[0])) // 2, y + 9), val, fill=color, font=font)
                x += col_w
            y += ROW_HEIGHT

    # Footer
    draw.rectangle([(0, y), (total_width, y + FOOTER_HEIGHT)], fill=TITLE_BG)
    draw.rectangle([(0, content_height - 3), (total_width, content_height)], fill=accent)
    ft = f"KFM Command Center • PILOT {', '.join(PILOT_STORES)}"
    bbox = draw.textbbox((0, 0), ft, font=fonts["small"])
    draw.text(((total_width - (bbox[2] - bbox[0])) // 2, y + 10), ft, fill=DIM_TEXT, font=fonts["small"])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    kho_safe = kho.replace("-", "").replace(" ", "_")
    fname = f"delivery_{kho_safe}_{date_iso}_pilot.png"
    fpath = os.path.join(OUTPUT_DIR, fname)
    img.save(fpath, "PNG", quality=95)
    print(f"  📸 Pilot image: {fpath} ({img.width}x{img.height})")
    return fpath


# ── Git deploy ──
def deploy_html():
    """Quick git add + commit + push for delivery HTML files."""
    print("\n📤 Deploying HTML to GitHub Pages...")
    try:
        subprocess.run(["git", "add", "docs/delivery/"], cwd=BASE, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", f"📦 Delivery report — {datetime.now().strftime('%d/%m/%Y %H:%M')}"],
            cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30
        )
        if "nothing to commit" in (result.stdout + result.stderr):
            print("  ℹ No changes to commit")
            return True
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60
        )
        if result.returncode == 0:
            print("  ✅ Deployed!")
            return True
        else:
            print(f"  ❌ Push failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Deploy error: {e}")
        return False


# ── Telegram ──
def send_telegram_message(bot_token, chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }, timeout=30)
    r.raise_for_status()
    return r.json()


def send_telegram_image(bot_token, chat_id, image_path, caption=""):
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(image_path, "rb") as f:
        r = requests.post(url, data={
            "chat_id": chat_id, "caption": caption, "parse_mode": "HTML",
        }, files={"photo": f}, timeout=30)
        r.raise_for_status()
    return r.json()


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Generate delivery report HTML/image & send Telegram")
    parser.add_argument("--kho", action="append", required=True,
                        help="Kho: KRC, ĐÔNG, MÁT, KSL-Sáng, KSL-Tối, THỊT CÁ")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today, KSL-Tối=yesterday)")
    parser.add_argument("--dry-run", action="store_true", help="Generate only, don't send/deploy")
    parser.add_argument("--chat-id", default=None, help="Override chat_id")
    parser.add_argument("--pilot", action="store_true", help="Also generate pilot image for HTP/SCV")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n{'═'*60}")
    print(f"  📸 Delivery Report Generator")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'═'*60}\n")

    print("📂 Loading tracking data...")
    tracking = load_tracking()
    if not tracking or not tracking.get("dates"):
        print("  ❌ No tracking data!")
        sys.exit(1)
    print(f"  ✅ Latest: {tracking.get('latest_date', '?')}")

    with open(TG_CONFIG, "r", encoding="utf-8") as f:
        tg_cfg = json.load(f)
    bot_token = ""
    for key in tg_cfg:
        if isinstance(tg_cfg[key], dict) and "bot_token" in tg_cfg[key]:
            bot_token = tg_cfg[key]["bot_token"]
            break
    chat_id = args.chat_id or tg_cfg.get("trip_reminder", {}).get("chat_id", "")

    results = []  # (type, kho, date, path_or_url, caption)

    for kho in args.kho:
        date_iso = args.date or (yesterday if kho == "KSL-Tối" else today)

        print(f"\n{'─'*50}")
        print(f"  🏭 {kho} — {date_iso}")
        print(f"{'─'*50}")

        rows = get_kho_rows(tracking, kho, date_iso)
        if not rows:
            print(f"  ⚠ No data for {kho} on {date_iso}")
            continue
        print(f"  📊 {len(rows)} rows")

        # Main HTML report
        html_path, html_url = generate_html_report(kho, date_iso, rows)
        summary = calc_summary(rows)
        caption = build_caption(kho, date_iso, summary, html_url=html_url)
        results.append(("html", kho, date_iso, html_url, caption))

        # Pilot image
        if args.pilot:
            pilot_rows = [r for r in rows if r.get("dest", "") in PILOT_STORES]
            if pilot_rows:
                print(f"\n  🧪 Pilot report ({len(pilot_rows)} stores)...")
                pilot_path = generate_pilot_image(kho, date_iso, rows)
                if pilot_path:
                    pilot_summary = calc_summary(pilot_rows)
                    pilot_caption = build_caption(kho, date_iso, pilot_summary, pilot_label=f" (PILOT {', '.join(PILOT_STORES)})")
                    results.append(("image", kho, date_iso, pilot_path, pilot_caption))

    if not results:
        print("\n  ❌ Nothing generated!")
        sys.exit(1)

    if args.dry_run:
        print(f"\n  [DRY RUN] {len(results)} report(s) generated.")
        for typ, kho, d, path, cap in results:
            print(f"    [{typ}] {kho} {d}")
            print(f"    Caption:\n{cap}\n")
        return

    # Deploy HTML
    has_html = any(t == "html" for t, *_ in results)
    if has_html:
        deploy_html()

    # Send Telegram
    print(f"\n📤 Sending {len(results)} report(s) to Telegram...")
    for typ, kho, d, path_or_url, caption in results:
        try:
            if typ == "html":
                send_telegram_message(bot_token, chat_id, caption)
                print(f"  ✅ Sent link: {kho} {d}")
            else:
                send_telegram_image(bot_token, chat_id, path_or_url, caption)
                print(f"  ✅ Sent image: {kho} {d}")
        except Exception as e:
            print(f"  ❌ Failed {kho}: {e}")

    print(f"\n{'═'*60}")
    print(f"  ✅ Done! {len(results)} report(s)")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
