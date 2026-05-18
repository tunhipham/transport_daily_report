"""
Fix all: 
1. Create remaining 6 groups (A188, A190)
2. Add bot to ALL 12 groups  
3. Send DC notice to ALL 4 DC groups
"""
import asyncio
import json
import os
import sys
import requests as req

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "telegram_client.json")
SESSION_FILE = os.path.join(REPO_ROOT, "config", ".telethon_session")
BOT_CONFIG_FILE = os.path.join(REPO_ROOT, "config", "telegram.json")

DC_NOTICE_MSG = """📢 *Siêu thị lưu ý:*

Hàng DC sẽ châm hàng *4 ngày liên tục* cho NSO.

👉 Khai trương ngày D sẽ châm hàng từ ngày *D* đến hết ngày *D+3*
👉 Từ ngày *D+4* sẽ về hàng DC theo lịch daily"""

# All DC groups that need notice
DC_GROUPS = [
    "DC - A195 (Nguyễn Sơn)",
    "DC - A171 (Phạm Thế Hiển)",
    "DC - A188 (Chung Cư Thuận Việt)",
    "DC - A190 (Botanica Premier)",
]

async def main():
    from telethon import TelegramClient, errors
    from telethon.tl.functions.messages import AddChatUserRequest
    from telethon.tl.functions.channels import InviteToChannelRequest
    from telethon.tl.types import Channel, Chat

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    phone = config.get("phone")
    await client.start(phone=phone) if phone else await client.start()

    me = await client.get_me()
    print(f"✅ Logged in: {me.first_name} (@{me.username})\n")

    # === Step 1: Run batch for remaining groups ===
    print("=" * 60)
    print("STEP 1: Creating remaining groups (batch_nso.py)")
    print("=" * 60)
    
    # Import and run batch
    sys.path.insert(0, os.path.join(REPO_ROOT, "script", "telegram"))
    from batch_nso import fetch_sheet, parse_sheet, print_plan, search_and_resolve, DELAY_CREATE, DELAY_ADD
    from telethon.tl.functions.messages import CreateChatRequest

    header, data = fetch_sheet()
    lookup, groups = parse_sheet(data)
    
    # Check existing groups
    existing = {}
    async for d in client.iter_dialogs():
        if d.title:
            existing[d.title.lower()] = d.entity

    created_count = 0
    for i, g in enumerate(groups, 1):
        if g['name'].lower() in existing:
            print(f"  ⏭️ [{i}/{len(groups)}] {g['name']} — already exists")
            continue

        print(f"\n  [{i}/{len(groups)}] 🔨 Creating \"{g['name']}\"...")
        
        # Resolve members
        user_entities = []
        for name, handle in g['resolved']:
            try:
                val = int(handle) if handle.isdigit() else handle
                entity = await client.get_entity(val)
                user_entities.append(entity)
                ename = getattr(entity, 'first_name', '') or ''
                euname = getattr(entity, 'username', '') or 'N/A'
                print(f"    ✅ {ename} (@{euname})")
            except Exception as e:
                print(f"    ❌ {name} ({handle}): {e}")
            await asyncio.sleep(DELAY_ADD)

        # Search unresolved
        for name in g['unresolved']:
            entity = await search_and_resolve(client, name)
            if entity:
                user_entities.append(entity)
            else:
                print(f"    ⚠️ Unresolved: {name}")
            await asyncio.sleep(DELAY_ADD)

        if not user_entities:
            print(f"    ❌ No members — skipping")
            continue

        try:
            result = await client(CreateChatRequest(title=g['name'], users=user_entities))
            chat_id = None
            if hasattr(result, 'chats') and result.chats:
                chat_id = result.chats[0].id
            print(f"    🎉 Created! (ID: {chat_id or '?'})")
            created_count += 1
            # Refresh dialogs
            existing[g['name'].lower()] = None  # mark as created
        except errors.FloodWaitError as e:
            print(f"    ⏳ Rate limited! Waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"    ❌ Failed: {e}")

        if i < len(groups):
            await asyncio.sleep(DELAY_CREATE)

    print(f"\n  📊 Created {created_count} new groups\n")

    # === Step 2: Add bot to ALL groups ===
    print("=" * 60)
    print("STEP 2: Adding bot to ALL groups")
    print("=" * 60)

    # Load bot
    bot_entity = None
    bot_token = None
    try:
        with open(BOT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            bot_cfg = json.load(f)
        bot_token = bot_cfg.get('daily', {}).get('bot_token', '')
        if bot_token:
            r = req.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=15)
            bot_uname = r.json().get('result', {}).get('username', '')
            if bot_uname:
                bot_entity = await client.get_entity(bot_uname)
                print(f"  🤖 Bot: @{bot_uname}\n")
    except Exception as e:
        print(f"  ⚠️ Could not load bot: {e}")

    if not bot_entity:
        print("  ❌ Bot not available — skipping bot step")
    else:
        # Refresh dialog list
        all_groups = []
        async for d in client.iter_dialogs():
            if d.title and isinstance(d.entity, (Channel, Chat)):
                # Match our NSO groups
                for prefix in ["KRC - A", "ABA - A", "DC - A"]:
                    if d.title.startswith(prefix):
                        all_groups.append(d)
                        break

        for d in all_groups:
            target = d.entity
            # Check if bot already in group
            try:
                participants = await client.get_participants(target)
                bot_in = any(p.id == bot_entity.id for p in participants)
                if bot_in:
                    print(f"  ⏭️ {d.title} — bot already in group")
                    continue
            except Exception:
                pass

            try:
                if isinstance(target, Channel):
                    await client(InviteToChannelRequest(channel=target, users=[bot_entity]))
                else:
                    await client(AddChatUserRequest(chat_id=target.id, user_id=bot_entity, fwd_limit=0))
                print(f"  🤖 {d.title} — bot added!")
            except errors.UserAlreadyParticipantError:
                print(f"  ⏭️ {d.title} — bot already in group")
            except Exception as e:
                print(f"  ⚠️ {d.title} — bot add failed: {e}")
            await asyncio.sleep(2)

    # === Step 3: Send DC notice to ALL DC groups ===
    print(f"\n{'='*60}")
    print("STEP 3: Sending DC notice to DC groups")
    print("=" * 60)

    if not bot_token:
        print("  ❌ No bot token — cannot send DC notice")
    else:
        # Refresh dialogs to get latest
        dc_found = {}
        async for d in client.iter_dialogs():
            if d.title and d.title.startswith("DC - A"):
                dc_found[d.title] = d.entity

        for dc_name in DC_GROUPS:
            entity = dc_found.get(dc_name)
            if not entity:
                print(f"  ❌ {dc_name} — not found")
                continue

            chat_id = -entity.id
            try:
                r = req.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": DC_NOTICE_MSG, "parse_mode": "Markdown"},
                    timeout=15
                )
                if r.json().get("ok"):
                    print(f"  📢 {dc_name} — DC notice sent!")
                else:
                    print(f"  ⚠️ {dc_name} — {r.json().get('description')}")
            except Exception as e:
                print(f"  ⚠️ {dc_name} — error: {e}")
            await asyncio.sleep(2)

    await client.disconnect()
    print(f"\n✅ ALL DONE!")

if __name__ == "__main__":
    asyncio.run(main())
