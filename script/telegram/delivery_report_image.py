# -*- coding: utf-8 -*-
"""
delivery_report_image.py — Generate delivery report images & send via Telegram
===============================================================================
Generates a styled table image for each kho showing:
  Trip | Siêu Thị | Giao | Nhận | Thiếu/Đủ

Schedules:
  - KRC (day D) + KSL-Tối (day D-1): 09:00
  - ĐÔNG (day D): 16:30
  - MÁT (day D): 16:30
  - KSL-Sáng (day D): 15:00

Usage:
  python script/telegram/delivery_report_image.py --kho KRC --date 2026-05-28
  python script/telegram/delivery_report_image.py --kho KSL-Tối --date 2026-05-27
  python script/telegram/delivery_report_image.py --kho KRC --kho KSL-Tối --dry-run
  python script/telegram/delivery_report_image.py --kho ĐÔNG --kho MÁT  # generate both
"""
import os, sys, json, argparse
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE, "output", "delivery_images")
PERF_JSON = os.path.join(BASE, "docs", "data", "performance.json")
TG_CONFIG = os.path.join(BASE, "config", "telegram.json")

# ── Color Palette (Dark theme matching dashboard) ──
BG_COLOR = (30, 30, 46)         # #1E1E2E
HEADER_BG = (42, 42, 60)       # #2A2A3C
ROW_EVEN = (35, 35, 50)        # slightly lighter
ROW_ODD = (30, 30, 46)         # base
TITLE_BG = (20, 20, 35)        # darker for title bar
BORDER_COLOR = (58, 58, 76)    # #3A3A4C
TEXT_COLOR = (224, 224, 224)    # #E0E0E0
HEADER_TEXT = (240, 192, 96)   # #F0C060 golden
GREEN = (16, 185, 129)         # #10B981
RED = (239, 68, 68)            # #EF4444
ORANGE = (249, 115, 22)        # #F97316
CYAN = (34, 211, 238)          # #22D3EE
WHITE = (255, 255, 255)
DIM_TEXT = (160, 160, 180)     # for secondary info
TRIP_BG = (25, 25, 40)         # trip separator row

# KHO accent colors
KHO_ACCENTS = {
    "KRC": (108, 166, 255),        # blue
    "ĐÔNG": (76, 175, 80),         # green
    "MÁT": (129, 212, 250),        # light blue
    "KSL-Sáng": (255, 217, 102),   # yellow
    "KSL-Tối": (196, 155, 255),    # purple
    "THỊT CÁ": (255, 159, 90),    # orange
}

# ── Fonts ──
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
    """Load tracking data from performance.json."""
    with open(PERF_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tracking", {})


def get_kho_rows(tracking, kho, date_iso):
    """Get rows for a specific kho on a specific date."""
    dates_data = tracking.get("dates", {})
    day_data = dates_data.get(date_iso, {})
    return day_data.get(kho, [])


# ── Image Generation ──
def generate_report_image(kho, date_iso, rows, pilot_stores=None):
    """
    Generate a delivery report image for a kho.
    
    Args:
        kho: warehouse name
        date_iso: date in YYYY-MM-DD format
        rows: list of tracking row dicts
        pilot_stores: if set, only include these stores (for HTP/SCV pilot)
    
    Returns:
        path to saved image file
    """
    fonts = get_fonts()
    
    # Filter pilot stores if specified
    if pilot_stores:
        rows = [r for r in rows if r.get("dest", "") in pilot_stores]
    
    # Sort by trip, then plan_time
    rows.sort(key=lambda r: (
        r.get("trip", ""),
        r.get("plan_time", "") or "23:59"
    ))
    
    # Group by trip
    trips = {}
    trip_order = []
    for r in rows:
        tid = r.get("trip", "—")
        if tid not in trips:
            trips[tid] = {
                "plate": r.get("plate", ""),
                "driver": r.get("driver", ""),
                "rows": [],
            }
            trip_order.append(tid)
        trips[tid]["rows"].append(r)
    
    # Date formatting
    parts = date_iso.split("-")
    date_vn = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else date_iso
    weekdays = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    day_name = weekdays[dt.weekday()]
    
    # Column definitions
    is_thitca = kho == "THỊT CÁ"
    if is_thitca:
        cols = [
            ("STT", 50),
            ("Siêu Thị", 120),
            ("Dự Kiến", 80),
            ("Đến ST", 80),
        ]
    else:
        cols = [
            ("STT", 50),
            ("Siêu Thị", 100),
            ("Dự Kiến", 80),
            ("Đến ST", 80),
            ("Giao", 65),
            ("Nhận", 65),
            ("Thiếu/Đủ", 90),
        ]
    
    # Layout constants
    PADDING_X = 20
    ROW_HEIGHT = 32
    HEADER_HEIGHT = 36
    TITLE_HEIGHT = 70
    TRIP_ROW_HEIGHT = 30
    SUMMARY_HEIGHT = 50
    FOOTER_HEIGHT = 35
    
    total_width = sum(c[1] for c in cols) + PADDING_X * 2
    
    # Calculate total height
    num_data_rows = sum(len(t["rows"]) for t in trips.values())
    num_trip_headers = len(trips)
    content_height = (
        TITLE_HEIGHT +
        SUMMARY_HEIGHT +
        HEADER_HEIGHT +
        num_trip_headers * TRIP_ROW_HEIGHT +
        num_data_rows * ROW_HEIGHT +
        FOOTER_HEIGHT +
        20  # padding
    )
    
    # Create image
    img = Image.new("RGB", (total_width, content_height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    accent = KHO_ACCENTS.get(kho, CYAN)
    
    # ── Title Bar ──
    draw.rectangle([(0, 0), (total_width, TITLE_HEIGHT)], fill=TITLE_BG)
    # Accent line at top
    draw.rectangle([(0, 0), (total_width, 4)], fill=accent)
    
    pilot_label = ""
    if pilot_stores:
        pilot_label = f" — PILOT ({', '.join(pilot_stores)})"
    
    title = f"📦 Báo Cáo Giao Hàng — {kho}{pilot_label}"
    draw.text((PADDING_X, 14), title, fill=accent, font=fonts["title"])
    
    subtitle = f"{day_name}, {date_vn}"
    draw.text((PADDING_X, 42), subtitle, fill=DIM_TEXT, font=fonts["subtitle"])
    
    # Timestamp on right
    now_str = f"Cập nhật: {datetime.now().strftime('%H:%M %d/%m')}"
    ts_bbox = draw.textbbox((0, 0), now_str, font=fonts["small"])
    ts_w = ts_bbox[2] - ts_bbox[0]
    draw.text((total_width - PADDING_X - ts_w, 46), now_str, fill=DIM_TEXT, font=fonts["small"])
    
    y = TITLE_HEIGHT
    
    # ── Summary Bar ──
    done = sum(1 for r in rows if r.get("arrival"))
    pending = len(rows) - done
    total_giao = sum((r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0) for r in rows)
    total_nhan = sum((r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0) for r in rows)
    
    draw.rectangle([(0, y), (total_width, y + SUMMARY_HEIGHT)], fill=HEADER_BG)
    
    summary_parts = [
        (f"🚛 {len(trips)} trip", WHITE),
        (f"  •  ", DIM_TEXT),
        (f"✅ {done}", GREEN),
        (f" / ", DIM_TEXT),
        (f"❌ {pending}", RED if pending else DIM_TEXT),
        (f"  •  ", DIM_TEXT),
        (f"📤 {total_giao:,}", WHITE),
        (f" → ", DIM_TEXT),
        (f"📥 {total_nhan:,}", WHITE),
    ]
    
    sx = PADDING_X
    for text, color in summary_parts:
        draw.text((sx, y + 16), text, fill=color, font=fonts["summary"])
        bbox = draw.textbbox((0, 0), text, font=fonts["summary"])
        sx += bbox[2] - bbox[0]
    
    y += SUMMARY_HEIGHT
    
    # ── Table Header ──
    draw.rectangle([(0, y), (total_width, y + HEADER_HEIGHT)], fill=HEADER_BG)
    draw.line([(0, y + HEADER_HEIGHT - 1), (total_width, y + HEADER_HEIGHT - 1)], fill=accent, width=2)
    
    x = PADDING_X
    for col_name, col_w in cols:
        # Center text in column
        bbox = draw.textbbox((0, 0), col_name, font=fonts["header"])
        tw = bbox[2] - bbox[0]
        cx = x + (col_w - tw) // 2
        draw.text((cx, y + 10), col_name, fill=HEADER_TEXT, font=fonts["header"])
        x += col_w
    
    y += HEADER_HEIGHT
    
    # ── Data Rows ──
    stt = 0
    for trip_id in trip_order:
        trip_data = trips[trip_id]
        trip_rows = trip_data["rows"]
        
        # Trip separator row
        draw.rectangle([(0, y), (total_width, y + TRIP_ROW_HEIGHT)], fill=TRIP_BG)
        draw.line([(0, y), (total_width, y)], fill=BORDER_COLOR)
        
        trip_label = f"🚚 {trip_id}  |  {trip_data['plate']}  |  {trip_data['driver']}"
        draw.text((PADDING_X + 5, y + 8), trip_label, fill=accent, font=fonts["trip_label"])
        
        # Trip subtotal on right
        trip_giao = sum((r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0) for r in trip_rows)
        trip_nhan = sum((r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0) for r in trip_rows)
        trip_summary = f"G:{trip_giao} | N:{trip_nhan}"
        ts_bbox = draw.textbbox((0, 0), trip_summary, font=fonts["trip_label"])
        ts_w = ts_bbox[2] - ts_bbox[0]
        draw.text((total_width - PADDING_X - ts_w - 5, y + 8), trip_summary, fill=DIM_TEXT, font=fonts["trip_label"])
        
        y += TRIP_ROW_HEIGHT
        
        for ri, r in enumerate(trip_rows):
            stt += 1
            row_bg = ROW_EVEN if stt % 2 == 0 else ROW_ODD
            draw.rectangle([(0, y), (total_width, y + ROW_HEIGHT)], fill=row_bg)
            draw.line([(0, y + ROW_HEIGHT - 1), (total_width, y + ROW_HEIGHT - 1)], fill=BORDER_COLOR)
            
            giao = (r.get("tote_t", 0) or 0) + (r.get("carton_t", 0) or 0)
            nhan = (r.get("tote_r", 0) or 0) + (r.get("carton_r", 0) or 0)
            diff = nhan - giao
            
            if diff == 0 and giao > 0:
                status_text = "Đủ"
                status_color = GREEN
            elif diff < 0:
                status_text = f"Thiếu {abs(diff)}"
                status_color = RED
            elif diff > 0:
                status_text = f"Dư {diff}"
                status_color = ORANGE
            else:
                status_text = "—"
                status_color = DIM_TEXT
            
            # Arrival styling
            arrival = r.get("arrival", "")
            arr_color = GREEN if arrival else RED
            arr_text = arrival if arrival else "—"
            
            # Plan time
            plan_text = r.get("plan_time", "") or "—"
            
            if is_thitca:
                cell_values = [
                    (str(stt), TEXT_COLOR),
                    (r.get("dest", "—"), WHITE),
                    (plan_text, DIM_TEXT),
                    (arr_text, arr_color),
                ]
            else:
                cell_values = [
                    (str(stt), TEXT_COLOR),
                    (r.get("dest", "—"), WHITE),
                    (plan_text, DIM_TEXT),
                    (arr_text, arr_color),
                    (str(giao) if giao else "—", TEXT_COLOR),
                    (str(nhan) if nhan else "—", TEXT_COLOR),
                    (status_text, status_color),
                ]
            
            x = PADDING_X
            for ci, ((_, col_w), (val, color)) in enumerate(zip(cols, cell_values)):
                font = fonts["cell_bold"] if ci == 1 else fonts["cell"]
                bbox = draw.textbbox((0, 0), val, font=font)
                tw = bbox[2] - bbox[0]
                cx = x + (col_w - tw) // 2
                draw.text((cx, y + 9), val, fill=color, font=font)
                x += col_w
            
            y += ROW_HEIGHT
    
    # ── Footer ──
    draw.rectangle([(0, y), (total_width, y + FOOTER_HEIGHT)], fill=TITLE_BG)
    draw.rectangle([(0, content_height - 3), (total_width, content_height)], fill=accent)
    
    footer_text = f"KFM Command Center  •  {len(rows)} điểm giao  •  {len(trips)} chuyến"
    bbox = draw.textbbox((0, 0), footer_text, font=fonts["small"])
    tw = bbox[2] - bbox[0]
    draw.text(((total_width - tw) // 2, y + 10), footer_text, fill=DIM_TEXT, font=fonts["small"])
    
    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    pilot_suffix = "_pilot" if pilot_stores else ""
    kho_safe = kho.replace("-", "").replace(" ", "_")
    fname = f"delivery_{kho_safe}_{date_iso}{pilot_suffix}.png"
    fpath = os.path.join(OUTPUT_DIR, fname)
    img.save(fpath, "PNG", quality=95)
    
    print(f"  📸 Image saved: {fpath} ({img.width}x{img.height})")
    return fpath


# ── Telegram ──
def send_telegram_image(bot_token, chat_id, image_path, caption=""):
    """Send image via Telegram Bot API."""
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(image_path, "rb") as f:
        payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        files = {"photo": f}
        r = requests.post(url, data=payload, files=files, timeout=30)
        r.raise_for_status()
    return r.json()


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Generate delivery report image & send Telegram")
    parser.add_argument("--kho", action="append", required=True,
                        help="Kho to generate (can repeat): KRC, ĐÔNG, MÁT, KSL-Sáng, KSL-Tối, THỊT CÁ")
    parser.add_argument("--date", default=None,
                        help="Date (YYYY-MM-DD). Default: today for most khos, yesterday for KSL-Tối")
    parser.add_argument("--dry-run", action="store_true", help="Generate image only, don't send")
    parser.add_argument("--chat-id", default=None, help="Override Telegram chat_id (for testing)")
    parser.add_argument("--pilot", action="store_true",
                        help="Also generate separate pilot image for HTP/SCV")
    args = parser.parse_args()
    
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"\n{'═'*60}")
    print(f"  📸 Delivery Report Image Generator")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'═'*60}\n")
    
    # Load data
    print("📂 Loading tracking data...")
    tracking = load_tracking()
    if not tracking or not tracking.get("dates"):
        print("  ❌ No tracking data found! Run run-realtime-performance.bat first.")
        sys.exit(1)
    
    print(f"  ✅ Latest date: {tracking.get('latest_date', '?')}")
    
    # Load telegram config
    with open(TG_CONFIG, "r", encoding="utf-8") as f:
        tg_cfg = json.load(f)
    
    bot_token = tg_cfg.get("delivery_report", tg_cfg.get("performance", {})).get("bot_token", "")
    chat_id = args.chat_id or tg_cfg.get("delivery_report", tg_cfg.get("trip_reminder", {})).get("chat_id", "")
    
    if not bot_token:
        # Fallback: use any available bot token
        for key in tg_cfg:
            if isinstance(tg_cfg[key], dict) and "bot_token" in tg_cfg[key]:
                bot_token = tg_cfg[key]["bot_token"]
                break
    
    images_generated = []
    
    for kho in args.kho:
        # Determine date
        if args.date:
            date_iso = args.date
        elif kho == "KSL-Tối":
            date_iso = yesterday
        else:
            date_iso = today
        
        print(f"\n{'─'*50}")
        print(f"  🏭 {kho} — {date_iso}")
        print(f"{'─'*50}")
        
        rows = get_kho_rows(tracking, kho, date_iso)
        if not rows:
            print(f"  ⚠ No data for {kho} on {date_iso}")
            continue
        
        print(f"  📊 {len(rows)} rows found")
        
        # Main report
        img_path = generate_report_image(kho, date_iso, rows)
        images_generated.append((kho, date_iso, img_path, None))
        
        # Pilot stores report (HTP, SCV)
        if args.pilot:
            pilot_stores = {"HTP", "SCV"}
            pilot_rows = [r for r in rows if r.get("dest", "") in pilot_stores]
            if pilot_rows:
                print(f"\n  🧪 Pilot report ({len(pilot_rows)} stores)...")
                pilot_path = generate_report_image(kho, date_iso, rows, pilot_stores=pilot_stores)
                images_generated.append((kho, date_iso, pilot_path, "pilot"))
    
    if not images_generated:
        print("\n  ❌ No images generated!")
        sys.exit(1)
    
    # Send to Telegram
    if args.dry_run:
        print(f"\n  [DRY RUN] {len(images_generated)} image(s) generated, not sending.")
    else:
        print(f"\n📤 Sending {len(images_generated)} image(s) to Telegram...")
        for kho, date_iso, img_path, tag in images_generated:
            parts = date_iso.split("-")
            date_vn = f"{parts[2]}/{parts[1]}/{parts[0]}"
            pilot_tag = " (PILOT)" if tag == "pilot" else ""
            caption = f"📦 <b>Báo Cáo Giao Hàng — {kho}{pilot_tag}</b>\n📅 {date_vn}"
            
            try:
                send_telegram_image(bot_token, chat_id, img_path, caption)
                print(f"  ✅ Sent: {kho} {date_iso}{pilot_tag}")
            except Exception as e:
                print(f"  ❌ Failed: {kho} — {e}")
    
    print(f"\n{'═'*60}")
    print(f"  ✅ Done! {len(images_generated)} image(s)")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
