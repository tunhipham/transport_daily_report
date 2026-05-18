"""
Add bot vào hàng loạt group Telegram bằng account cá nhân.

Cách dùng:
  1. pip install telethon
  2. Lấy api_id & api_hash tại https://my.telegram.org/apps
  3. Chạy:  python add_bot_to_groups.py

Lần đầu chạy sẽ hỏi số điện thoại + OTP để đăng nhập.
Session được lưu lại, lần sau không cần đăng nhập lại.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# ══════════════════════════════════════════════
# CẤU HÌNH - THAY ĐỔI Ở ĐÂY
# ══════════════════════════════════════════════

# Lấy tại https://my.telegram.org/apps
API_ID = 0          # ← Thay bằng api_id của bạn (số nguyên)
API_HASH = ""       # ← Thay bằng api_hash của bạn (chuỗi)

# Username của bot cần add (không có @)
BOT_USERNAME = "ten_bot_cua_ban"  # ← Thay bằng username bot

# Delay giữa mỗi lần add (giây) — ĐỂ TRÁNH BỊ TELEGRAM RATE-LIMIT
DELAY_SECONDS = 15  # Khuyến nghị 10-20 giây

# ══════════════════════════════════════════════

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(SCRIPT_DIR, "telethon_session")
LOG_FILE = os.path.join(SCRIPT_DIR, "add_bot_log.json")


async def main():
    try:
        from telethon import TelegramClient, errors
        from telethon.tl.functions.channels import InviteToChannelRequest
        from telethon.tl.functions.messages import AddChatUserRequest
        from telethon.tl.types import Channel, Chat
    except ImportError:
        print("❌ Chưa cài telethon. Chạy lệnh:")
        print("   pip install telethon")
        sys.exit(1)

    if API_ID == 0 or not API_HASH:
        print("❌ Chưa điền API_ID và API_HASH!")
        print("   Vào https://my.telegram.org/apps để lấy.")
        sys.exit(1)

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start()
    print("✅ Đã đăng nhập Telegram!\n")

    # ── Bước 1: Lấy entity của bot ──
    try:
        bot_entity = await client.get_entity(BOT_USERNAME)
        print(f"🤖 Bot: @{BOT_USERNAME} (ID: {bot_entity.id})\n")
    except Exception as e:
        print(f"❌ Không tìm thấy bot @{BOT_USERNAME}: {e}")
        await client.disconnect()
        sys.exit(1)

    # ── Bước 2: Lấy danh sách tất cả group ──
    print("📋 Đang lấy danh sách group...")
    all_groups = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            # Channel = supergroup/channel, Chat = basic group
            is_supergroup = isinstance(entity, Channel) and entity.megagroup
            is_basic_group = isinstance(entity, Chat)
            is_channel_group = isinstance(entity, Channel) and not entity.megagroup and not entity.broadcast

            if is_supergroup or is_basic_group or is_channel_group:
                all_groups.append({
                    "id": entity.id,
                    "title": dialog.title,
                    "type": "supergroup" if is_supergroup else ("basic" if is_basic_group else "channel"),
                    "entity": entity,
                })

    print(f"   Tìm thấy {len(all_groups)} group.\n")

    if not all_groups:
        print("⚠ Không tìm thấy group nào!")
        await client.disconnect()
        return

    # ── Bước 3: Lọc group (tuỳ chọn) ──
    # Mặc định add vào TẤT CẢ group. 
    # Nếu muốn lọc, bỏ comment và sửa filter bên dưới:
    # all_groups = [g for g in all_groups if "siêu thị" in g["title"].lower()]

    print(f"🎯 Sẽ add bot vào {len(all_groups)} group.")
    print(f"⏱  Ước tính thời gian: ~{len(all_groups) * DELAY_SECONDS // 60} phút")
    print(f"   (Delay {DELAY_SECONDS}s giữa mỗi group để tránh rate-limit)\n")

    confirm = input("Bấm Enter để bắt đầu (hoặc gõ 'q' để thoát): ").strip()
    if confirm.lower() == 'q':
        print("Đã huỷ.")
        await client.disconnect()
        return

    # ── Bước 4: Add bot vào từng group ──
    results = {"success": [], "already_in": [], "no_permission": [], "error": []}
    total = len(all_groups)

    for i, group in enumerate(all_groups, 1):
        title = group["title"]
        entity = group["entity"]
        prefix = f"[{i}/{total}]"

        try:
            if isinstance(entity, Channel):
                # Supergroup / Channel
                await client(InviteToChannelRequest(
                    channel=entity,
                    users=[bot_entity]
                ))
            else:
                # Basic group
                await client(AddChatUserRequest(
                    chat_id=entity.id,
                    user_id=bot_entity,
                    fwd_limit=0
                ))

            print(f"  ✅ {prefix} {title}")
            results["success"].append(title)

        except errors.UserAlreadyParticipantError:
            print(f"  ⏭  {prefix} {title} — bot đã có trong group")
            results["already_in"].append(title)

        except errors.ChatAdminRequiredError:
            print(f"  🔒 {prefix} {title} — bạn không có quyền admin")
            results["no_permission"].append(title)

        except errors.UserNotMutualContactError:
            print(f"  🔒 {prefix} {title} — bot chưa được phép add vào group")
            results["no_permission"].append(title)

        except errors.FloodWaitError as e:
            print(f"  ⏳ {prefix} Telegram yêu cầu chờ {e.seconds}s (rate-limit)...")
            await asyncio.sleep(e.seconds + 5)
            # Retry
            try:
                if isinstance(entity, Channel):
                    await client(InviteToChannelRequest(channel=entity, users=[bot_entity]))
                else:
                    await client(AddChatUserRequest(chat_id=entity.id, user_id=bot_entity, fwd_limit=0))
                print(f"  ✅ {prefix} {title} (retry OK)")
                results["success"].append(title)
            except Exception as e2:
                print(f"  ❌ {prefix} {title} — retry failed: {e2}")
                results["error"].append({"title": title, "error": str(e2)})

        except Exception as e:
            print(f"  ❌ {prefix} {title} — {e}")
            results["error"].append({"title": title, "error": str(e)})

        # Delay để tránh rate-limit
        if i < total:
            await asyncio.sleep(DELAY_SECONDS)

    # ── Bước 5: Tổng kết ──
    print("\n" + "=" * 50)
    print("📊 KẾT QUẢ:")
    print(f"  ✅ Thành công:      {len(results['success'])}")
    print(f"  ⏭  Đã có sẵn:      {len(results['already_in'])}")
    print(f"  🔒 Không có quyền:  {len(results['no_permission'])}")
    print(f"  ❌ Lỗi:             {len(results['error'])}")
    print("=" * 50)

    # Lưu log
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "bot": BOT_USERNAME,
        "results": {
            "success": results["success"],
            "already_in": results["already_in"],
            "no_permission": results["no_permission"],
            "error": results["error"],
        }
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Log đã lưu tại: {LOG_FILE}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
