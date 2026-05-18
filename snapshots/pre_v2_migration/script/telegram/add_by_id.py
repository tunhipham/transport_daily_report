"""Add users to a group by their Telegram user ID."""
import asyncio, json, os, sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(REPO, "config", "telegram_client.json")
SESSION = os.path.join(REPO, "config", ".telethon_session")

async def add_by_id(group_name, user_ids):
    from telethon import TelegramClient, errors
    from telethon.tl.functions.messages import AddChatUserRequest
    from telethon.tl.functions.channels import InviteToChannelRequest
    from telethon.tl.types import Channel, Chat, InputPeerUser

    with open(CONFIG) as f:
        cfg = json.load(f)

    client = TelegramClient(SESSION, cfg["api_id"], cfg["api_hash"])
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Not logged in")
        return

    me = await client.get_me()
    print(f"✅ Logged in: {me.first_name}\n")

    # Find group
    target = None
    async for d in client.iter_dialogs():
        if d.title and group_name.lower() in d.title.lower():
            if isinstance(d.entity, (Channel, Chat)):
                target = d.entity
                print(f"📋 Group: {d.title} (ID: {d.entity.id})")
                break
    if not target:
        print(f"❌ Group not found: {group_name}")
        await client.disconnect()
        return

    # Add each user by ID
    for uid in user_ids:
        uid = int(uid)
        try:
            # Get the user entity by ID
            user = await client.get_entity(uid)
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            print(f"\n👤 Adding: {name} (ID: {uid})")

            if isinstance(target, Channel):
                await client(InviteToChannelRequest(channel=target, users=[user]))
            else:
                await client(AddChatUserRequest(chat_id=target.id, user_id=user, fwd_limit=0))

            print(f"  ✅ Added!")
        except errors.UserAlreadyParticipantError:
            print(f"  ⏭️ Already in group")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        await asyncio.sleep(5)

    await client.disconnect()
    print("\n✅ Done!")

if __name__ == "__main__":
    group = sys.argv[1]
    ids = sys.argv[2:]
    asyncio.run(add_by_id(group, ids))
