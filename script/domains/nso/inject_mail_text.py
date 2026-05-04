# -*- coding: utf-8 -*-
"""
inject_mail_text.py — Parse NSO mail from raw text (no browser needed)
Usage:
    python script/domains/nso/inject_mail_text.py --file path/to/mail.txt [--send]
"""
import os, sys, json, re, subprocess
from datetime import datetime, date, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "script"))


def parse_mail_text(text):
    """Parse NSO stores from raw mail text. Same logic as fetch_nso_mail.parse_nso_table."""
    # Normalize broken dates
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

    entries = re.split(r'\n(?=\d{1,3}\.\s)', text)
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
        name_mail = re.sub(r'\s*-\s*mới bổ sung\s*$', '', name_mail, flags=re.IGNORECASE).strip()
        # Also remove trailing "- Mới bổ sung" (case variant)
        name_mail = re.sub(r'\s*-\s*Mới bổ sung\s*$', '', name_mail).strip()

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


def get_week_stores(stores_master, weeks_offset=0):
    """Get stores opening in a specific week (0=this week, 1=next week)."""
    today = date.today()
    # Monday of target week
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=weeks_offset)
    sunday = monday + timedelta(days=6)

    result = []
    for store in stores_master:
        od = store.get("opening_date")
        if not od:
            continue
        try:
            parts = od.split("/")
            d = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            continue
        if monday <= d <= sunday:
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
                # Day of week
                try:
                    parts = od.split("/")
                    d = date(int(parts[2]), int(parts[1]), int(parts[0]))
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


def send_telegram(text):
    """Send to NSO Telegram group."""
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

    if not bot_token or not chat_ids:
        print("  ❌ NSO Telegram chưa cấu hình!")
        return

    import urllib.request
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"  ✅ Telegram sent to {chat_id}")
            else:
                print(f"  ❌ Telegram error: {result}")
        except Exception as e:
            print(f"  ❌ Telegram failed ({chat_id}): {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to mail text file")
    parser.add_argument("--send", action="store_true", help="Send to Telegram")
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"  🏪 NSO Mail Inject (Text) — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}")

    # Read mail text
    with open(args.file, "r", encoding="utf-8") as f:
        mail_text = f.read()
    print(f"  📄 Mail text: {len(mail_text)} chars")

    # Parse
    mail_stores = parse_mail_text(mail_text)
    print(f"  ✅ Parsed {len(mail_stores)} stores")
    for s in mail_stores[:5]:
        print(f"     #{s['stt']} | {s['name_mail'][:50]} | {s['opening_date']}")
    if len(mail_stores) > 5:
        print(f"     ... +{len(mail_stores) - 5} more")

    if not mail_stores:
        print("  ❌ No stores parsed!")
        return

    # Read DSST
    from domains.nso.fetch_nso_mail import read_dsst
    dsst_lookup = read_dsst()

    # Load master
    from domains.nso.nso_master import NsoMaster
    master = NsoMaster()
    master.load()
    print(f"  📊 Master before: {len(master.stores)} stores")

    # Merge
    summary, added, updated = master.merge_mail(mail_stores, dsst_lookup)
    print(f"\n  {'─'*40}")
    print(f"  📊 Merge result:")
    print(f"     Total: {len(master.stores)}")
    print(f"     New:   {len(added)} {added[:5] if added else ''}")
    print(f"     Updated dates: {len(updated)} {updated[:5] if updated else ''}")

    # Save
    master.save()
    master.save_output(scan_summary=summary)

    # Export + Deploy
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

    # Telegram
    if args.send:
        print(f"\n  📤 Sending to Telegram...")
        msg = build_telegram_summary(master.stores)
        print(f"\n{msg}\n")
        send_telegram(msg)

    # Generate châm hàng Excel
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
