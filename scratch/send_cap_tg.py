"""Send capacity PNGs to Telegram for today."""
import os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.path.insert(0, os.path.join(BASE, "script", "domains", "daily"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from generate import send_telegram_photo

output_dir = os.path.join(BASE, "output", "artifacts", "daily")
date_tag = "21052026"

cap_files = [
    (os.path.join(output_dir, f"BAO_CAO_{date_tag}_6_CAP_KRC.png"), "🏭 Capacity Forecast — KRC (Rau Củ)"),
    (os.path.join(output_dir, f"BAO_CAO_{date_tag}_7_CAP_KSL.png"), "🏭 Capacity Forecast — KSL Dry (Sáng+Tối)"),
]

caption = "📊 Báo cáo xuất kho 21/05/2026 — Bổ sung Capacity Forecast"

for img_path, label in cap_files:
    if os.path.exists(img_path):
        print(f"📤 Sending {os.path.basename(img_path)}...")
        pairs = send_telegram_photo(img_path, f"{caption}\n{label}")
        print(f"  ✅ Sent to {len(pairs)} group(s)")
    else:
        print(f"❌ Not found: {img_path}")

print("\n✅ Done!")
