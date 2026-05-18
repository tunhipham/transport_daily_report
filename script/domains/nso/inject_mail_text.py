# -*- coding: utf-8 -*-
"""
inject_mail_text.py — Parse NSO mail from raw text (no browser needed)
=====================================================================
Full pipeline: parse mail → merge master → generate calendar PNG →
deploy dashboard → send Telegram (photo + text) → generate Excel

Usage:
    python script/domains/nso/inject_mail_text.py --file path/to/mail.txt [--send]
"""
import os, sys, json, re, subprocess, calendar
from datetime import datetime, date, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "script"))

OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "state", "nso")


# ══════════════════════════════════════════════════════
#  PARSE MAIL TEXT
# ══════════════════════════════════════════════════════

def parse_mail_text(text):
    """Parse NSO stores from raw mail text."""
    lines = text.split('\n')
    fixed = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('/') and fixed:
            fixed[-1] = fixed[-1].rstrip() + stripped
        else:
            fixed.append(line)
    text = '\n'.join(fixed)
    text = re.sub(r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})', r'\1/\2/\3', text)

    stores = []
    entry_pattern = re.compile(r'(\d{1,3})\.\s+(.+?)(?=\n)')
    date_pattern = re.compile(r'Ngày khai trương:\s*([\d/]+)')

    # Allow leading whitespace before store number (e.g. ' 196. ...')
    entries = re.split(r'\n\s*(?=\d{1,3}\.\s)', text)
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        header_match = entry_pattern.match(entry)
        if not header_match:
            continue
        stt = header_match.group(1)
        name_mail = header_match.group(2).strip()
        name_mail = re.sub(r'https?://\S+', '', name_mail).strip()
        name_mail = name_mail.rstrip(' -')
        name_mail = re.sub(r'\s*-\s*dời.*$', '', name_mail, flags=re.IGNORECASE).strip()
        name_mail = re.sub(r'\s*-\s*[Mm]ới bổ sung\s*$', '', name_mail).strip()
        # Also strip standalone 'Mới bổ sung' without dash
        name_mail = re.sub(r'\s*[Mm]ới bổ sung\s*$', '', name_mail).strip()

        date_match = date_pattern.search(entry)
        if not date_match:
            continue
        raw_date = date_match.group(1)
        opening_date = re.sub(r'\s+', '', raw_date)

        stores.append({
            "stt": int(stt),
            "name_mail": name_mail,
            "opening_date": opening_date,
        })

    stores.sort(key=lambda s: s["stt"])
    return stores


# ══════════════════════════════════════════════════════
#  CALENDAR IMAGE GENERATION (self-contained, no browser)
# ══════════════════════════════════════════════════════

def _parse_store_date(store):
    """Parse opening_date string to date object."""
    od = store.get("opening_date", "")
    try:
        parts = od.split("/")
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        return None


def _get_store_status(store, today):
    """Get status: 'opening' (D→D+3), 'upcoming', 'reschedule', or None (past D+3)."""
    d = _parse_store_date(store)
    if not d:
        return None
    if d <= today <= d + timedelta(days=3):
        return "opening"
    if d > today:
        if store.get("original_date") and store["original_date"] != store["opening_date"]:
            return "reschedule"
        return "upcoming"
    return None  # past D+3


def _store_label(store):
    """Short label for calendar cell."""
    code = store.get("code") or "None"
    name = store.get("name_full") or store.get("name_mail") or "?"
    # Truncate long names
    if len(name) > 28:
        name = name[:26] + "…"
    return f"{code} · {name}"


def build_calendar_html(stores, target_month=None, target_year=None):
    """Build a self-contained HTML calendar with store events for rendering to PNG."""
    today = date.today()
    year = target_year or today.year
    month = target_month or today.month

    month_names = ['', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
                   'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12']
    day_headers = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'CN']

    # Build events map: date → [(label, status)]
    events = {}
    for store in stores:
        d = _parse_store_date(store)
        if not d:
            continue
        status = _get_store_status(store, today)
        if not status:
            continue
        if d.year == year and d.month == month:
            if d not in events:
                events[d] = []
            events[d].append((_store_label(store), status))

    # Calendar grid
    cal = calendar.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdayscalendar(year, month)

    # Status colors
    colors = {
        "opening": ("rgba(245,158,11,.18)", "#f59e0b"),
        "upcoming": ("rgba(16,185,129,.18)", "#10b981"),
        "reschedule": ("rgba(168,85,247,.18)", "#a855f7"),
    }

    # Build cells
    cells_html = ""
    for week in weeks:
        for i, day in enumerate(week):
            if day == 0:
                cells_html += '<div class="cell empty"></div>'
                continue

            d = date(year, month, day)
            is_today = d == today
            is_sun = i == 6
            today_cls = " today" if is_today else ""

            day_events = events.get(d, [])
            ev_html = ""
            for label, status in day_events:
                bg, fg = colors.get(status, ("rgba(100,100,100,.2)", "#999"))
                ev_html += f'<div class="ev" style="background:{bg};color:{fg}">{label}</div>'

            day_cls = " sun" if is_sun else ""
            cells_html += f'''<div class="cell{today_cls}">
                <div class="day{day_cls}">{day}</div>{ev_html}</div>'''

    # Legend
    legend_html = '''
    <div class="legend">
        <span class="leg-item"><span class="leg-dot" style="background:#f59e0b"></span>Đang Khai Trương</span>
        <span class="leg-item"><span class="leg-dot" style="background:#10b981"></span>Sắp Khai Trương</span>
        <span class="leg-item"><span class="leg-dot" style="background:#a855f7"></span>Dời Khai Trương</span>
    </div>'''

    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0a0e1a;
    color: #f1f5f9;
    display: inline-block;
    padding: 24px;
}}
.title {{
    text-align: center;
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 10px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.subtitle {{
    text-align: center;
    color: #64748b;
    font-size: 12px;
    margin-bottom: 12px;
}}
.legend {{
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-bottom: 16px;
}}
.leg-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #94a3b8;
    font-weight: 500;
}}
.leg-dot {{
    width: 10px;
    height: 10px;
    border-radius: 3px;
}}
.month {{
    text-align: center;
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 14px;
    color: #f1f5f9;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 2px;
    width: 980px;
}}
.hd {{
    background: rgba(99,102,241,.15);
    color: #818cf8;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 4px;
    text-align: center;
    border-radius: 6px;
}}
.hd.sun {{ color: #ef4444; }}
.cell {{
    min-height: 88px;
    background: rgba(30,41,59,.4);
    border-radius: 6px;
    padding: 4px 5px;
    position: relative;
}}
.cell.empty {{ background: transparent; min-height: 40px; }}
.cell.today {{ border: 2px solid #6366f1; }}
.day {{
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 3px;
}}
.day.sun {{ color: #ef4444; }}
.ev {{
    font-size: 10px;
    line-height: 1.3;
    padding: 2px 5px;
    border-radius: 4px;
    margin-bottom: 2px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
</style></head><body>
<div class="title">🏪 NSO Calendar</div>
<div class="subtitle">Lịch Khai Trương — Cập nhật {today.strftime("%d/%m/%Y")}</div>
{legend_html}
<div class="month">{month_names[month]} / {year}</div>
<div class="grid">
{"".join(f'<div class="hd{" sun" if i==6 else ""}">{d}</div>' for i, d in enumerate(day_headers))}
{cells_html}
</div>
</body></html>'''
    return html


def render_calendar_png(stores):
    """Build calendar HTML and render to PNG using Playwright."""
    from playwright.sync_api import sync_playwright

    today = date.today()
    html = build_calendar_html(stores, today.month, today.year)

    # Save temp HTML
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    html_path = os.path.join(OUTPUT_DIR, "_cal_temp.html")
    png_path = os.path.join(OUTPUT_DIR, "nso_calendar.png")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1100, "height": 800},
            device_scale_factor=2,
        )
        page = context.new_page()
        page.goto(f"file:///{html_path.replace(os.sep, '/')}")
        page.wait_for_load_state("networkidle")

        body = page.query_selector("body")
        box = body.bounding_box()
        page.screenshot(
            path=png_path,
            clip={"x": 0, "y": 0, "width": box["width"], "height": box["height"]},
        )
        browser.close()

    # Cleanup temp
    try:
        os.remove(html_path)
    except OSError:
        pass

    print(f"  ✅ Calendar PNG: {png_path}")
    return png_path


# ══════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════

def _load_telegram_config():
    """Load NSO Telegram config."""
    cfg_path = os.path.join(REPO_ROOT, "config", "telegram.json")
    with open(cfg_path, "r") as f:
        cfg = json.load(f)
    nso_cfg = cfg.get("nso", {})
    bot_token = nso_cfg.get("bot_token")
    chat_ids = nso_cfg.get("chat_ids", [])
    if not chat_ids:
        chat_id = nso_cfg.get("chat_id")
        if chat_id:
            chat_ids = [chat_id]
    return bot_token, chat_ids


def get_week_stores(stores_master, weeks_offset=0):
    """Get stores opening in a specific week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=weeks_offset)
    sunday = monday + timedelta(days=6)
    result = []
    for store in stores_master:
        d = _parse_store_date(store)
        if d and monday <= d <= sunday:
            result.append(store)
    result.sort(key=lambda s: s["opening_date"])
    return result, monday, sunday


def build_telegram_summary(stores_master):
    """Build Telegram message with this week + next week openings."""
    lines = []
    today = date.today()
    lines.append(f"🏪 CẬP NHẬT NSO — {today.strftime('%d/%m/%Y')}")
    lines.append("")

    for offset, label in [(0, "📌 TUẦN NÀY"), (1, "📅 TUẦN SAU")]:
        week_stores, mon, sun = get_week_stores(stores_master, offset)
        lines.append(f"{label} ({mon.strftime('%d/%m')} – {sun.strftime('%d/%m')}):")
        if week_stores:
            for s in week_stores:
                code = s.get("code") or "—"
                name = s.get("name_full") or s.get("name_mail") or "?"
                ver = s.get("version")
                ver_str = f" · v{ver}" if ver else ""
                od = s.get("opening_date", "?")
                try:
                    d = _parse_store_date(s)
                    dow = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][d.weekday()]
                except Exception:
                    dow = ""
                lines.append(f"  🔹 {name}")
                lines.append(f"     📅 {od} ({dow}) · {code}{ver_str}")
        else:
            lines.append("  (Không có)")
        lines.append("")

    lines.append(f"📊 Tổng master: {len(stores_master)} stores")
    lines.append(f"🔗 https://tunhipham.github.io/transport_daily_report/")
    return "\n".join(lines)


def send_telegram_photo(photo_path, caption, bot_token, chat_ids):
    """Send photo to all NSO Telegram groups."""
    import urllib.request
    for chat_id in chat_ids:
        # Use multipart form data for photo upload
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        with open(photo_path, "rb") as f:
            photo_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="photo"; filename="nso_calendar.png"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + photo_data + f"\r\n--{boundary}--\r\n".encode()

        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"  ✅ Telegram photo sent to {chat_id}")
            else:
                print(f"  ❌ Telegram photo error: {result}")
        except Exception as e:
            print(f"  ❌ Telegram photo failed ({chat_id}): {e}")


def send_telegram_text(text, bot_token, chat_ids):
    """Send text to all NSO Telegram groups."""
    import urllib.request
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"  ✅ Telegram text sent to {chat_id}")
            else:
                print(f"  ❌ Telegram error: {result}")
        except Exception as e:
            print(f"  ❌ Telegram failed ({chat_id}): {e}")


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NSO Mail Inject (Text)")
    parser.add_argument("--file", required=False, help="Path to mail text file")
    parser.add_argument("--send", action="store_true", help="Send to Telegram after full pipeline")
    parser.add_argument("--send-only", action="store_true", dest="send_only",
                        help="Send existing results to Telegram (no parse/merge)")
    args = parser.parse_args()

    # ── Send-only mode: just send Telegram from existing data ──
    if args.send_only:
        print(f"\n{'='*55}")
        print(f"  🏪 NSO SEND-ONLY — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(f"{'='*55}")

        from domains.nso.nso_master import NsoMaster
        master = NsoMaster()
        master.load()
        print(f"  📊 Master: {len(master.stores)} stores")

        # Find existing calendar PNG
        cal_png = os.path.join(OUTPUT_DIR, "nso_calendar.png")
        if not os.path.exists(cal_png):
            print(f"  ⚠ Calendar PNG not found, regenerating...")
            cal_png = render_calendar_png(master.stores)

        bot_token, chat_ids = _load_telegram_config()
        if not bot_token or not chat_ids:
            print("  ❌ NSO Telegram chưa cấu hình!")
            sys.exit(1)

        print(f"\n  📤 Sending to Telegram...")
        if cal_png and os.path.exists(cal_png):
            send_telegram_photo(cal_png,
                f"🏪 NSO Calendar — {date.today().strftime('%d/%m/%Y')}",
                bot_token, chat_ids)
        msg = build_telegram_summary(master.stores)
        print(f"\n{msg}\n")
        send_telegram_text(msg, bot_token, chat_ids)

        print(f"\n{'='*55}")
        print(f"  DONE (send-only)")
        print(f"{'='*55}")
        return

    # ── Full pipeline requires --file ──
    if not args.file:
        parser.error("--file is required (unless using --send-only)")


    print(f"\n{'='*55}")
    print(f"  🏪 NSO Mail Inject (Text) — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}")

    # ── Step 1: Parse mail ──
    with open(args.file, "r", encoding="utf-8") as f:
        mail_text = f.read()
    print(f"\n  📄 Mail text: {len(mail_text)} chars")

    mail_stores = parse_mail_text(mail_text)
    print(f"  ✅ Parsed {len(mail_stores)} stores")
    for s in mail_stores[:5]:
        print(f"     #{s['stt']} | {s['name_mail'][:50]} | {s['opening_date']}")
    if len(mail_stores) > 5:
        print(f"     ... +{len(mail_stores) - 5} more")

    if not mail_stores:
        print("  ❌ No stores parsed!")
        return

    # ── Step 2: Read DSST + Load master ──
    from domains.nso.fetch_nso_mail import read_dsst
    dsst_lookup = read_dsst()

    from domains.nso.nso_master import NsoMaster
    master = NsoMaster()
    master.load()
    print(f"  📊 Master before: {len(master.stores)} stores")

    # ── Step 3: Merge ──
    summary, added, updated = master.merge_mail(mail_stores, dsst_lookup)
    print(f"\n  {'─'*40}")
    print(f"  📊 Merge result:")
    print(f"     Total: {len(master.stores)}")
    print(f"     New:   {len(added)} {added[:5] if added else ''}")
    print(f"     Updated: {len(updated)} {updated[:5] if updated else ''}")

    # ── Step 4: Save master ──
    master.save()
    master.save_output(scan_summary=summary)

    # ── Step 5: Generate calendar PNG ──
    print(f"\n  🖼️  Rendering calendar image...")
    cal_png = render_calendar_png(master.stores)

    # ── Step 6: Export + Deploy dashboard ──
    print(f"\n  📦 Re-exporting NSO data...")
    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "script", "dashboard", "export_data.py"),
         "--domain", "nso"],
        cwd=REPO_ROOT, timeout=60
    )
    print(f"  🚀 Deploying...")
    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "script", "dashboard", "deploy.py"),
         "--domain", "nso"],
        cwd=REPO_ROOT, timeout=120
    )

    # ── Step 7: Send Telegram (photo + text) ──
    if args.send:
        bot_token, chat_ids = _load_telegram_config()
        if not bot_token or not chat_ids:
            print("  ❌ NSO Telegram chưa cấu hình!")
        else:
            print(f"\n  📤 Sending to Telegram...")
            # Send calendar photo first
            if cal_png:
                send_telegram_photo(cal_png,
                    f"🏪 NSO Calendar — {date.today().strftime('%d/%m/%Y')}",
                    bot_token, chat_ids)
            # Then send text summary
            msg = build_telegram_summary(master.stores)
            print(f"\n{msg}\n")
            send_telegram_text(msg, bot_token, chat_ids)

    # ── Step 8: Generate châm hàng Excel ──
    print(f"\n  📋 Generating châm hàng Excel...")
    excel_script = os.path.join(REPO_ROOT, "script", "domains", "weekly_plan", "generate_excel.py")
    if os.path.exists(excel_script):
        subprocess.run(
            [sys.executable, excel_script],
            cwd=REPO_ROOT, timeout=60
        )
    else:
        print(f"  ⚠ generate_excel.py not found")

    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
