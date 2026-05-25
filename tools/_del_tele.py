# -*- coding: utf-8 -*-
"""Delete 4 most recent bot messages from NSO Telegram group."""
import urllib.request, json, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BOT_TOKEN = "8786933573:AAHAus-L2ReuRM9q_Zr2IC122B62uNftisc"
CHAT_ID = "-4511126388"

def api(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return json.loads(body) if body else {"ok": False}
    except Exception as e:
        return {"ok": False, "description": str(e)}

# Send temp message to get current message_id
result = api("sendMessage", {"chat_id": CHAT_ID, "text": "."})
if not result.get("ok"):
    print(f"FAIL: {result}")
    sys.exit(1)

ref_id = result["result"]["message_id"]
print(f"Ref ID: {ref_id}")
api("deleteMessage", {"chat_id": CHAT_ID, "message_id": ref_id})
print(f"Deleted temp {ref_id}")

# Delete 4 messages before this
deleted = 0
for offset in range(1, 20):
    mid = ref_id - offset
    result = api("deleteMessage", {"chat_id": CHAT_ID, "message_id": mid})
    if result.get("ok"):
        deleted += 1
        print(f"  OK deleted {mid}")
        if deleted >= 4:
            break
    else:
        desc = result.get("description", "")
        if "not found" in desc or "can't be deleted" in desc:
            print(f"  SKIP {mid}")
        else:
            print(f"  FAIL {mid}: {desc}")

print(f"Total deleted: {deleted}")
