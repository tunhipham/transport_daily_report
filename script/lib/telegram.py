# -*- coding: utf-8 -*-
"""
Shared Telegram utilities for all domains.
Handles: load config, send photo/document, delete messages, track sent messages.
"""

import os
import json

# Use requests if available, fallback to urllib
try:
    import requests as _requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    _HAS_REQUESTS = False


def load_telegram_config(config_path, domain=None):
    """Load bot_token and chat_id from a JSON config file.
    Supports both flat format {"bot_token":..., "chat_id":...}
    and hierarchical format {"daily": {"bot_token":..., "chat_id":...}, ...}.
    If domain is specified, reads from that key in hierarchical config.
    Returns (bot_token, chat_id) tuple. Both None if file missing."""
    if not os.path.exists(config_path):
        print(f"  ⚠ Telegram config not found: {config_path}")
        return None, None
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Hierarchical format: {"daily": {...}, "inventory": {...}}
    if domain and domain in cfg:
        cfg = cfg[domain]
    # Flat format fallback: {"bot_token": ..., "chat_id": ...}
    return cfg.get("bot_token"), cfg.get("chat_id")


def send_telegram_photo(photo_path, caption, bot_token, chat_id, fallback_document=True):
    """Send a photo to Telegram chat.
    If fallback_document=True, retry as document when photo is too large.
    Returns message_id or None."""
    if not bot_token or not chat_id:
        print("  ⚠ Telegram not configured, skipping photo send")
        return None

    if _HAS_REQUESTS:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                resp = _requests.post(url, data={
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                }, files={"photo": f}, timeout=30, verify=False)
            result = resp.json()
            if result.get("ok"):
                mid = result["result"]["message_id"]
                print(f"  ✅ Telegram photo sent (msg_id={mid})")
                return mid

            # Fallback to sendDocument if photo dimensions too large
            if fallback_document and ("PHOTO_INVALID_DIMENSIONS" in resp.text or "PHOTO_SAVE_FILE_INVALID" in resp.text):
                print(f"  ⚠️ Ảnh quá lớn, chuyển sang sendDocument...")
                return send_telegram_document(photo_path, caption, bot_token, chat_id)

            print(f"  ❌ Telegram photo error: {result.get('description', resp.text[:100])}")
            return None
        except Exception as e:
            print(f"  ❌ Telegram photo exception: {e}")
            return None
    else:
        # urllib fallback (for nso which uses urllib)
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        try:
            import mimetypes
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            with open(photo_path, 'rb') as f:
                file_data = f.read()
            body = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{os.path.basename(photo_path)}"\r\n'
                f'Content-Type: {mimetypes.guess_type(photo_path)[0] or "image/png"}\r\n\r\n'
            ).encode('utf-8') + file_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
            req = urllib.request.Request(url, data=body)
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            if result.get("ok"):
                mid = result["result"]["message_id"]
                print(f"  ✅ Telegram photo sent (msg_id={mid})")
                return mid
            print(f"  ❌ Telegram photo error: {result.get('description')}")
            return None
        except Exception as e:
            print(f"  ❌ Telegram photo exception: {e}")
            return None


def send_telegram_document(file_path, caption, bot_token, chat_id):
    """Send a document to Telegram chat. Returns message_id or None."""
    if not bot_token or not chat_id:
        print("  ⚠ Telegram not configured, skipping document send")
        return None

    if _HAS_REQUESTS:
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        try:
            with open(file_path, "rb") as f:
                resp = _requests.post(url, data={
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                }, files={"document": f}, timeout=30, verify=False)
            result = resp.json()
            if result.get("ok"):
                mid = result["result"]["message_id"]
                print(f"  ✅ Telegram document sent: {os.path.basename(file_path)} (msg_id={mid})")
                return mid
            print(f"  ❌ Telegram document error: {result.get('description', resp.text[:100])}")
            return None
        except Exception as e:
            print(f"  ❌ Telegram document exception: {e}")
            return None
    else:
        # urllib fallback
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        try:
            import mimetypes
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            with open(file_path, 'rb') as f:
                file_data = f.read()
            body = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{os.path.basename(file_path)}"\r\n'
                f'Content-Type: {mimetypes.guess_type(file_path)[0] or "application/octet-stream"}\r\n\r\n'
            ).encode('utf-8') + file_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
            req = urllib.request.Request(url, data=body)
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            if result.get("ok"):
                mid = result["result"]["message_id"]
                print(f"  ✅ Telegram document sent: {os.path.basename(file_path)} (msg_id={mid})")
                return mid
            print(f"  ❌ Telegram document error: {result.get('description')}")
            return None
        except Exception as e:
            print(f"  ❌ Telegram document exception: {e}")
            return None


def delete_telegram_message(message_id, bot_token, chat_id):
    """Delete a single message from Telegram chat."""
    if not bot_token or not chat_id:
        return False

    if _HAS_REQUESTS:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"
            resp = _requests.post(url, data={
                "chat_id": chat_id, "message_id": message_id,
            }, timeout=10, verify=False)
            return resp.json().get("ok", False)
        except Exception:
            return False
    else:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id, "message_id": message_id,
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode('utf-8'))
            return result.get("ok", False)
        except Exception:
            return False


def send_telegram_text(text, bot_token, chat_id, parse_mode="HTML"):
    """Send a text message to Telegram chat. Returns message_id or None."""
    if not bot_token or not chat_id:
        print("  ⚠ Telegram not configured, skipping text send")
        return None

    if _HAS_REQUESTS:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            resp = _requests.post(url, data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }, timeout=30, verify=False)
            result = resp.json()
            if result.get("ok"):
                mid = result["result"]["message_id"]
                print(f"  ✅ Telegram text sent (msg_id={mid})")
                return mid
            print(f"  ❌ Telegram text error: {result.get('description', resp.text[:100])}")
            return None
        except Exception as e:
            print(f"  ❌ Telegram text exception: {e}")
            return None
    else:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            if result.get("ok"):
                mid = result["result"]["message_id"]
                print(f"  ✅ Telegram text sent (msg_id={mid})")
                return mid
            print(f"  ❌ Telegram text error: {result.get('description')}")
            return None
        except Exception as e:
            print(f"  ❌ Telegram text exception: {e}")
            return None


# ── Sent messages tracking (date-tag based, used by daily) ──

def load_sent_messages(sent_file):
    """Load sent messages dict from JSON file. Returns dict."""
    if os.path.exists(sent_file):
        with open(sent_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sent_messages(sent_file, data):
    """Save sent messages dict to JSON file."""
    os.makedirs(os.path.dirname(sent_file), exist_ok=True)
    with open(sent_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_messages_by_tag(sent_file, tag, bot_token, chat_id):
    """Delete previously sent Telegram messages for a given tag (e.g. date_tag).
    Updates the tracking file after deletion."""
    sent = load_sent_messages(sent_file)
    msg_ids = sent.get(tag, [])
    if not msg_ids:
        return
    print(f"  🗑️  Xóa {len(msg_ids)} tin nhắn cũ ({tag})...")
    deleted = 0
    for mid in msg_ids:
        if delete_telegram_message(mid, bot_token, chat_id):
            deleted += 1
    print(f"  ✅ Đã xóa {deleted}/{len(msg_ids)} tin nhắn cũ")
    sent.pop(tag, None)
    save_sent_messages(sent_file, sent)


def track_sent_message(sent_file, tag, message_id):
    """Append a message_id to the tracking file under the given tag."""
    sent = load_sent_messages(sent_file)
    if tag not in sent:
        sent[tag] = []
    sent[tag].append(message_id)
    save_sent_messages(sent_file, sent)
