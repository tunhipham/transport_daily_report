# -*- coding: utf-8 -*-
"""Delete recent NSO bot messages from Telegram group."""
import urllib.request, json, sys

BOT_TOKEN = "8786933573:AAHAus-L2ReuRM9q_Zr2IC122B62uNftisc"
CHAT_ID = "-4511126388"

# Get recent updates
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-20&allowed_updates=[%22message%22]"
try:
    resp = urllib.request.urlopen(url, timeout=10)
    data = json.loads(resp.read())
except Exception as e:
    print(f"Failed to get updates: {e}")
    sys.exit(1)

# Find messages from bot in NSO chat
bot_msgs = []
for u in data.get("result", []):
    msg = u.get("message") or u.get("channel_post") or {}
    if str(msg.get("chat", {}).get("id", "")) == CHAT_ID:
        from_user = msg.get("from", {})
        if from_user.get("is_bot"):
            bot_msgs.append(msg)

if not bot_msgs:
    print("No bot messages found in recent updates. Trying deleteMessage with recent IDs...")
    # Telegram getUpdates may not have old messages. Ask user for message IDs.
    print("Cannot auto-detect message IDs from getUpdates.")
    print("Will try to get chat history via getChat...")
    sys.exit(0)

print(f"Found {len(bot_msgs)} bot messages:")
for m in bot_msgs:
    mid = m["message_id"]
    text = (m.get("text") or m.get("caption") or "[photo/media]")[:80]
    print(f"  id={mid}: {text}")

# Delete each
for m in bot_msgs:
    mid = m["message_id"]
    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "message_id": mid}).encode()
    req = urllib.request.Request(del_url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get("ok"):
            print(f"  ✅ Deleted message {mid}")
        else:
            print(f"  ❌ Failed to delete {mid}: {result}")
    except Exception as e:
        print(f"  ❌ Error deleting {mid}: {e}")
