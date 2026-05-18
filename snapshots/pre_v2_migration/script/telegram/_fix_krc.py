"""Fix KRC NSO groups: remove Liên Nguyễn, add Hào Tống @hubert286"""
import asyncio
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "telegram_client.json")
SESSION_FILE = os.path.join(REPO_ROOT, "config", ".telethon_session")

KRC_GROUPS = [
    "KRC - A195 (Nguyễn Sơn)",
    "KRC - A171 (Phạm Thế Hiển)",
    "KRC - A188 (Chung Cư Thuận Việt)",
    "KRC - A190 (Botanica Premier)",
]

REMOVE_USERNAME = "Mailienld"      # Liên Nguyễn
ADD_USERNAME = "hubert286"         # Hào Tống

async def main():
    from telethon import TelegramClient, errors
    from telethon.tl.functions.messages import DeleteChatUserRequest, AddChatUserRequest
    from telethon.tl.functions.channels import EditBannedRequest, InviteToChannelRequest
    from telethon.tl.types import Channel, Chat, ChatBannedRights

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    phone = config.get("phone")
    await client.start(phone=phone) if phone else await client.start()
    me = await client.get_me()
    print(f"✅ Logged in: {me.first_name} (@{me.username})\n")

    # Resolve users
    remove_entity = await client.get_entity(REMOVE_USERNAME)
    print(f"🗑️ Remove: {remove_entity.first_name} {remove_entity.last_name or ''} (@{REMOVE_USERNAME})")
    add_entity = await client.get_entity(ADD_USERNAME)
    print(f"➕ Add: {add_entity.first_name} {add_entity.last_name or ''} (@{ADD_USERNAME})\n")

    for group_name in KRC_GROUPS:
        print(f"{'='*50}")
        print(f"📁 {group_name}")
        print(f"{'='*50}")

        target = None
        async for d in client.iter_dialogs():
            if d.title == group_name:
                target = d.entity
                break
        if not target:
            print(f"  ❌ Not found!\n")
            continue

        is_channel = isinstance(target, Channel)

        # Check participants
        try:
            participants = await client.get_participants(target)
            current_ids = {p.id for p in participants}
        except:
            current_ids = set()

        # Remove Liên Nguyễn
        if remove_entity.id in current_ids:
            try:
                if is_channel:
                    await client(EditBannedRequest(
                        channel=target, participant=remove_entity,
                        banned_rights=ChatBannedRights(until_date=None, view_messages=True)
                    ))
                else:
                    await client(DeleteChatUserRequest(chat_id=target.id, user_id=remove_entity))
                print(f"  🗑️ Removed: {remove_entity.first_name}")
            except Exception as e:
                print(f"  ⚠️ Remove failed: {e}")
        else:
            print(f"  ⏭️ {remove_entity.first_name} not in group")
        await asyncio.sleep(2)

        # Add Hào Tống
        if add_entity.id in current_ids:
            print(f"  ⏭️ {add_entity.first_name} already in group")
        else:
            try:
                if is_channel:
                    await client(InviteToChannelRequest(channel=target, users=[add_entity]))
                else:
                    await client(AddChatUserRequest(chat_id=target.id, user_id=add_entity, fwd_limit=0))
                print(f"  ✅ Added: {add_entity.first_name} (@{ADD_USERNAME})")
            except errors.UserAlreadyParticipantError:
                print(f"  ⏭️ {add_entity.first_name} already in group")
            except Exception as e:
                print(f"  ⚠️ Add failed: {e}")
        await asyncio.sleep(3)
        print()

    await client.disconnect()
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
