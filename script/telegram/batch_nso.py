"""
Batch NSO — Auto-create Telegram groups from Google Sheet.

Chỉ đọc cột A→E:
  A: no.
  B: store_code
  C: group_name   → tên group cần tạo
  D: member        → danh sách members (multiline)
  E: tag_user      → (optional, dùng cho DC notice)

Cột I,J dùng làm bảng lookup: user_info → @username

Usage:
  python batch_nso.py                    # Dry run
  python batch_nso.py --execute          # Tạo groups
  python batch_nso.py --execute --notice # Tạo + gửi DC notice
"""

import argparse
import asyncio
import csv
import io
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

SHEET_ID = "1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# Members không có username — dùng Telegram user ID
FIXED_IDS = {
    "KFM - SCM - Thọ Nguyễn - SC006747": 5593486255,
}

DELAY_CREATE = 15
DELAY_ADD = 2

DC_NOTICE_MSG = """📢 *Siêu thị lưu ý:*

Hàng DC sẽ châm hàng *4 ngày liên tục* cho NSO.

👉 Khai trương ngày D sẽ châm hàng từ ngày *D* đến hết ngày *D+3*
👉 Từ ngày *D+4* sẽ về hàng DC theo lịch daily"""


def fetch_sheet():
    """Download and parse the Google Sheet CSV."""
    print("📥 Fetching Google Sheet...")
    r = req.get(SHEET_URL)
    r.raise_for_status()
    text = r.content.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    header = rows[0]
    data = rows[1:]
    print(f"  ✅ {len(data)} rows loaded\n")
    return header, data


def parse_sheet(data):
    """
    Parse sheet:
    - Cột I (9), J (10): bảng lookup user_info → @username
    - Cột C (2): group_name → mỗi row có group_name = 1 group cần tạo
    - Cột D (3): members (multiline)
    """
    # --- Build username lookup from columns I, J ---
    lookup = {}
    for row in data:
        if len(row) > 10:
            user_info = row[9].strip()
            username = row[10].strip()
            if user_info and username:
                lookup[user_info] = username

    # Add fixed IDs
    for name, uid in FIXED_IDS.items():
        if name not in lookup:
            lookup[name] = str(uid)

    print(f"📋 Username lookup: {len(lookup)} entries")
    for name, handle in lookup.items():
        print(f"  {name} → {handle}")
    print()

    # --- Build groups from columns A→E ---
    groups = []
    for row in data:
        if len(row) < 4:
            continue

        group_name = row[2].strip()  # Col C
        members_raw = row[3].strip()  # Col D

        if not group_name:
            continue

        # Parse multiline members
        members = [m.strip() for m in members_raw.split("\n") if m.strip()]

        # Resolve each member
        resolved = []
        unresolved = []
        for m in members:
            if m in lookup:
                resolved.append((m, lookup[m]))
            elif m in FIXED_IDS:
                resolved.append((m, str(FIXED_IDS[m])))
            else:
                unresolved.append(m)

        groups.append({
            "name": group_name,
            "resolved": resolved,
            "unresolved": unresolved,
        })

    return lookup, groups


def print_plan(groups):
    """Print what will be created."""
    print("=" * 60)
    print(f"📋 PLAN: Create {len(groups)} group(s)")
    print("=" * 60)

    for i, g in enumerate(groups, 1):
        print(f"\n  {i}. 📁 {g['name']}")
        print(f"     Members ({len(g['resolved'])} resolved, {len(g['unresolved'])} unresolved):")
        for name, handle in g['resolved']:
            print(f"       ✅ {name} → {handle}")
        for name in g['unresolved']:
            print(f"       ❌ {name} → ???")

    print(f"\n  + 🤖 Bot will be added to all groups")
    print()


async def execute(groups, send_notice=False):
    """Create groups via Telethon."""
    from telethon import TelegramClient, errors
    from telethon.tl.functions.messages import CreateChatRequest, AddChatUserRequest
    from telethon.tl.functions.channels import InviteToChannelRequest
    from telethon.tl.types import Channel, Chat

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    phone = config.get("phone")
    await client.start(phone=phone) if phone else await client.start()

    me = await client.get_me()
    print(f"✅ Logged in: {me.first_name} (@{me.username})\n")

    # Existing groups — avoid duplicates
    existing = set()
    async for d in client.iter_dialogs():
        if d.title:
            existing.add(d.title.lower())

    # Bot entity
    bot_entity = None
    try:
        with open(BOT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            bot_cfg = json.load(f)
        bot_token = bot_cfg.get('daily', {}).get('bot_token', '')
        if bot_token:
            r = req.get(f"https://api.telegram.org/bot{bot_token}/getMe")
            bot_uname = r.json().get('result', {}).get('username', '')
            if bot_uname:
                bot_entity = await client.get_entity(bot_uname)
                print(f"🤖 Bot: @{bot_uname}\n")
    except Exception as e:
        print(f"⚠️ Could not load bot: {e}\n")

    results = {"created": [], "skipped": [], "failed": []}

    for i, g in enumerate(groups, 1):
        print(f"\n{'='*50}")
        print(f"[{i}/{len(groups)}] 📁 {g['name']}")
        print(f"{'='*50}")

        if g['name'].lower() in existing:
            print(f"  ⏭️ Already exists — skipping")
            results["skipped"].append(g['name'])
            continue

        # Resolve member entities
        user_entities = []
        for name, handle in g['resolved']:
            try:
                val = int(handle) if handle.isdigit() else handle
                entity = await client.get_entity(val)
                user_entities.append(entity)
                ename = getattr(entity, 'first_name', '') or ''
                euname = getattr(entity, 'username', '') or 'N/A'
                print(f"  ✅ {ename} (@{euname})")
            except Exception as e:
                print(f"  ❌ {name} ({handle}): {e}")
            await asyncio.sleep(DELAY_ADD)

        for name in g['unresolved']:
            print(f"  ⚠️ Unresolved: {name}")

        if not user_entities:
            print(f"  ❌ No members — skipping")
            results["failed"].append(g['name'])
            continue

        # Create group
        try:
            print(f"\n  🔨 Creating \"{g['name']}\"...")
            result = await client(CreateChatRequest(title=g['name'], users=user_entities))

            chat_id = None
            if hasattr(result, 'chats') and result.chats:
                chat_id = result.chats[0].id
                print(f"  🎉 Created! ID: {chat_id}")
            else:
                print(f"  🎉 Created!")

            results["created"].append(g['name'])

            # Add bot
            if bot_entity:
                await asyncio.sleep(3)
                try:
                    target = None
                    async for d in client.iter_dialogs():
                        if d.title == g['name']:
                            target = d.entity
                            break
                    if target:
                        if isinstance(target, Channel):
                            await client(InviteToChannelRequest(channel=target, users=[bot_entity]))
                        else:
                            await client(AddChatUserRequest(chat_id=target.id, user_id=bot_entity, fwd_limit=0))
                        print(f"  🤖 Bot added!")
                except errors.UserAlreadyParticipantError:
                    print(f"  🤖 Bot already in group")
                except Exception as e:
                    print(f"  ⚠️ Bot add failed: {e}")

            # DC notice (optional)
            if send_notice and chat_id and g['name'].upper().startswith('DC'):
                await asyncio.sleep(2)
                try:
                    bt = bot_cfg.get('daily', {}).get('bot_token', '') if 'bot_cfg' in dir() else ''
                    if not bt:
                        with open(BOT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                            bt = json.load(f).get('daily', {}).get('bot_token', '')
                    if bt:
                        r = req.post(
                            f"https://api.telegram.org/bot{bt}/sendMessage",
                            json={"chat_id": -chat_id, "text": DC_NOTICE_MSG, "parse_mode": "Markdown"}
                        )
                        if r.json().get("ok"):
                            print(f"  📢 DC notice sent!")
                        else:
                            print(f"  ⚠️ DC notice failed: {r.json().get('description')}")
                except Exception as e:
                    print(f"  ⚠️ DC notice error: {e}")

        except errors.FloodWaitError as e:
            print(f"  ⏳ Rate limited! Waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds + 5)
            results["failed"].append(g['name'])
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results["failed"].append(g['name'])

        if i < len(groups):
            print(f"\n  ⏳ Waiting {DELAY_CREATE}s...")
            await asyncio.sleep(DELAY_CREATE)

    await client.disconnect()

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"  ✅ Created: {len(results['created'])}")
    for n in results['created']:
        print(f"     • {n}")
    print(f"  ⏭️ Skipped: {len(results['skipped'])}")
    for n in results['skipped']:
        print(f"     • {n}")
    print(f"  ❌ Failed: {len(results['failed'])}")
    for n in results['failed']:
        print(f"     • {n}")


def main():
    parser = argparse.ArgumentParser(description="Batch NSO Group Creation")
    parser.add_argument("--execute", action="store_true", help="Actually create (default: dry run)")
    parser.add_argument("--notice", action="store_true", help="Send DC notice for DC groups")
    args = parser.parse_args()

    header, data = fetch_sheet()
    lookup, groups = parse_sheet(data)
    print_plan(groups)

    if not groups:
        print("⚠️  Không tìm thấy group nào trong Sheet (cột C trống).")
        return

    if not args.execute:
        print("⚠️  DRY RUN — nothing created.")
        print("   Add --execute to create groups.")
        return

    print("🚀 EXECUTING...\n")
    asyncio.run(execute(groups, send_notice=args.notice))


if __name__ == "__main__":
    main()
