"""Delete old capacity PNGs from Telegram, then send new ones."""
import os, sys, json
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.path.insert(0, os.path.join(BASE, "script", "domains", "daily"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from generate import send_telegram_photo, load_telegram_config
from lib.telegram import delete_telegram_message

# Step 1: Delete old capacity messages
OLD_MSG_IDS = [2838, 2839, 2840, 2841]
bot_token, chat_ids = load_telegram_config()

print("🗑️ Deleting old capacity images...")
for msg_id in OLD_MSG_IDS:
    for chat_id in chat_ids:
        try:
            delete_telegram_message(msg_id, bot_token, chat_id)
            print(f"  ✅ Deleted msg {msg_id} from {chat_id}")
        except Exception as e:
            print(f"  ⚠ msg {msg_id} @ {chat_id}: {e}")

# Step 2: Generate new PNGs
print("\n🖼️ Generating new capacity PNGs...")
output_dir = os.path.join(BASE, "output", "artifacts", "daily")
cap_json_path = os.path.join(BASE, "docs", "data", "capacity_forecast.json")
with open(cap_json_path, "r", encoding="utf-8") as f:
    cap_data = json.load(f)
print(f"  KRC: {len(cap_data['krc']['data'])} days | KSL: {len(cap_data['ksl']['data'])} days")

from generate import _generate_capacity_pngs
paths = _generate_capacity_pngs(cap_data, output_dir, "21052026")

# Step 3: Send new PNGs
print("\n📤 Sending new capacity images...")
caption = "📊 Báo cáo xuất kho 21/05/2026"
cap_labels = ["🏭 Capacity Forecast — KRC (Rau Củ)", "🏭 Capacity Forecast — KSL Dry (Sáng+Tối)"]
for img_path, label in zip(paths, cap_labels):
    if os.path.exists(img_path):
        pairs = send_telegram_photo(img_path, f"{caption}\n{label}")
        print(f"  ✅ Sent {os.path.basename(img_path)} to {len(pairs)} group(s)")

print("\n✅ Done!")
