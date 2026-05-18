"""
Telegram Group Management — Tạo group + add members bằng account cá nhân.

Usage:
  python manage_group.py create --name "Group Name" --members @user1 @user2 +84xxx
  python manage_group.py add --group "Group Name" --members @user1
  python manage_group.py add --group "Group Name" --members @bot_username --bot
  python manage_group.py list
  python manage_group.py info --group "Group Name"

Lần đầu chạy sẽ hỏi số điện thoại + OTP để đăng nhập.
Session được lưu lại, lần sau không cần đăng nhập lại.
"""

import argparse
import asyncio
import json
import os
import sys

# Fix Windows console encoding for Vietnamese
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "telegram_client.json")
SESSION_FILE = os.path.join(REPO_ROOT, "config", ".telethon_session")

# Delay giữa mỗi lần add member (giây) — tránh rate-limit
DELAY_SECONDS = 10


def load_config():
    """Load API credentials from config file."""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file not found: {CONFIG_FILE}")
        print("   Tạo file với nội dung:")
        print('   {"api_id": YOUR_ID, "api_hash": "YOUR_HASH"}')
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    api_id = config.get("api_id", 0)
    api_hash = config.get("api_hash", "")

    if not api_id or not api_hash:
        print("❌ api_id hoặc api_hash trống trong config!")
        print(f"   File: {CONFIG_FILE}")
        sys.exit(1)

    return api_id, api_hash


async def get_client():
    """Create and start Telethon client."""
    try:
        from telethon import TelegramClient
    except ImportError:
        print("❌ Chưa cài telethon. Chạy:")
        print("   pip install telethon")
        sys.exit(1)

    api_id, api_hash = load_config()

    # Load phone from config if available (avoids interactive stdin issues)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    phone = config.get("phone", None)

    client = TelegramClient(SESSION_FILE, api_id, api_hash)

    if phone:
        await client.start(phone=phone)
    else:
        await client.start()

    me = await client.get_me()
    print(f"✅ Đã đăng nhập: {me.first_name} (@{me.username or 'N/A'})\n")
    return client


async def cmd_create(args):
    """Tạo group mới + add members."""
    from telethon.tl.functions.messages import CreateChatRequest
    from telethon import errors

    client = await get_client()

    group_name = args.name
    member_inputs = args.members or []

    print(f"📋 Tạo group: \"{group_name}\"")
    if member_inputs:
        print(f"👥 Members to add: {', '.join(member_inputs)}")
    print()

    # Resolve member entities (supports @username, +phone, or numeric user ID)
    resolved_users = []
    for m in member_inputs:
        try:
            # If it's a pure number, treat as user ID
            lookup = int(m) if m.isdigit() else m
            entity = await client.get_entity(lookup)
            resolved_users.append(entity)
            name = getattr(entity, 'first_name', '') or ''
            uname = getattr(entity, 'username', '') or ''
            print(f"  ✅ Found: {name} (@{uname}) — ID: {entity.id}")
        except Exception as e:
            print(f"  ❌ Không tìm thấy \"{m}\": {e}")

    if not resolved_users:
        print("\n⚠️  Không resolve được member nào.")
        print("   Tạo group trống (chỉ có bạn)? (y/n): ", end="")
        confirm = input().strip().lower()
        if confirm != 'y':
            print("Đã hủy.")
            await client.disconnect()
            return

    print(f"\n🔨 Đang tạo group \"{group_name}\"...")

    try:
        # CreateChatRequest cần ít nhất 1 user khác
        # Nếu không có ai, tạo với bot rồi kick sau
        if resolved_users:
            result = await client(CreateChatRequest(
                title=group_name,
                users=resolved_users
            ))
        else:
            # Tạo group trống: cần ít nhất 1 user
            # Sẽ add bot tạm rồi user tự kick nếu cần
            bot_token_file = os.path.join(REPO_ROOT, "config", "telegram.json")
            if os.path.exists(bot_token_file):
                with open(bot_token_file, 'r') as f:
                    bot_config = json.load(f)
                # Lấy bot username từ token
                import aiohttp
                token = bot_config.get('daily', {}).get('bot_token', '')
                if token:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                            data = await resp.json()
                            bot_username = data.get('result', {}).get('username', '')
                            if bot_username:
                                bot_entity = await client.get_entity(bot_username)
                                result = await client(CreateChatRequest(
                                    title=group_name,
                                    users=[bot_entity]
                                ))
                                print(f"  ℹ️  Added bot @{bot_username} để tạo group (Telegram yêu cầu ≥1 member)")
                            else:
                                print("❌ Không tạo được group trống (cần ít nhất 1 member)")
                                await client.disconnect()
                                return
                else:
                    print("❌ Không tạo được group trống (cần ít nhất 1 member)")
                    await client.disconnect()
                    return
            else:
                print("❌ Không tạo được group trống (cần ít nhất 1 member)")
                await client.disconnect()
                return

        # Get the created chat — handle different response types
        if hasattr(result, 'chats') and result.chats:
            chat = result.chats[0]
            print(f"\n🎉 Group đã tạo thành công!")
            print(f"   📝 Tên: {chat.title}")
            print(f"   🆔 ID: {chat.id}")
        elif hasattr(result, 'updates'):
            # Extract from updates
            for update in result.updates:
                if hasattr(update, 'message') and hasattr(update.message, 'peer_id'):
                    chat_id = getattr(update.message.peer_id, 'chat_id', None)
                    if chat_id:
                        print(f"\n🎉 Group đã tạo thành công!")
                        print(f"   📝 Tên: {group_name}")
                        print(f"   🆔 ID: {chat_id}")
                        break
            else:
                print(f"\n🎉 Group đã tạo thành công!")
                print(f"   📝 Tên: {group_name}")
        else:
            # Fallback: group was created, fetch it from dialogs
            print(f"\n🎉 Group đã tạo (đang tìm ID)...")
            async for dialog in client.iter_dialogs():
                if dialog.title == group_name:
                    print(f"   📝 Tên: {dialog.title}")
                    print(f"   🆔 ID: {dialog.entity.id}")
                    break
            else:
                print(f"   📝 Tên: {group_name}")
                print(f"   (Tạo xong nhưng không lấy được ID)")
        print(f"   👑 Owner: BẠN")

    except errors.FloodWaitError as e:
        print(f"⏳ Rate limit! Chờ {e.seconds}s...")
        await asyncio.sleep(e.seconds + 5)
        print("Thử lại...")
    except Exception as e:
        print(f"❌ Lỗi tạo group: {e}")

    await client.disconnect()


async def cmd_add(args):
    """Add members vào group đã có."""
    from telethon.tl.functions.messages import AddChatUserRequest
    from telethon.tl.functions.channels import InviteToChannelRequest
    from telethon.tl.types import Channel, Chat
    from telethon import errors

    client = await get_client()

    group_name = args.group
    member_inputs = args.members or []

    if not member_inputs:
        print("❌ Cần chỉ định --members")
        await client.disconnect()
        return

    # Tìm group
    print(f"🔍 Tìm group \"{group_name}\"...")
    target_group = None
    async for dialog in client.iter_dialogs():
        if dialog.title and group_name.lower() in dialog.title.lower():
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                target_group = entity
                print(f"  ✅ Found: {dialog.title} (ID: {entity.id})")
                break

    if not target_group:
        print(f"  ❌ Không tìm thấy group \"{group_name}\"")
        await client.disconnect()
        return

    # Resolve + add members
    print(f"\n👥 Adding {len(member_inputs)} member(s)...")
    results = {"success": [], "failed": []}

    for i, m in enumerate(member_inputs, 1):
        try:
            # If it's a pure number, treat as user ID
            lookup = int(m) if m.isdigit() else m
            entity = await client.get_entity(lookup)
            name = getattr(entity, 'first_name', '') or m

            if isinstance(target_group, Channel):
                await client(InviteToChannelRequest(
                    channel=target_group,
                    users=[entity]
                ))
            else:
                await client(AddChatUserRequest(
                    chat_id=target_group.id,
                    user_id=entity,
                    fwd_limit=0
                ))

            print(f"  ✅ [{i}/{len(member_inputs)}] {name}")
            results["success"].append(name)

        except errors.UserAlreadyParticipantError:
            print(f"  ⏭️  [{i}/{len(member_inputs)}] {m} — đã có trong group")
            results["success"].append(m)

        except errors.ChatAdminRequiredError:
            print(f"  🔒 [{i}/{len(member_inputs)}] {m} — bạn không có quyền admin")
            results["failed"].append(m)

        except errors.UserPrivacyRestrictedError:
            print(f"  🔒 [{i}/{len(member_inputs)}] {m} — user bật privacy, không add được")
            results["failed"].append(m)

        except errors.FloodWaitError as e:
            print(f"  ⏳ Rate limit! Chờ {e.seconds}s...")
            await asyncio.sleep(e.seconds + 5)

        except Exception as e:
            print(f"  ❌ [{i}/{len(member_inputs)}] {m} — {e}")
            results["failed"].append(m)

        if i < len(member_inputs):
            await asyncio.sleep(DELAY_SECONDS)

    print(f"\n📊 Kết quả: ✅ {len(results['success'])} | ❌ {len(results['failed'])}")
    await client.disconnect()


async def cmd_list(args):
    """Liệt kê tất cả groups."""
    from telethon.tl.types import Channel, Chat

    client = await get_client()

    print("📋 Danh sách groups:\n")
    count = 0
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            is_supergroup = isinstance(entity, Channel) and entity.megagroup
            is_basic = isinstance(entity, Chat)
            is_channel = isinstance(entity, Channel) and entity.broadcast

            if is_supergroup or is_basic:
                gtype = "supergroup" if is_supergroup else "basic"
                count += 1
                print(f"  {count}. {dialog.title} [{gtype}] (ID: {entity.id})")

    print(f"\n  Tổng: {count} groups")
    await client.disconnect()


async def cmd_info(args):
    """Xem thông tin group."""
    from telethon.tl.types import Channel, Chat

    client = await get_client()

    group_name = args.group
    print(f"🔍 Tìm group \"{group_name}\"...\n")

    async for dialog in client.iter_dialogs():
        if dialog.title and group_name.lower() in dialog.title.lower():
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                print(f"📝 Tên: {dialog.title}")
                print(f"🆔 ID: {entity.id}")

                if isinstance(entity, Channel):
                    gtype = "supergroup" if entity.megagroup else "channel"
                else:
                    gtype = "basic group"
                print(f"📦 Type: {gtype}")

                # Get participants
                try:
                    participants = await client.get_participants(entity)
                    print(f"👥 Members: {len(participants)}")
                    print()
                    for p in participants:
                        name = p.first_name or ""
                        if p.last_name:
                            name += f" {p.last_name}"
                        uname = f"@{p.username}" if p.username else "no username"
                        bot_tag = " 🤖" if p.bot else ""
                        print(f"  • {name} ({uname}){bot_tag}")
                except Exception as e:
                    print(f"  ⚠️ Không lấy được danh sách members: {e}")

                await client.disconnect()
                return

    print(f"❌ Không tìm thấy group \"{group_name}\"")
    await client.disconnect()


# DC NSO notice preset message
DC_NOTICE_MSG = """📢 *Siêu thị lưu ý:*

Hàng DC sẽ châm hàng *4 ngày liên tục* cho NSO.

👉 Khai trương ngày D sẽ châm hàng từ ngày *D* đến hết ngày *D+3*
👉 Từ ngày *D+4* sẽ về hàng DC theo lịch daily"""


async def cmd_notify(args):
    """Gửi tin nhắn bot vào group."""
    import requests as req

    group_name = args.group
    message = args.message
    dc_notice = getattr(args, 'dc_notice', False)

    if not message and not dc_notice:
        print("❌ Cần --message hoặc --dc-notice")
        return

    if dc_notice:
        message = DC_NOTICE_MSG

    # Load bot token
    bot_config_file = os.path.join(REPO_ROOT, "config", "telegram.json")
    if not os.path.exists(bot_config_file):
        print(f"❌ Bot config not found: {bot_config_file}")
        return

    with open(bot_config_file, 'r', encoding='utf-8') as f:
        bot_config = json.load(f)
    bot_token = bot_config.get('daily', {}).get('bot_token', '')
    if not bot_token:
        print("❌ Bot token trống!")
        return

    # Find group via Telethon to get chat_id
    client = await get_client()

    from telethon.tl.types import Channel, Chat
    target_id = None
    async for dialog in client.iter_dialogs():
        if dialog.title and group_name.lower() in dialog.title.lower():
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                target_id = entity.id
                print(f"📋 Group: {dialog.title} (ID: {target_id})")
                break

    await client.disconnect()

    if not target_id:
        print(f"❌ Không tìm thấy group \"{group_name}\"")
        return

    # Send via Bot API (basic group IDs need negative prefix)
    chat_id = -target_id
    r = req.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    )
    result = r.json()

    if result.get("ok"):
        print(f"✅ Bot đã gửi tin nhắn vào group!")
    else:
        print(f"❌ Lỗi gửi: {result.get('description', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(
        description="Telegram Group Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create --name "KFM Team" --members @user1 @user2
  %(prog)s add --group "KFM Team" --members @user3 +84123456789
  %(prog)s list
  %(prog)s info --group "KFM Team"
  %(prog)s notify --group "DC - A178" --dc-notice
  %(prog)s notify --group "Group Name" --message "Custom message"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    p_create = subparsers.add_parser("create", help="Tạo group mới")
    p_create.add_argument("--name", required=True, help="Tên group")
    p_create.add_argument("--members", nargs="+", help="Username (@xxx), phone (+84xxx), hoặc user ID (số)")

    # add
    p_add = subparsers.add_parser("add", help="Add members vào group")
    p_add.add_argument("--group", required=True, help="Tên group (tìm theo tên)")
    p_add.add_argument("--members", nargs="+", required=True, help="Members to add")
    p_add.add_argument("--bot", action="store_true", help="Add bot (không check mutual contact)")

    # list
    subparsers.add_parser("list", help="Liệt kê groups")

    # info
    p_info = subparsers.add_parser("info", help="Xem info group")
    p_info.add_argument("--group", required=True, help="Tên group")

    # notify
    p_notify = subparsers.add_parser("notify", help="Gửi tin nhắn bot vào group")
    p_notify.add_argument("--group", required=True, help="Tên group")
    p_notify.add_argument("--message", type=str, help="Nội dung tin nhắn")
    p_notify.add_argument("--dc-notice", action="store_true", help="Gửi thông báo lưu ý DC NSO")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "create": cmd_create,
        "add": cmd_add,
        "list": cmd_list,
        "info": cmd_info,
        "notify": cmd_notify,
    }

    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
