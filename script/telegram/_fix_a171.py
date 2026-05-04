"""Quick fix: remove wrong users + add correct users to A171 groups."""
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

# Wrong users added (from auto-search bug)
WRONG_IDS = [
    5590866435,   # HCM4 - LVL - GSM - Phụng Trần (wrong, should be Tuấn Cao)
]
# Note: Chí Nguyện (@HCM3_A144_ChiNguyen) also wrong
WRONG_USERNAMES = ["HCM3_A144_ChiNguyen"]

# Correct users to add
CORRECT_USERS = [
    2114593560,   # HCM10 - A114 - TC - Phong Trần - SC002310
    7272870275,   # HCM10 - PHG - GSM - Tuấn Cao - SC009565
    5601649330,   # HCM10 - A171 - TC - Tú Nguyễn - SC003669
]

# Target groups
GROUPS = [
    "KRC - A171 (Phạm Thế Hiển)",
    "ABA - A171 (Phạm Thế Hiển)",
    "DC - A171 (Phạm Thế Hiển)",
]

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

    # Resolve wrong users
    wrong_entities = []
    for uid in WRONG_IDS:
        try:
            e = await client.get_entity(uid)
            wrong_entities.append(e)
            print(f"❌ Wrong user (by ID): {e.first_name} {e.last_name or ''} (ID: {e.id})")
        except Exception as ex:
            print(f"⚠️ Cannot find wrong user ID {uid}: {ex}")
    for uname in WRONG_USERNAMES:
        try:
            e = await client.get_entity(uname)
            wrong_entities.append(e)
            print(f"❌ Wrong user (by username): {e.first_name} {e.last_name or ''} (@{uname})")
        except Exception as ex:
            print(f"⚠️ Cannot find wrong user @{uname}: {ex}")

    # Resolve correct users
    correct_entities = []
    for uid in CORRECT_USERS:
        try:
            e = await client.get_entity(uid)
            correct_entities.append(e)
            uname = f"@{e.username}" if e.username else "no username"
            print(f"✅ Correct user: {e.first_name} {e.last_name or ''} ({uname}, ID: {e.id})")
        except Exception as ex:
            print(f"⚠️ Cannot find correct user ID {uid}: {ex}")

    print()

    for group_name in GROUPS:
        print(f"\n{'='*50}")
        print(f"📁 {group_name}")
        print(f"{'='*50}")

        # Find group
        target = None
        async for d in client.iter_dialogs():
            if d.title == group_name:
                target = d.entity
                break

        if not target:
            print(f"  ❌ Group not found!")
            continue

        is_channel = isinstance(target, Channel)
        print(f"  Found (ID: {target.id}, type: {'channel' if is_channel else 'basic'})")

        # Get current participants
        try:
            participants = await client.get_participants(target)
            current_ids = {p.id for p in participants}
            print(f"  👥 Current members: {len(participants)}")
        except Exception as ex:
            print(f"  ⚠️ Cannot get participants: {ex}")
            current_ids = set()

        # Remove wrong users
        for we in wrong_entities:
            if we.id not in current_ids:
                print(f"  ⏭️ {we.first_name} not in group, skip remove")
                continue
            try:
                if is_channel:
                    await client(EditBannedRequest(
                        channel=target,
                        participant=we,
                        banned_rights=ChatBannedRights(
                            until_date=None,
                            view_messages=True
                        )
                    ))
                else:
                    await client(DeleteChatUserRequest(
                        chat_id=target.id,
                        user_id=we
                    ))
                print(f"  🗑️ Removed: {we.first_name} {we.last_name or ''}")
            except Exception as ex:
                print(f"  ⚠️ Remove failed for {we.first_name}: {ex}")
            await asyncio.sleep(2)

        # Add correct users
        for ce in correct_entities:
            if ce.id in current_ids:
                print(f"  ⏭️ {ce.first_name} already in group")
                continue
            try:
                if is_channel:
                    await client(InviteToChannelRequest(channel=target, users=[ce]))
                else:
                    await client(AddChatUserRequest(chat_id=target.id, user_id=ce, fwd_limit=0))
                uname = f"@{ce.username}" if ce.username else f"ID:{ce.id}"
                print(f"  ✅ Added: {ce.first_name} {ce.last_name or ''} ({uname})")
            except errors.UserAlreadyParticipantError:
                print(f"  ⏭️ {ce.first_name} already in group")
            except errors.UserPrivacyRestrictedError:
                print(f"  🔒 {ce.first_name} — privacy restricted")
            except Exception as ex:
                print(f"  ⚠️ Add failed for {ce.first_name}: {ex}")
            await asyncio.sleep(3)

    await client.disconnect()
    print(f"\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
