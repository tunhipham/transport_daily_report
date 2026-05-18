"""Search Telegram contacts/dialogs by display name."""
import asyncio, json, os, sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(REPO, "config", "telegram_client.json")
SESSION = os.path.join(REPO, "config", ".telethon_session")

async def search(names):
    from telethon import TelegramClient
    from telethon.tl.functions.contacts import SearchRequest
    
    with open(CONFIG) as f:
        cfg = json.load(f)
    
    client = TelegramClient(SESSION, cfg["api_id"], cfg["api_hash"])
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ Not logged in")
        return
    
    me = await client.get_me()
    print(f"✅ Logged in: {me.first_name}\n")
    
    for name in names:
        print(f"🔍 Searching: \"{name}\"")
        
        # Method 1: Search contacts
        try:
            result = await client(SearchRequest(q=name, limit=10))
            if result.users:
                for u in result.users:
                    fname = u.first_name or ""
                    lname = u.last_name or ""
                    uname = f"@{u.username}" if u.username else "no username"
                    print(f"  📌 {fname} {lname} ({uname}) — ID: {u.id}")
            else:
                print(f"  ⚠️ No contacts found")
        except Exception as e:
            print(f"  ❌ Search error: {e}")
        
        # Method 2: Search in dialogs
        print(f"  📂 Checking dialogs...")
        count = 0
        async for dialog in client.iter_dialogs():
            if dialog.is_user:
                entity = dialog.entity
                full = f"{entity.first_name or ''} {entity.last_name or ''}".strip().lower()
                if name.lower() in full or any(n.lower() in full for n in name.split()):
                    uname = f"@{entity.username}" if entity.username else "no username"
                    print(f"  💬 {entity.first_name} {entity.last_name or ''} ({uname}) — ID: {entity.id}")
                    count += 1
        if count == 0:
            print(f"  ⚠️ No dialogs found")
        print()
    
    await client.disconnect()

if __name__ == "__main__":
    names = sys.argv[1:] if len(sys.argv) > 1 else ["Thọ Nguyễn", "Hường Hồ"]
    asyncio.run(search(names))
