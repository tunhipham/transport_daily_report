"""
Generate 2 capacity forecast PNG images and send full report to personal Telegram.
"""
import os, sys, json, requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DATA = os.path.join(BASE, "docs", "data")
OUTPUT_DIR = os.path.join(BASE, "output", "artifacts", "daily")
DATE_TAG = datetime.now().strftime("%d%m%Y")
BOT_TOKEN = "8786933573:AAHAus-L2ReuRM9q_Zr2IC122B62uNftisc"
CHAT_ID = "5782090339"  # Personal

# ── Load capacity forecast data ──
cap_path = os.path.join(DOCS_DATA, "capacity_forecast.json")
with open(cap_path, "r", encoding="utf-8") as f:
    cap = json.load(f)


def build_cap_html(key, data_list, benchmark, threshold, title, unit, color, bar_color_ok, bar_color_alert):
    """Build a self-contained HTML for a capacity chart using SVG bars."""
    alert_limit = benchmark * (1 + threshold / 100)
    if not data_list:
        return "<html><body><p>No data</p></body></html>"
    
    values = [d.get('tons', d.get('items', 0)) for d in data_list]
    max_val = max(values) * 1.15 if values else 1
    # Ensure max_val at least covers alert line
    max_val = max(max_val, alert_limit * 1.15)
    avg_val = sum(values) / len(values) if values else 0
    peak_val = max(values) if values else 0
    alert_days = sum(1 for v in values if v > alert_limit)
    
    chart_w = 1600
    chart_h = 500
    pad_l = 90
    pad_r = 40
    pad_t = 40
    pad_b = 80
    plot_w = chart_w - pad_l - pad_r
    plot_h = chart_h - pad_t - pad_b
    n = len(values)
    bar_w = max(8, min(50, (plot_w / n) * 0.7)) if n > 0 else 30
    gap = (plot_w - bar_w * n) / max(n - 1, 1) if n > 1 else 0
    
    def xpos(i):
        return pad_l + i * (bar_w + gap) + bar_w / 2
    
    def ypos(v):
        return pad_t + plot_h * (1 - v / max_val) if max_val > 0 else pad_t + plot_h

    fmt_val = lambda v: f"{v:.1f} Tấn" if key == 'krc' else f"{v/1000:.0f}K"
    
    svg_parts = []
    svg_parts.append(f'<svg viewBox="0 0 {chart_w} {chart_h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto">')
    
    # Grid lines
    for i in range(6):
        y = pad_t + plot_h * i / 5
        v = max_val * (5 - i) / 5
        svg_parts.append(f'<line x1="{pad_l}" y1="{y:.0f}" x2="{chart_w-pad_r}" y2="{y:.0f}" stroke="#3a3f4a" stroke-width="0.5"/>')
        svg_parts.append(f'<text x="{pad_l-8}" y="{y+5:.0f}" text-anchor="end" font-size="14" font-weight="600" fill="#b0b5c0">{fmt_val(v)}</text>')
    
    # Benchmark line
    by = ypos(benchmark)
    svg_parts.append(f'<line x1="{pad_l}" y1="{by:.1f}" x2="{chart_w-pad_r}" y2="{by:.1f}" stroke="#6366f1" stroke-width="2.5" stroke-dasharray="10,5"/>')
    svg_parts.append(f'<rect x="{pad_l+5}" y="{by-28:.1f}" width="{len(f"Benchmark {fmt_val(benchmark)}")*9+16}" height="22" rx="4" fill="rgba(99,102,241,0.25)"/>')
    svg_parts.append(f'<text x="{pad_l+13}" y="{by-12:.1f}" font-size="13" font-weight="700" fill="#818cf8">Benchmark {fmt_val(benchmark)}</text>')
    
    # Alert line
    ay = ypos(alert_limit)
    svg_parts.append(f'<line x1="{pad_l}" y1="{ay:.1f}" x2="{chart_w-pad_r}" y2="{ay:.1f}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>')
    svg_parts.append(f'<text x="{chart_w-pad_r-5}" y="{ay+18:.1f}" text-anchor="end" font-size="11" font-weight="600" fill="#f87171">+{threshold}% Alert</text>')
    
    # Bars
    for i, (d, v) in enumerate(zip(data_list, values)):
        x = pad_l + i * (bar_w + gap)
        y = ypos(v)
        h = pad_t + plot_h - y
        is_alert = v > alert_limit
        fill = bar_color_alert if is_alert else bar_color_ok
        stroke = '#ef4444' if is_alert else color
        svg_parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        # Value label on top
        if n <= 30 or is_alert:
            label = f"{v:.1f}" if key == 'krc' else f"{v/1000:.0f}K"
            font_color = '#ef4444' if is_alert else '#ffffff'
            svg_parts.append(f'<text x="{xpos(i):.1f}" y="{y-6:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="{font_color}">{label}</text>')
    
    # X-axis labels
    step = max(1, n // 25)
    for i, d in enumerate(data_list):
        if i % step == 0 or i == n - 1:
            x = xpos(i)
            label = d['date'][:5]
            svg_parts.append(f'<text x="{x:.1f}" y="{pad_t+plot_h+22:.0f}" text-anchor="middle" font-size="12" font-weight="600" fill="#b0b5c0">{label}</text>')
    
    svg_parts.append('</svg>')
    svg_str = '\n'.join(svg_parts)
    
    # Alert badge
    if alert_days > 0:
        alert_html = f'<div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#f87171;padding:10px 18px;border-radius:10px;font-size:17px;font-weight:700;margin-bottom:14px">⚠️ {alert_days} ngày vượt {threshold}% capacity benchmark ({fmt_val(benchmark)})</div>'
    else:
        alert_html = f'<div style="background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.25);color:#10b981;padding:10px 18px;border-radius:10px;font-size:17px;font-weight:700;margin-bottom:14px">✅ Tất cả ngày trong ngưỡng capacity an toàn</div>'
    
    # Info cards
    info_html = f"""<div style="display:flex;gap:14px;margin-bottom:16px">
      <div style="flex:1;background:#1e2029;border:1px solid #3a3f4a;border-radius:10px;padding:14px;text-align:center">
      <div style="font-size:28px;font-weight:800;color:{color}">{fmt_val(avg_val)}</div>
        <div style="font-size:13px;color:#8a8f9a;font-weight:600;text-transform:uppercase;margin-top:4px">Trung bình/ngày</div>
      </div>
      <div style="flex:1;background:#1e2029;border:1px solid #3a3f4a;border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:28px;font-weight:800;color:#f87171">{fmt_val(peak_val)}</div>
        <div style="font-size:13px;color:#8a8f9a;font-weight:600;text-transform:uppercase;margin-top:4px">Cao nhất</div>
      </div>
      <div style="flex:1;background:#1e2029;border:1px solid #3a3f4a;border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:28px;font-weight:800;color:{'#f87171' if alert_days else '#10b981'}">{alert_days}/{len(values)}</div>
        <div style="font-size:13px;color:#8a8f9a;font-weight:600;text-transform:uppercase;margin-top:4px">Ngày vượt {threshold}%</div>
      </div>
    </div>"""
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  * {{ margin:0;padding:0;box-sizing:border-box }}
  body {{ background:#1e2029;color:#e8eaef;font-family:'Inter','Segoe UI',sans-serif;padding:24px }}
  .title {{ font-size:22px;font-weight:800;color:#f0c060;text-align:center;text-transform:uppercase;letter-spacing:1px;margin-bottom:18px }}
</style></head>
<body>
<div class="title">{title}</div>
{alert_html}
{info_html}
<div style="background:#252830;border:1px solid #3a3f4a;border-radius:12px;padding:16px">
{svg_str}
</div>
</body></html>"""


def render_html_to_png(html_content, output_path, width=1700):
    """Render HTML to PNG using Playwright."""
    from playwright.sync_api import sync_playwright
    
    temp_file = output_path + ".html"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": 1000}, device_scale_factor=3)
        page = ctx.new_page()
        page.goto(f"file:///{temp_file.replace(os.sep, '/')}")
        page.wait_for_load_state("networkidle")
        body = page.query_selector("body")
        box = body.bounding_box()
        page.screenshot(path=output_path, clip={"x": 0, "y": 0, "width": box["width"], "height": box["height"]})
        page.close()
        browser.close()
    
    try:
        os.remove(temp_file)
    except OSError:
        pass
    return output_path


def send_photo(path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(path, 'rb') as photo:
        r = requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': photo})
    print(f"  {'✅' if r.ok else '❌'} {os.path.basename(path)}: {r.status_code}")
    return r.ok


def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': False})
    print(f"  {'✅' if r.ok else '❌'} Text message: {r.status_code}")
    return r.ok


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
print("=" * 60)
print("  🏭 Capacity Forecast — Generate PNGs + Send Preview")
print("=" * 60)

# 1. Generate KRC chart PNG
print("\n📊 Generating KRC capacity chart...")
krc_html = build_cap_html(
    'krc', cap['krc']['data'], cap['krc']['benchmark_tons'], cap['krc']['alert_threshold_pct'],
    f"CAPACITY FORECAST — KRC (RAU CỦ) — {cap['_updated'][:10]}",
    'Tấn', '#10b981', 'rgba(16,185,129,0.7)', 'rgba(239,68,68,0.75)'
)
krc_png = os.path.join(OUTPUT_DIR, f"BAO_CAO_{DATE_TAG}_6_CAP_KRC.png")
render_html_to_png(krc_html, krc_png)
print(f"  ✅ {os.path.basename(krc_png)}")

# 2. Generate KSL chart PNG
print("\n📊 Generating KSL capacity chart...")
ksl_html = build_cap_html(
    'ksl', cap['ksl']['data'], cap['ksl']['benchmark_items'], cap['ksl']['alert_threshold_pct'],
    f"CAPACITY FORECAST — KSL DRY (SÁNG + TỐI) — {cap['_updated'][:10]}",
    'Items', '#f59e0b', 'rgba(245,158,11,0.7)', 'rgba(239,68,68,0.75)'
)
ksl_png = os.path.join(OUTPUT_DIR, f"BAO_CAO_{DATE_TAG}_7_CAP_KSL.png")
render_html_to_png(ksl_html, ksl_png)
print(f"  ✅ {os.path.basename(ksl_png)}")

# 3. Send all 7 images to personal Telegram
print(f"\n📤 Sending to personal Telegram ({CHAT_ID})...")
date_str = datetime.now().strftime("%d/%m/%Y")

# Existing 5 images
existing = [
    (f"BAO_CAO_{DATE_TAG}_1_BANG.png", "📋 Bảng KPI"),
    (f"BAO_CAO_{DATE_TAG}_2_DONGGOP.png", "🍩 % Đóng góp"),
    (f"BAO_CAO_{DATE_TAG}_3_SANLUONG.png", "📈 Trend Sản lượng"),
    (f"BAO_CAO_{DATE_TAG}_4_ITEMS.png", "📦 Trend Items"),
    (f"BAO_CAO_{DATE_TAG}_5_XE.png", "🚛 Trend Xe"),
]

caption_base = f"📊 Báo cáo xuất kho {date_str} — REVIEW"

for fname, label in existing:
    fpath = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(fpath):
        send_photo(fpath, f"{caption_base}\n{label}")
    else:
        print(f"  ⚠ Missing: {fname}")

# 2 new capacity images
send_photo(krc_png, f"{caption_base}\n🏭 Capacity Forecast — KRC (Rau Củ)\nBenchmark: 65 Tấn | Alert: >5%")
send_photo(ksl_png, f"{caption_base}\n🏭 Capacity Forecast — KSL Dry (Sáng+Tối)\nBenchmark: 270,000 items | Alert: >5%")

# Dashboard link
send_text(f"📊 Dashboard đã cập nhật: {date_str}\n🔗 https://tunhipham.github.io/transport_daily_report/\n⏱ Kéo xuống cuối tab Daily để xem Capacity Forecast\n\n<i>Preview gửi cá nhân — chưa gửi nhóm</i>")

print(f"\n{'='*60}")
print("  ✅ DONE — Check Telegram cá nhân!")
print(f"{'='*60}")
