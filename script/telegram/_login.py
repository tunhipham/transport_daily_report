"""
One-time Telethon login script.
Sends OTP code via command-line argument to avoid interactive stdin issues.

Usage:
  Step 1: python _login.py --send       (sends OTP to your phone)
  Step 2: python _login.py --code 12345  (enters the OTP code)
"""
import asyncio
import json
import os
import sys
import argparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "telegram_client.json")
SESSION_FILE = os.path.join(REPO_ROOT, "config", ".telethon_session")


async def send_code():
    from telethon import TelegramClient
    
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    
    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Đã đăng nhập rồi: {me.first_name} (@{me.username or 'N/A'})")
        await client.disconnect()
        return
    
    phone = config.get("phone")
    if not phone:
        print("❌ Chưa có phone trong config. Thêm 'phone' vào telegram_client.json")
        await client.disconnect()
        return
    print(f"📱 Sending OTP to {phone}...")
    
    result = await client.send_code_request(phone)
    
    # Save phone_code_hash for step 2
    config["_phone_code_hash"] = result.phone_code_hash
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ OTP sent! Check Telegram app on your phone.")
    print(f"   Then run: python _login.py --code XXXXX")
    await client.disconnect()


async def sign_in(code):
    from telethon import TelegramClient
    
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    
    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Đã đăng nhập rồi: {me.first_name} (@{me.username or 'N/A'})")
        await client.disconnect()
        return
    
    phone = config.get("phone")
    if not phone:
        print("❌ Chưa có phone trong config.")
        await client.disconnect()
        return
    phone_code_hash = config.get("_phone_code_hash", "")
    
    if not phone_code_hash:
        print("❌ Chưa gửi OTP. Chạy: python _login.py --send")
        await client.disconnect()
        return
    
    print(f"🔑 Signing in with code: {code}")
    
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        print(f"✅ Đăng nhập thành công: {me.first_name} (@{me.username or 'N/A'})")
        
        # Clean up temp hash
        config.pop("_phone_code_hash", None)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    
    except Exception as e:
        err_str = str(e)
        if "Two-steps verification" in err_str or "SessionPasswordNeeded" in err_str:
            print(f"🔐 Account bật 2FA — cần cloud password.")
            print(f"   Chạy: python _login.py --password YOUR_PASSWORD")
        else:
            print(f"❌ Lỗi đăng nhập: {e}")
    
    await client.disconnect()


async def sign_in_password(password):
    """Sign in with 2FA cloud password (after OTP step)."""
    from telethon import TelegramClient
    
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    
    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Đã đăng nhập rồi: {me.first_name} (@{me.username or 'N/A'})")
        await client.disconnect()
        return
    
    print(f"🔐 Signing in with 2FA password...")
    
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        print(f"✅ Đăng nhập thành công: {me.first_name} (@{me.username or 'N/A'})")
        
        # Clean up temp hash
        config.pop("_phone_code_hash", None)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
            
    except Exception as e:
        print(f"❌ Lỗi đăng nhập 2FA: {e}")
    
    await client.disconnect()


async def check_status():
    from telethon import TelegramClient
    
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    
    client = TelegramClient(SESSION_FILE, config["api_id"], config["api_hash"])
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Đã đăng nhập: {me.first_name} (@{me.username or 'N/A'})")
    else:
        print("❌ Chưa đăng nhập. Chạy: python _login.py --send")
    
    await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Telethon Login Helper")
    parser.add_argument("--send", action="store_true", help="Send OTP code")
    parser.add_argument("--code", type=str, help="Enter OTP code")
    parser.add_argument("--password", type=str, help="Enter 2FA cloud password")
    parser.add_argument("--status", action="store_true", help="Check login status")
    args = parser.parse_args()
    
    if args.send:
        asyncio.run(send_code())
    elif args.code:
        asyncio.run(sign_in(args.code))
    elif args.password:
        asyncio.run(sign_in_password(args.password))
    elif args.status:
        asyncio.run(check_status())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
