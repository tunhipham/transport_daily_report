# Quick script: Send existing 11/05/2026 images to Telegram
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'script'))

from lib.telegram import (
    load_telegram_config_multi,
    send_telegram_photo,
    send_telegram_text,
    delete_messages_by_tag,
    load_sent_messages,
    save_sent_messages,
)

BASE = os.path.join(os.path.dirname(__file__), '..')
CONFIG = os.path.join(BASE, 'config', 'telegram.json')
SENT_FILE = os.path.join(BASE, 'output', 'state', 'sent_messages.json')
ARTIFACTS = os.path.join(BASE, 'output', 'artifacts', 'daily')

date_str = "11/05/2026"
date_tag = "11052026"

# Load history to get totals
history = json.load(open(os.path.join(BASE, 'output', 'state', 'history.json'), 'r', encoding='utf-8'))
entry = [h for h in history if h['date'] == date_str]
if not entry:
    print(f"❌ No history entry for {date_str}")
    sys.exit(1)
data = entry[-1]
print(f"📊 {date_str}: {data['total_tons']:.2f} tấn, {data['total_xe']} xe, {data['total_sthi']} ST, {data['total_items']:,.0f} items")

# Image paths
suffixes = ["1_BANG", "2_DONGGOP", "3_SANLUONG", "4_ITEMS", "5_XE"]
labels = ["📋 Bảng KPI", "🍩 % Đóng góp", "📈 Trend Sản lượng", "📦 Trend Items", "🚛 Trend Xe"]
img_paths = [os.path.join(ARTIFACTS, f"BAO_CAO_{date_tag}_{s}.png") for s in suffixes]

# Check all images exist
for p in img_paths:
    if not os.path.exists(p):
        print(f"❌ Missing: {p}")
        sys.exit(1)
    print(f"  ✅ {os.path.basename(p)} ({os.path.getsize(p):,} bytes)")

# Load telegram config
bot_token, chat_ids = load_telegram_config_multi(CONFIG, domain="daily")
print(f"\n📤 Sending to {len(chat_ids)} group(s)...")

# Delete old messages for this date
for chat_id in chat_ids:
    delete_messages_by_tag(SENT_FILE, f"{date_tag}_{chat_id}", bot_token, chat_id)

# Send images
caption = f"📊 Báo cáo xuất kho {date_str} — Tổng: {data['total_tons']:.2f} tấn, {data['total_xe']} xe, {data['total_sthi']} ST"
all_sent = []
for img_path, sec_label in zip(img_paths, labels):
    for chat_id in chat_ids:
        mid = send_telegram_photo(img_path, f"{caption}\n{sec_label}", bot_token, chat_id, fallback_document=True)
        if mid:
            all_sent.append((chat_id, mid))

# Send dashboard text
dashboard_text = f"📊 Dashboard đã cập nhật: {date_str}\n🔗 https://tunhipham.github.io/transport_daily_report/\n⏱ Refresh sau 1-2 phút để xem dữ liệu mới nhất"
for chat_id in chat_ids:
    mid = send_telegram_text(dashboard_text, bot_token, chat_id)
    if mid:
        all_sent.append((chat_id, mid))

# Save sent message IDs
if all_sent:
    sent_data = load_sent_messages(SENT_FILE)
    for chat_id, mid in all_sent:
        key = f"{date_tag}_{chat_id}"
        if key not in sent_data:
            sent_data[key] = []
        sent_data[key].append(mid)
    save_sent_messages(SENT_FILE, sent_data)
    n_groups = len(set(cid for cid, _ in all_sent))
    print(f"\n✅ Done! Sent {len(all_sent)} messages to {n_groups} group(s)")
else:
    print("\n❌ No messages sent")
