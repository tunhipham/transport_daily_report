# -*- coding: utf-8 -*-
"""
delivery_report_image.py — Generate delivery report HTML + pilot image & send via Telegram
============================================================================================
Main report: HTML page deployed to GitHub Pages → send link + summary caption
Pilot report (HTP/SCV): Selenium screenshot of mini HTML → send as image

Columns: Trip | Siêu Thị | Giao | Nhận | Đủ/Thiếu/Dư

Usage:
  python script/telegram/delivery_report_image.py --kho KRC --date 2026-05-28
  python script/telegram/delivery_report_image.py --kho KSL-Tối --date 2026-05-27
  python script/telegram/delivery_report_image.py --kho KRC --pilot --dry-run
"""
import os, sys, json, argparse, subprocess
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE, "docs")
DELIVERY_DIR = os.path.join(DOCS_DIR, "delivery")
OUTPUT_DIR = os.path.join(BASE, "output", "delivery_images")
PERF_JSON = os.path.join(DOCS_DIR, "data", "performance.json")
TG_CONFIG = os.path.join(BASE, "config", "telegram.json")

GITHUB_PAGES_BASE = "https://tunhipham.github.io/transport_daily_report/delivery"

PILOT_STORES = ["HTP", "SCV"]

KHO_ACCENT_HEX = {
    "KRC": "#6CA6FF",
    "ĐÔNG": "#4CAF50",
    "MÁT": "#81D4FA",
    "KSL-Sáng": "#FFD966",
    "KSL-Tối": "#C49BFF",
    "THỊT CÁ": "#FF9F5A",
}


# ── Data Loading ──
def load_tracking():
    with open(PERF_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tracking", {})


def get_kho_rows(tracking, kho, date_iso):
    return tracking.get("dates", {}).get(date_iso, {}).get(kho, [])


def sort_rows(rows):
    rows = list(rows)
    rows.sort(key=lambda r: (r.get("trip", ""), r.get("plan_time", "") or "23:59"))
    return rows


def group_by_trip(rows):
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
    total_giao = sum((r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0) for r in rows)
    total_nhan = sum((r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0) for r in rows)
    done = sum(1 for r in rows if r.get("arrival"))
    pending = len(rows) - done
    return {
        "total_giao": total_giao, "total_nhan": total_nhan,
        "done": done, "pending": pending,
        "diff": total_nhan - total_giao, "total": len(rows),
    }


def format_date_vn(date_iso):
    p = date_iso.split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else date_iso


def get_day_name(date_iso):
    weekdays = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    return weekdays[datetime.strptime(date_iso, "%Y-%m-%d").weekday()]


def build_caption(kho, date_iso, summary, html_url=None, pilot_label=""):
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
        lines += ["", f"🔗 <a href=\"{html_url}\">Xem chi tiết</a>"]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Shared CSS + HTML table builder (used by both full report & pilot)
# ══════════════════════════════════════════════════════════════
def _get_report_css(accent):
    """Dark theme CSS matching KFM Command Center dashboard."""
    return f'''
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:#0F172A; color:#E2E8F0; font-family:'Segoe UI',Arial,sans-serif; font-size:14px }}

  .header {{ background:linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding:20px 24px 16px; border-bottom:3px solid {accent} }}
  .header h1 {{ font-size:20px; color:{accent}; margin-bottom:6px; letter-spacing:0.3px }}
  .header .sub {{ color:#94A3B8; font-size:14px }}
  .header .ts {{ float:right; color:#64748B; font-size:11px; margin-top:-36px }}

  .summary {{ background:#1E293B; padding:16px 24px; display:flex; gap:24px; flex-wrap:wrap; align-items:center; border-bottom:1px solid #334155 }}
  .s-item {{ display:flex; align-items:center; gap:8px }}
  .s-val {{ font-weight:700; font-size:18px }}
  .s-label {{ color:#94A3B8; font-size:13px }}
  .green {{ color:#10B981 }}
  .red {{ color:#EF4444 }}
  .white {{ color:#F1F5F9 }}

  .search-bar {{ padding:12px 24px; background:#0F172A; display:flex; gap:10px; flex-wrap:wrap }}
  .search-bar input {{ background:#1E293B; border:1px solid #334155; color:#E2E8F0; border-radius:8px; padding:8px 14px; font-size:13px; width:220px; outline:none; transition:border-color .2s }}
  .search-bar input:focus {{ border-color:{accent} }}
  .search-bar input::placeholder {{ color:#64748B }}

  .wrap {{ overflow-x:auto }}
  table {{ width:100%; border-collapse:collapse; font-size:14px }}
  thead {{ position:sticky; top:0; z-index:2 }}
  th {{ background:#1E293B; color:#F0C060; padding:12px 12px; font-weight:700; text-align:center; border-bottom:2px solid {accent}; white-space:nowrap; font-size:14px }}
  td {{ padding:10px 12px; border-bottom:1px solid #1E293B; font-size:14px }}
  .tc {{ text-align:center }}
  .dest {{ font-weight:700; white-space:nowrap; font-size:15px }}
  .trip-cell {{ color:{accent}; font-family:monospace; font-size:12px; white-space:nowrap }}
  .even {{ background:#1E293B }}
  .odd {{ background:#0F172A }}

  .arr-done {{ color:#10B981; font-weight:600 }}
  .arr-pending {{ color:#EF4444; font-weight:600 }}
  .st-ok {{ color:#10B981; font-weight:700 }}
  .st-bad {{ color:#EF4444; font-weight:700 }}
  .st-warn {{ color:#F97316; font-weight:700 }}
  .st-na {{ color:#475569 }}

  .footer {{ background:#0B1120; padding:14px 24px; text-align:center; color:#475569; font-size:12px; border-top:2px solid {accent} }}

  @media(max-width:600px) {{
    .summary {{ padding:12px 16px; gap:16px }}
    .search-bar {{ padding:10px 16px }}
    .search-bar input {{ width:45% }}
    th, td {{ padding:8px 6px; font-size:13px }}
    .trip-meta {{ display:none }}
  }}
'''


def _build_table_rows(rows, is_thitca=False):
    """Build flat HTML table rows — Trip | Siêu Thị | Giao | Nhận | Đủ/Thiếu/Dư."""
    html = ""

    for stt, r in enumerate(rows, 1):
        giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
        nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
        d = nhan - giao

        if d == 0 and giao > 0:
            st_cls, st_txt = "ok", "Đủ ✅"
        elif d < 0:
            st_cls, st_txt = "bad", f"Thiếu {abs(d)} ❌"
        elif d > 0:
            st_cls, st_txt = "warn", f"Dư {d} ⚠️"
        else:
            st_cls, st_txt = "na", "—"

        row_cls = "even" if stt % 2 == 0 else "odd"
        trip_id = r.get("trip", "") or "—"

        if is_thitca:
            html += f'''<tr class="{row_cls}">
  <td class="trip-cell">{trip_id}</td>
  <td class="dest">{r.get("dest", "—")}</td>
  <td class="tc">{giao if giao else "—"}</td>
  <td class="tc st-{st_cls}">{st_txt}</td>
</tr>\n'''
        else:
            html += f'''<tr class="{row_cls}">
  <td class="trip-cell">{trip_id}</td>
  <td class="dest">{r.get("dest", "—")}</td>
  <td class="tc">{giao if giao else "—"}</td>
  <td class="tc">{nhan if nhan else "—"}</td>
  <td class="tc st-{st_cls}">{st_txt}</td>
</tr>\n'''

    return html


# ══════════════════════════════════════════════════════════════
# Full HTML Report (deployed to GitHub Pages)
# ══════════════════════════════════════════════════════════════
def generate_html_report(kho, date_iso, rows):
    rows = sort_rows(rows)
    summary = calc_summary(rows)
    date_vn = format_date_vn(date_iso)
    day_name = get_day_name(date_iso)
    accent = KHO_ACCENT_HEX.get(kho, "#22D3EE")
    now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
    is_thitca = kho == "THỊT CÁ"
    n_trips = len(set(r.get("trip", "") for r in rows if r.get("trip")))

    diff = summary["diff"]
    if diff == 0:
        diff_html = '<span style="color:#10b981;font-weight:700">✅ ĐỦ</span>'
    elif diff < 0:
        diff_html = f'<span style="color:#ef4444;font-weight:700">🔴 THIẾU {abs(diff)}</span>'
    else:
        diff_html = f'<span style="color:#f97316;font-weight:700">🟡 DƯ {diff}</span>'

    if is_thitca:
        thead = '<tr><th>Trip</th><th>Siêu Thị</th><th>Giao</th><th>Đủ/Thiếu/Dư</th></tr>'
    else:
        thead = '<tr><th>Trip</th><th>Siêu Thị</th><th>Giao</th><th>Nhận</th><th>Đủ/Thiếu/Dư</th></tr>'

    table_rows = _build_table_rows(rows, is_thitca)

    html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Báo Cáo Giao Hàng — {kho} {date_vn}</title>
<style>{_get_report_css(accent)}</style>
</head>
<body>
<div class="header">
  <h1>📦 BÁO CÁO GIAO HÀNG — {kho}</h1>
  <div class="sub">{day_name}, {date_vn}</div>
  <div class="ts">Cập nhật: {now_str}</div>
</div>

<div class="summary">
  <div class="s-item"><span>🚛</span><span class="s-val white">{n_trips}</span><span class="s-label">trip</span></div>
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

<div class="footer">KFM Command Center • {summary["total"]} điểm giao • {n_trips} chuyến</div>

<script>
function filterRows() {{
  const tq = document.getElementById('searchTrip').value.toLowerCase();
  const sq = document.getElementById('searchSthi').value.toLowerCase();
  const rows = document.querySelectorAll('#tbody tr');
  rows.forEach(r => {{
    const text = r.textContent.toLowerCase();
    const match = text.includes(tq) && text.includes(sq);
    r.style.display = match ? '' : 'none';
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
    print(f"  🌐 HTML: {fpath}")
    print(f"  🔗 URL: {url}")
    return fpath, url


# ══════════════════════════════════════════════════════════════
# Pilot Image (PIL — high quality, clear, large fonts)
# ══════════════════════════════════════════════════════════════
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate_pilot_image(kho, date_iso, all_rows):
    """Generate a beautiful, clear PIL image for HTP & SCV pilot stores."""
    from PIL import Image, ImageDraw, ImageFont

    pilot_rows = [r for r in all_rows if r.get("dest", "") in PILOT_STORES]
    if not pilot_rows:
        return None, None

    pilot_rows = sort_rows(pilot_rows)
    trips, trip_order = group_by_trip(pilot_rows)
    summary = calc_summary(pilot_rows)
    date_vn = format_date_vn(date_iso)
    day_name = get_day_name(date_iso)
    now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
    accent = _hex_to_rgb(KHO_ACCENT_HEX.get(kho, "#22D3EE"))

    # ── Fonts (large for clarity) ──
    f_title = ImageFont.truetype("arialbd.ttf", 28)
    f_subtitle = ImageFont.truetype("arial.ttf", 18)
    f_summary = ImageFont.truetype("arialbd.ttf", 22)
    f_sum_label = ImageFont.truetype("arial.ttf", 16)
    f_header = ImageFont.truetype("arialbd.ttf", 20)
    f_cell = ImageFont.truetype("arial.ttf", 20)
    f_cell_bold = ImageFont.truetype("arialbd.ttf", 20)
    f_status = ImageFont.truetype("arialbd.ttf", 20)
    f_trip = ImageFont.truetype("arialbd.ttf", 16)
    f_footer = ImageFont.truetype("arial.ttf", 14)

    # ── Colors ──
    BG = (15, 23, 42)        # #0F172A
    HEADER_BG = (30, 41, 59) # #1E293B
    ROW_A = (30, 41, 59)
    ROW_B = (15, 23, 42)
    TRIP_BG = (11, 17, 32)   # #0B1120
    BORDER = (51, 65, 85)    # #334155
    TEXT = (226, 232, 240)    # #E2E8F0
    TEXT_DIM = (148, 163, 184)
    TEXT_DARK = (71, 85, 105)
    GOLD = (240, 192, 96)
    GREEN = (16, 185, 129)
    RED = (239, 68, 68)
    ORANGE = (249, 115, 22)
    WHITE = (241, 245, 249)

    # ── Layout constants ──
    W = 820
    PAD = 30
    TITLE_H = 100
    SUMMARY_H = 70
    HDR_H = 50
    ROW_H = 48
    TRIP_H = 44
    FOOTER_H = 40

    # Column widths: Trip | Siêu Thị | Giao | Nhận | Đủ/Thiếu/Dư
    cols = [("Trip", 200), ("Siêu Thị", 130), ("Giao", 120), ("Nhận", 120), ("Đủ/Thiếu/Dư", 230)]
    table_w = sum(c[1] for c in cols)
    table_x = (W - table_w) // 2

    # Calculate height
    n_rows = len(pilot_rows)
    total_h = TITLE_H + SUMMARY_H + HDR_H + n_rows * ROW_H + FOOTER_H + 10

    # ── Create image ──
    img = Image.new("RGB", (W, total_h), BG)
    draw = ImageDraw.Draw(img)

    # ── Title bar ──
    draw.rectangle([(0, 0), (W, TITLE_H)], fill=HEADER_BG)
    draw.rectangle([(0, 0), (W, 5)], fill=accent)

    title = f"BÁO CÁO GIAO HÀNG HTP & SCV_{kho}_{date_vn.replace('/', '.')}"
    draw.text((PAD, 20), title, fill=accent, font=f_title)
    draw.text((PAD, 58), f"{day_name}, {date_vn}", fill=TEXT_DIM, font=f_subtitle)

    # Timestamp right
    ts_bb = draw.textbbox((0, 0), now_str, font=f_footer)
    draw.text((W - PAD - (ts_bb[2] - ts_bb[0]), 66), now_str, fill=TEXT_DARK, font=f_footer)

    y = TITLE_H

    # ── Summary bar ──
    draw.rectangle([(0, y), (W, y + SUMMARY_H)], fill=HEADER_BG)
    draw.line([(0, y + SUMMARY_H - 1), (W, y + SUMMARY_H - 1)], fill=BORDER)

    diff = summary["diff"]
    if diff == 0:
        st_text, st_color = "ĐỦ", GREEN
    elif diff < 0:
        st_text, st_color = f"THIẾU {abs(diff)}", RED
    else:
        st_text, st_color = f"DƯ {diff}", ORANGE

    sx = PAD
    sum_items = [
        (f"{summary['done']}/{summary['total']}", WHITE, "đã giao"),
        (f"{summary['total_giao']}", WHITE, "giao"),
        (f"{summary['total_nhan']}", WHITE, "nhận"),
        (st_text, st_color, ""),
    ]
    for val, color, label in sum_items:
        draw.text((sx, y + 14), val, fill=color, font=f_summary)
        vbb = draw.textbbox((0, 0), val, font=f_summary)
        vw = vbb[2] - vbb[0]
        if label:
            draw.text((sx + vw + 6, y + 20), label, fill=TEXT_DIM, font=f_sum_label)
            lbb = draw.textbbox((0, 0), label, font=f_sum_label)
            sx += vw + 6 + (lbb[2] - lbb[0]) + 30
        else:
            sx += vw + 30

    y += SUMMARY_H

    # ── Table header ──
    draw.rectangle([(0, y), (W, y + HDR_H)], fill=HEADER_BG)
    draw.line([(0, y + HDR_H - 2), (W, y + HDR_H - 2)], fill=accent, width=3)

    x = table_x
    for col_name, col_w in cols:
        bb = draw.textbbox((0, 0), col_name, font=f_header)
        tw = bb[2] - bb[0]
        draw.text((x + (col_w - tw) // 2, y + 13), col_name, fill=GOLD, font=f_header)
        x += col_w

    y += HDR_H

    # ── Data rows (flat table) ──
    for row_idx, r in enumerate(pilot_rows, 1):
        row_bg = ROW_A if row_idx % 2 == 0 else ROW_B
        draw.rectangle([(0, y), (W, y + ROW_H)], fill=row_bg)
        draw.line([(0, y + ROW_H - 1), (W, y + ROW_H - 1)], fill=(30, 41, 59))

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
            st_txt, st_col = "—", TEXT_DARK

        trip_id = r.get("trip", "") or "—"

        cell_vals = [
            (trip_id, accent, f_trip),
            (r.get("dest", "—"), WHITE, f_cell_bold),
            (str(giao) if giao else "—", TEXT, f_cell),
            (str(nhan) if nhan else "—", TEXT, f_cell),
            (st_txt, st_col, f_status),
        ]

        x = table_x
        for (val, color, font), (_, col_w) in zip(cell_vals, cols):
            bb = draw.textbbox((0, 0), val, font=font)
            tw = bb[2] - bb[0]
            draw.text((x + (col_w - tw) // 2, y + 12), val, fill=color, font=font)
            x += col_w

        y += ROW_H

    # ── Footer ──
    draw.rectangle([(0, y), (W, y + FOOTER_H)], fill=TRIP_BG)
    draw.rectangle([(0, total_h - 4), (W, total_h)], fill=accent)
    ft = f"KFM Command Center  •  PILOT HTP & SCV  •  {n_rows} điểm"
    bb = draw.textbbox((0, 0), ft, font=f_footer)
    draw.text(((W - (bb[2] - bb[0])) // 2, y + 12), ft, fill=TEXT_DARK, font=f_footer)

    # ── Save ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    kho_safe = kho.replace("-", "").replace(" ", "_")
    fname = f"pilot_{kho_safe}_{date_iso}.png"
    fpath = os.path.join(OUTPUT_DIR, fname)
    img.save(fpath, "PNG")
    print(f"  📸 Pilot image: {fpath} ({img.width}x{img.height})")
    return fpath, summary


# ── Git deploy ──
def deploy_html():
    print("\n📤 Deploying HTML to GitHub Pages...")
    try:
        subprocess.run(["git", "add", "docs/delivery/"], cwd=BASE, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", f"📦 Delivery report — {datetime.now().strftime('%d/%m/%Y %H:%M')}"],
            cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30
        )
        if "nothing to commit" in (result.stdout + result.stderr):
            print("  ℹ No changes")
            return True
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60
        )
        if result.returncode == 0:
            print("  ✅ Deployed!")
            return True
        print(f"  ❌ Push failed: {result.stderr}")
        return False
    except Exception as e:
        print(f"  ❌ Deploy error: {e}")
        return False


# ── Telegram ──
def send_telegram_message(bot_token, chat_id, text):
    import requests
    r = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False,
    }, timeout=30)
    r.raise_for_status()
    return r.json()


def send_telegram_image(bot_token, chat_id, image_path, caption=""):
    import requests
    with open(image_path, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"photo": f}, timeout=30)
    if "PHOTO_INVALID_DIMENSIONS" in r.text or "PHOTO_SAVE_FILE_INVALID" in r.text:
        print("  ⚠ Photo too large, sending as document...")
        with open(image_path, "rb") as f2:
            r = requests.post(f"https://api.telegram.org/bot{bot_token}/sendDocument",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"document": f2}, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Generate delivery report HTML/image & send Telegram")
    parser.add_argument("--kho", action="append", required=True,
                        help="Kho: KRC, ĐÔNG, MÁT, KSL-Sáng, KSL-Tối, THỊT CÁ")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Generate only, don't send/deploy")
    parser.add_argument("--chat-id", default=None, help="Override chat_id")
    parser.add_argument("--pilot", action="store_true", help="Generate pilot image for HTP/SCV")
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

        # Full HTML report
        html_path, html_url = generate_html_report(kho, date_iso, rows)
        summary = calc_summary(rows)
        caption = build_caption(kho, date_iso, summary, html_url=html_url)
        results.append(("html", kho, date_iso, html_url, caption))

        # Pilot image
        if args.pilot:
            pilot_rows = [r for r in rows if r.get("dest", "") in PILOT_STORES]
            if pilot_rows:
                print(f"\n  🧪 Pilot ({len(pilot_rows)} stores)...")
                pilot_path, pilot_summary = generate_pilot_image(kho, date_iso, rows)
                if pilot_path:
                    pilot_caption = build_caption(kho, date_iso, pilot_summary,
                                                  pilot_label=f" (PILOT HTP & SCV)")
                    results.append(("image", kho, date_iso, pilot_path, pilot_caption))

    if not results:
        print("\n  ❌ Nothing generated!")
        sys.exit(1)

    if args.dry_run:
        print(f"\n  [DRY RUN] {len(results)} report(s) generated.")
        for typ, kho, d, path, cap in results:
            print(f"  [{typ}] {kho} {d}")
            print(f"  Caption:\n{cap}\n")
        return

    # Deploy HTML
    if any(t == "html" for t, *_ in results):
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
