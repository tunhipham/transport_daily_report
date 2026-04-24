# -*- coding: utf-8 -*-
"""
Telegram Mention Watcher — 24/7 Listener
Khi ai đó tag bạn trong group → gửi link tin nhắn về chat cá nhân.

Usage:
  python mention_watcher.py          (chạy listener)
  python mention_watcher.py --test   (gửi tin nhắn test về chat cá nhân)

Requires: pip install telethon requests
"""

import asyncio
import json
import logging
import os
import sys
import time

# ── Setup logging to file (critical for pythonw which has no console) ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
LOG_FILE = os.path.join(REPO_ROOT, "output", "mention_watcher.log")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("mention_watcher")

# Reconfigure stdout for Windows console (safe even under pythonw)
try:
    if sys.platform == "win32" and sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

sys.path.insert(0, os.path.join(REPO_ROOT, "script"))

CONFIG_FILE = os.path.join(REPO_ROOT, "config", "telegram_client.json")
TELEGRAM_CFG = os.path.join(REPO_ROOT, "config", "telegram.json")
SESSION_FILE = os.path.join(REPO_ROOT, "config", ".telethon_watcher")


def load_watcher_config():
    """Load mention_watcher config from telegram.json."""
    with open(TELEGRAM_CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    watcher = cfg.get("mention_watcher", {})
    bot_token = watcher.get("bot_token")
    notify_chat_id = watcher.get("notify_chat_id")
    if not bot_token or not notify_chat_id:
        log.error("Thiếu config mention_watcher trong telegram.json")
        sys.exit(1)
    return bot_token, notify_chat_id


def send_notification(text, bot_token, chat_id):
    """Send notification via Bot API (sync)."""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
            timeout=15,
            verify=False,
        )
        result = resp.json()
        if result.get("ok"):
            log.info(f"Notification sent (msg_id={result['result']['message_id']})")
            return True
        log.error(f"Bot API error: {result.get('description', '')[:100]}")
        return False
    except Exception as e:
        log.error(f"Notification exception: {e}")
        return False


def build_message_link(chat_id, message_id):
    """Build t.me deep link for a message in a group/supergroup."""
    cid = str(chat_id)
    if cid.startswith("-100"):
        cid = cid[4:]
    elif cid.startswith("-"):
        cid = cid[1:]
    return f"https://t.me/c/{cid}/{message_id}"


async def run_watcher():
    """Main event loop — listens for mentions 24/7."""
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        MessageEntityMention, MessageEntityMentionName,
        InputMessageEntityMentionName,
    )

    bot_token, notify_chat_id = load_watcher_config()

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        client_cfg = json.load(f)

    client = TelegramClient(SESSION_FILE, client_cfg["api_id"], client_cfg["api_hash"])
    await client.start(phone=client_cfg.get("phone"))

    me = await client.get_me()
    my_id = me.id
    my_username = (me.username or "").lower()
    log.info(f"Logged in: {me.first_name} (@{me.username or 'N/A'}) — ID: {my_id}")
    log.info(f"Listening for mentions across all groups...")
    log.info(f"Notifications → chat_id {notify_chat_id}")
    log.info(f"Log file: {LOG_FILE}")

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            msg = event.message

            # Only group messages, not our own
            if not event.is_group:
                return
            if msg.sender_id == my_id:
                return

            # --- Check mention ---
            is_mentioned = False

            # Method 1: Telethon built-in flag
            if msg.mentioned:
                is_mentioned = True

            # Method 2: Check entities
            if not is_mentioned and msg.entities:
                for ent in msg.entities:
                    if isinstance(ent, MessageEntityMention):
                        offset = ent.offset
                        length = ent.length
                        mention_text = (msg.raw_text or "")[offset:offset + length].lower()
                        if mention_text.lstrip("@") == my_username:
                            is_mentioned = True
                            break
                    elif isinstance(ent, (MessageEntityMentionName, InputMessageEntityMentionName)):
                        uid = getattr(ent, "user_id", None)
                        if uid == my_id:
                            is_mentioned = True
                            break

            if not is_mentioned:
                return

            # --- Build notification ---
            chat = await event.get_chat()
            chat_title = getattr(chat, "title", "Unknown group")
            chat_id = event.chat_id

            sender = await event.get_sender()
            sender_name = ""
            if sender:
                sender_name = getattr(sender, "first_name", "") or ""
                if getattr(sender, "last_name", ""):
                    sender_name += f" {sender.last_name}"

            preview = (msg.raw_text or "(media/sticker)")[:150]
            if len(msg.raw_text or "") > 150:
                preview += "…"

            link = build_message_link(chat_id, msg.id)

            log.info(f"🔔 Mentioned in [{chat_title}] by {sender_name}")

            notification = (
                f"🔔 <b>Bạn được tag trong</b>: {chat_title}\n"
                f"👤 <b>Từ</b>: {sender_name}\n"
                f"💬 {preview}\n"
                f'🔗 <a href="{link}">Xem tin nhắn</a>'
            )

            send_notification(notification, bot_token, notify_chat_id)

        except Exception as e:
            log.exception(f"Handler error: {e}")

    # Run forever
    await client.run_until_disconnected()


async def test_notify():
    """Send a test notification to verify config works."""
    bot_token, notify_chat_id = load_watcher_config()
    log.info(f"Sending test notification to chat_id {notify_chat_id}...")
    ok = send_notification(
        "🧪 <b>Test notification</b>\nMention watcher đang hoạt động! ✅",
        bot_token,
        notify_chat_id,
    )
    if ok:
        log.info("Test thành công!")
    else:
        log.error("Test thất bại — kiểm tra bot_token và notify_chat_id.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Telegram Mention Watcher — 24/7")
    parser.add_argument("--test", action="store_true", help="Gửi tin nhắn test")
    args = parser.parse_args()

    if args.test:
        asyncio.run(test_notify())
    else:
        # Auto-reconnect loop
        while True:
            try:
                log.info("Starting mention watcher...")
                asyncio.run(run_watcher())
            except KeyboardInterrupt:
                log.info("Mention watcher stopped by user.")
                break
            except Exception as e:
                log.exception(f"Watcher crashed: {e}")
                log.info("Restarting in 10 seconds...")
                time.sleep(10)


if __name__ == "__main__":
    main()
