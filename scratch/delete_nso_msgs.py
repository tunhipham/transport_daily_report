import urllib.request, json

bot_token = '8786933573:AAHAus-L2ReuRM9q_Zr2IC122B62uNftisc'
chat_id = '-4511126388'

# Check range 2550-2560 for any remaining
deleted = 0
for mid in range(2550, 2565):
    url = f'https://api.telegram.org/bot{bot_token}/deleteMessage'
    payload = json.dumps({'chat_id': chat_id, 'message_id': mid}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get('ok'):
            print(f"  msg {mid}: DELETED")
            deleted += 1
    except Exception:
        pass

if deleted == 0:
    print("No more messages found. All clean!")
else:
    print(f"Deleted {deleted} more message(s)")
