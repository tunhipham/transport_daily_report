# -*- coding: utf-8 -*-
"""
fetch_nso_mail.py — Scan Haraworks inbox for NSO schedule updates
==================================================================
Opens Haraworks, finds "Fwd: Cập nhật NSO - 2026" email,
parses the table, cross-references DSST sheet, and updates nso_stores.json.

Usage:
    python script/domains/nso/fetch_nso_mail.py              # Full run
    python script/domains/nso/fetch_nso_mail.py --dry-run     # Parse only, no write
    python script/domains/nso/fetch_nso_mail.py --force       # Skip day-of-week check

Schedule: Monday + Tuesday at logon (Windows Task Scheduler)
"""
import os, sys, json, time, argparse, re
from datetime import datetime, date

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "script"))

from lib.sources import DSST_SHEET_URL, DSST_GID
from domains.nso.generate import JSON_STORES_PATH, load_stores, save_stores

HARAWORKS_INBOX = "https://ic.haraworks.vn/internal_mail/inbox"
MAIL_SUBJECT_PATTERN = "Cập nhật NSO"
MAIL_SENDER_NAME = "Lương Thị Hương Giang"

LOGIN_USER = "SC012433"
LOGIN_PASS = "@Ptn240400"


# ══════════════════════════════════════════════════════════════
#  SELENIUM SETUP (reuse Edge profile from inject_haraworks)
# ══════════════════════════════════════════════════════════════

def _kill_stale_drivers():
    """Kill leftover msedgedriver.exe from previous sessions."""
    import subprocess as _sp
    try:
        _sp.run(["taskkill", "/f", "/im", "msedgedriver.exe"],
                capture_output=True, text=True, timeout=5)
    except Exception:
        pass
    lock_path = os.path.join(os.path.expanduser("~"), ".edge_automail", "lockfile")
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except Exception:
            pass


def setup_driver():
    """Setup Edge WebDriver with shared AutoMail profile."""
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions

    _kill_stale_drivers()
    auto_profile_dir = os.path.join(os.path.expanduser("~"), ".edge_automail")
    os.makedirs(auto_profile_dir, exist_ok=True)

    options = EdgeOptions()
    options.page_load_strategy = 'eager'
    options.add_argument(f"--user-data-dir={auto_profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1600,900")
    options.add_argument("--log-level=3")

    try:
        driver = webdriver.Edge(options=options)
    except Exception as e:
        print(f"  ⚠ Edge failed ({e}), trying Chrome...")
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        chrome_options = ChromeOptions()
        chrome_options.page_load_strategy = 'eager'
        # Use Chrome Default profile (phamtunhi2k — has Google auth)
        chrome_user_data = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data")
        chrome_options.add_argument(f"--user-data-dir={chrome_user_data}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--remote-debugging-port=0")
        chrome_options.add_argument("--window-size=1600,900")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        driver = webdriver.Chrome(options=chrome_options)

    driver.implicitly_wait(10)
    driver.set_page_load_timeout(30)
    return driver


# ══════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════

def _is_logged_in(driver):
    url = driver.current_url
    source = driver.page_source
    return (
        "internal_mail" in url or
        "Hộp Thư Đến" in source or
        "Tạo Thư Mới" in source or
        "Kingfoodmart" in source
    )


def ensure_logged_in(driver):
    """Auto-login to Haraworks if needed."""
    from selenium.webdriver.common.by import By

    print("  🔑 Checking login...")
    try:
        driver.get(HARAWORKS_INBOX)
    except Exception:
        pass
    time.sleep(3)

    if _is_logged_in(driver):
        print("  ✅ Already logged in")
        return True

    print("  🔐 Logging in...")

    # Step 1: Dismiss
    try:
        dismissed = driver.execute_script("""
            var els = document.querySelectorAll('button, a, span, div[role="button"]');
            for (var i = 0; i < els.length; i++) {
                var text = (els[i].textContent || '').trim().toLowerCase();
                if (text === 'dismiss' || text === 'bỏ qua' || text === 'đóng') {
                    if (els[i].offsetParent !== null) { els[i].click(); return true; }
                }
            }
            return false;
        """)
        if dismissed:
            print("  ✅ Dismissed")
        time.sleep(2)
    except Exception:
        pass

    # Step 2: Sign in with password
    try:
        clicked = driver.execute_script("""
            var els = document.querySelectorAll('button, a, span, div[role="button"]');
            for (var i = 0; i < els.length; i++) {
                var text = (els[i].textContent || '').trim().toLowerCase();
                if (text.includes('sign in with password') || text.includes('đăng nhập bằng mật khẩu')) {
                    if (els[i].offsetParent !== null) { els[i].click(); return true; }
                }
            }
            return false;
        """)
        if clicked:
            print("  ✅ Sign in with password clicked")
        time.sleep(2)
    except Exception:
        pass

    # Step 3: Check if form already has credentials (pre-filled)
    # Try clicking submit directly first
    try:
        submit_clicked = driver.execute_script("""
            var submit = document.querySelector('button[type="submit"], input[type="submit"]');
            if (submit && submit.offsetParent !== null) {
                submit.click();
                return true;
            }
            return false;
        """)
        if submit_clicked:
            print("  ✅ Submit clicked (pre-filled credentials)")
            time.sleep(5)
            if _is_logged_in(driver):
                print("  ✅ Login successful!")
                return True
    except Exception:
        pass

    # Step 3b: Enter credentials if not pre-filled
    try:
        user_selectors = [
            "input[name='Username']", "input[name='username']", "input[name='email']",
            "input[type='email']", "input[type='text']"
        ]
        for sel in user_selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    el.clear()
                    el.send_keys(LOGIN_USER)
                    print(f"  ✅ Username entered")
                    break
            else:
                continue
            break

        els = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        for el in els:
            if el.is_displayed():
                el.clear()
                el.send_keys(LOGIN_PASS)
                print("  ✅ Password entered")
                break

        time.sleep(1)
        driver.execute_script("""
            var btn = document.querySelector('button[type="submit"]');
            if (btn) btn.click();
        """)
        time.sleep(5)
    except Exception as e:
        print(f"  ⚠ Credential entry error: {e}")

    # Verify
    for i in range(12):
        if _is_logged_in(driver):
            print("  ✅ Login successful!")
            return True
        time.sleep(5)

    print("  ❌ Login failed")
    return False


# ══════════════════════════════════════════════════════════════
#  FIND AND PARSE NSO MAIL
# ══════════════════════════════════════════════════════════════

def find_nso_mail(driver):
    """Find the NSO update email in inbox. Returns the mail URL or None."""
    from selenium.webdriver.common.by import By

    print(f"  🔍 Searching for '{MAIL_SUBJECT_PATTERN}'...")
    driver.get(HARAWORKS_INBOX)
    time.sleep(4)

    # Extract the detail URL from the inbox list
    detail_url = driver.execute_script("""
        var subject = arguments[0];
        // Search all links for the NSO email
        var links = document.querySelectorAll('a[href*="detail"]');
        for (var i = 0; i < links.length; i++) {
            var row = links[i].closest('tr') || links[i].parentElement;
            var text = (row ? row.textContent : links[i].textContent) || '';
            if (text.indexOf(subject) >= 0) {
                return links[i].href;
            }
        }
        // Fallback: search text nodes
        var all = document.querySelectorAll('td, div, span');
        for (var i = 0; i < all.length; i++) {
            var t = (all[i].textContent || '').trim();
            if (t.indexOf(subject) >= 0 && t.length < 500) {
                var el = all[i];
                for (var j = 0; j < 10; j++) {
                    if (!el.parentElement) break;
                    el = el.parentElement;
                    var link = el.querySelector('a[href*="detail"]');
                    if (link) return link.href;
                }
            }
        }
        return null;
    """, MAIL_SUBJECT_PATTERN)

    if not detail_url:
        # Fallback: click and wait for navigation
        print("  ⚠ No detail URL found, trying click...")
        clicked = driver.execute_script("""
            var subject = arguments[0];
            var all = document.querySelectorAll('td, div, span, b, strong');
            for (var i = 0; i < all.length; i++) {
                var t = (all[i].textContent || '').trim();
                if (t.indexOf(subject) >= 0 && t.length < 300) {
                    all[i].click();
                    return true;
                }
            }
            return false;
        """, MAIL_SUBJECT_PATTERN)
        if clicked:
            time.sleep(5)
            if "detail" in driver.current_url:
                detail_url = driver.current_url
                print(f"  ✅ Opened mail: {detail_url}")
                return detail_url
        print("  ❌ NSO mail not found")
        return None

    # Navigate directly to the detail page
    print(f"  📧 Found mail URL: {detail_url}")
    driver.get(detail_url)
    time.sleep(5)

    if "detail" in driver.current_url:
        print(f"  ✅ Opened mail detail")
        return detail_url

    print("  ⚠ URL didn't change to detail")
    return None


# State file for dedup
STATE_FILE = os.path.join(REPO_ROOT, "data", "nso", ".last_mail_url")

def _read_last_mail_url():
    """Read last processed mail URL from state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return None

def _save_last_mail_url(url):
    """Save processed mail URL to state file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write(url)


# No-mail warning counter (warn user if 3 consecutive scans find no new mail)
NO_MAIL_COUNTER = os.path.join(REPO_ROOT, "output", "state", "nso", ".no_mail_count")

def _read_no_mail_count():
    if os.path.exists(NO_MAIL_COUNTER):
        try:
            return int(open(NO_MAIL_COUNTER).read().strip())
        except Exception:
            return 0
    return 0

def _save_no_mail_count(n):
    os.makedirs(os.path.dirname(NO_MAIL_COUNTER), exist_ok=True)
    with open(NO_MAIL_COUNTER, "w") as f:
        f.write(str(n))

def _warn_no_mail(count):
    """Send Telegram warning to personal chat when no new mail after 3 scans."""
    try:
        import urllib.request
        cfg_path = os.path.join(REPO_ROOT, "config", "telegram.json")
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        bot_token = cfg["nso_remind"]["bot_token"]
        chat_id = cfg["nso_remind"]["chat_id"]
        msg = (f"⚠️ NSO Warning: Đã quét {count} lần liên tiếp "
               f"nhưng KHÔNG tìm thấy mail NSO mới!\n"
               f"Kiểm tra Haraworks inbox hoặc hỏi Hoàng Nguyên Công.")
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print(f"  ⚠️ Warning sent to personal chat (scan #{count})")
    except Exception as e:
        print(f"  ❌ Warning send failed: {e}")


def parse_nso_table(driver):
    """Parse NSO store list from the email body.

    Actual email format (plain text inside CKEditor):
        160. The Park Residence - Nguyễn Hữu Thọ
            Ngày nhận mặt bằng: 15/03/2026
            Ngày khai trương: 17/04/2026 - Thứ 6
    """
    print("  📋 Parsing NSO email...")

    # Wait for content to render
    time.sleep(3)

    # Extract innerText — try multiple selectors
    ck_text = driver.execute_script('''
        var selectors = [".ck-content", ".mail-body", ".card-body", ".mail-content"];
        var best = null;
        for (var i = 0; i < selectors.length; i++) {
            var els = document.querySelectorAll(selectors[i]);
            for (var j = 0; j < els.length; j++) {
                var t = els[j].innerText;
                if (t && (!best || t.length > best.length)) {
                    best = t;
                }
            }
        }
        return best;
    ''')

    if not ck_text:
        print("  ❌ No email content found")
        return []

    print(f"  📄 Email text: {len(ck_text)} chars")

    # ── Normalize text: fix broken dates (22\n/05/2026 → 22/05/2026) ──
    # Join lines that start with / back to previous line
    lines = ck_text.split('\n')
    fixed = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('/') and fixed:
            fixed[-1] = fixed[-1].rstrip() + stripped
        else:
            fixed.append(line)
    ck_text = '\n'.join(fixed)

    # Also fix "dd /mm/yyyy" patterns (spaces around /)
    ck_text = re.sub(r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})', r'\1/\2/\3', ck_text)

    # Parse store entries using regex
    stores = []
    entry_pattern = re.compile(r'(\d{1,3})\.\s+(.+?)(?=\n)')
    date_pattern = re.compile(r'Ngày khai trương:\s*([\d/]+)')

    # Split into blocks per store entry
    entries = re.split(r'\n(?=\d{1,3}\.\s)', ck_text)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        header_match = entry_pattern.match(entry)
        if not header_match:
            continue

        stt = header_match.group(1)
        name_mail = header_match.group(2).strip()

        # Clean name
        name_mail = re.sub(r'https?://\S+', '', name_mail).strip()
        name_mail = name_mail.rstrip(' -')
        # Remove trailing notes like "- dời ngày khai trương trễ"
        name_mail = re.sub(r'\s*-\s*dời.*$', '', name_mail, flags=re.IGNORECASE).strip()
        name_mail = re.sub(r'\s*-\s*mới bổ sung\s*$', '', name_mail, flags=re.IGNORECASE).strip()

        date_match = date_pattern.search(entry)
        if not date_match:
            continue

        # Clean spaces from date: "22 /0 5/2026" → "22/05/2026"
        raw_date = date_match.group(1)
        opening_date = re.sub(r'\s+', '', raw_date)

        stores.append({
            "stt": int(stt),
            "name_mail": name_mail,
            "opening_date": opening_date,
        })

    stores.sort(key=lambda s: s["stt"])

    print(f"  ✅ Parsed {len(stores)} stores from mail")
    for s in stores[:5]:
        print(f"     #{s['stt']} | {s['name_mail'][:50]} | {s['opening_date']}")
    if len(stores) > 5:
        print(f"     ... +{len(stores) - 5} more")

    return stores


def read_dsst():
    """Read DSST store data from local cache.

    Cache file: data/dsst_cache.json (refreshed by _save_dsst.py)
    Returns dict: code -> {name_system, name_full, branch_name, version}
    """
    cache_path = os.path.join(REPO_ROOT, "data", "dsst_cache.json")
    print("  📖 Reading DSST cache...")

    if not os.path.exists(cache_path):
        print(f"  ⚠ DSST cache not found: {cache_path}")
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            lookup = json.load(f)
        print(f"  ✅ DSST lookup: {len(lookup)} stores")
        return lookup
    except Exception as e:
        print(f"  ⚠ DSST cache read failed: {e}")
        return {}


# ══════════════════════════════════════════════════════════════
#  MERGE LOGIC
# ══════════════════════════════════════════════════════════════

def _normalize(s):
    """Normalize store name for fuzzy matching."""
    s = s.lower().strip()
    # Remove common noise
    for noise in ['- mới bổ sung', '- tbi', '- bth', '- q1', 'shophoue', 'shophouse']:
        s = s.replace(noise, '')
    return ' '.join(s.split())


def _name_match(name_mail, store):
    """Check if a mail store name matches an existing store entry."""
    nm = _normalize(name_mail)
    # Check against name_mail, name_full, name_system
    for key in ['name_mail', 'name_full']:
        sv = store.get(key)
        if sv:
            sv_n = _normalize(sv)
            # Substring match (either direction)
            if nm in sv_n or sv_n in nm:
                return True
            # First significant word match
            nm_words = [w for w in nm.split() if len(w) > 2]
            sv_words = [w for w in sv_n.split() if len(w) > 2]
            common = set(nm_words) & set(sv_words)
            if len(common) >= 2:
                return True
    return False


def merge_stores(current_stores, mail_stores, dsst_lookup):
    """Merge mail data into current stores list.

    Mail stores have: stt, name_mail, opening_date (no code!)
    Current stores have: code, name_system, name_full, name_mail, opening_date, version

    Match by name (fuzzy). New stores added without code (will be filled by DSST later).
    """
    added = []
    updated = []

    for ms in mail_stores:
        # Find matching existing store by name
        matched = None
        for cs in current_stores:
            if _name_match(ms["name_mail"], cs):
                matched = cs
                break

        if matched:
            # Check if opening_date changed
            if matched["opening_date"] != ms["opening_date"]:
                old_date = matched.get("original_date") or matched["opening_date"]
                matched["original_date"] = old_date
                matched["opening_date"] = ms["opening_date"]
                updated.append(matched.get("code") or ms["name_mail"][:20])
        else:
            # New store — no code yet
            new_store = {
                "code": None,
                "name_system": None,
                "name_full": ms["name_mail"],
                "name_mail": ms["name_mail"],
                "opening_date": ms["opening_date"],
                "version": None,
                "original_date": None,
            }
            current_stores.append(new_store)
            added.append(ms["name_mail"][:25])

    # Enrich with DSST data — fuzzy match name → code + version
    for store in current_stores:
        code = store.get("code")

        # If already has code, just fill missing fields
        if code:
            dsst = dsst_lookup.get(code, {})
            if dsst.get("name_system") and not store.get("name_system"):
                store["name_system"] = dsst["name_system"]
            if dsst.get("version") and not store.get("version"):
                store["version"] = dsst["version"]
            continue

        # No code — fuzzy match mail name against DSST branch_name
        mail_name = (store.get("name_mail") or store.get("name_full") or "").lower()
        if not mail_name:
            continue

        # Split into keywords (>2 chars, skip noise)
        noise = {"chung", "cư", "siêu", "thị", "mới", "bổ", "sung", "kfm", "hcm"}
        keywords = [w for w in re.split(r'[\s\-/,\.]+', mail_name) if len(w) > 1 and w not in noise]

        best_match = None
        best_score = 0

        for dsst_code, dsst_info in dsst_lookup.items():
            dsst_name = (dsst_info.get("branch_name") or dsst_info.get("name_full") or "").lower()
            if not dsst_name:
                continue
            # Count how many keywords match
            score = sum(1 for kw in keywords if kw in dsst_name)
            if score > best_score and score >= 2:
                best_score = score
                best_match = (dsst_code, dsst_info)

        if best_match:
            dsst_code, dsst_info = best_match
            store["code"] = dsst_code
            store["name_system"] = dsst_info.get("name_system")
            if not store.get("name_full"):
                store["name_full"] = dsst_info.get("name_full")
            store["version"] = dsst_info.get("version")

    return current_stores, added, updated


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="NSO Mail Scanner — Haraworks")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't write")
    parser.add_argument("--force", action="store_true", help="Skip dedup check")
    parser.add_argument("--no-deploy", action="store_true",
                        help="Skip deploy step (for tracking runs)")
    args = parser.parse_args()

    now = datetime.now()
    print(f"\n{'='*55}")
    print(f"  🏪 NSO Mail Scanner — {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}")

    # Reset upstream flags (prevent stale values from previous runs)
    _state_dir = os.path.join(REPO_ROOT, "output", "state", "nso")
    os.makedirs(_state_dir, exist_ok=True)
    for _fname in [".has_changes", ".mail_processed"]:
        with open(os.path.join(_state_dir, _fname), "w") as f:
            f.write("0")

    # Read DSST cache (no browser needed)
    dsst_lookup = read_dsst()

    # Load master
    from nso_master import NsoMaster
    master = NsoMaster()
    master.load()
    print(f"  📊 Master: {len(master.stores)} stores")

    driver = None
    try:
        # Setup browser
        print("\n  🌐 Starting browser...")
        driver = setup_driver()

        # Login to Haraworks
        if not ensure_logged_in(driver):
            print("  ❌ Cannot login to Haraworks")
            return

        # Find NSO mail
        mail_url = find_nso_mail(driver)
        if not mail_url:
            count = _read_no_mail_count() + 1
            _save_no_mail_count(count)
            print(f"  ❌ Cannot find NSO mail (miss #{count}/3)")
            if count >= 3:
                _warn_no_mail(count)
            return

        # Dedup: skip if same mail already processed
        last_url = _read_last_mail_url()
        if last_url == mail_url and not args.force:
            count = _read_no_mail_count() + 1
            _save_no_mail_count(count)
            print(f"  ⏭ Mail already processed (miss #{count}/3): {mail_url.split('/')[-1][:12]}...")
            print(f"  💡 Use --force to re-process")
            if count >= 3:
                _warn_no_mail(count)
            return

        # Parse table
        mail_stores = parse_nso_table(driver)
        if not mail_stores:
            print("  ❌ No stores parsed from mail")
            return

        print(f"\n  📧 Mail stores: {len(mail_stores)}")
        print(f"  📖 DSST lookup: {len(dsst_lookup)}")

        # Merge via master (with history tracking)
        summary, added, updated = master.merge_mail(mail_stores, dsst_lookup)

        print(f"\n  {'─'*40}")
        print(f"  📊 Merge result:")
        print(f"     Total: {len(master.stores)}")
        print(f"     New:   {len(added)} {added[:5] if added else ''}")
        print(f"     Updated dates: {len(updated)} {updated[:5] if updated else ''}")
        print(f"     History entries: {len(master.history)}")

        has_changes = len(added) > 0 or len(updated) > 0

        if args.dry_run:
            print(f"\n  🏃 DRY RUN — not writing files")
            return has_changes

        # Save master + output
        master.save()
        master.save_output(scan_summary=summary)

        # Mark mail as processed
        _save_last_mail_url(mail_url)
        print(f"  📌 Saved state: {mail_url.split('/')[-1][:12]}...")

        if args.no_deploy:
            if has_changes:
                print(f"\n  ⚠ Changes detected but --no-deploy set, skipping deploy")
            else:
                print(f"\n  ℹ No changes, skipping deploy")
        else:
            # Re-export + deploy
            import subprocess
            print(f"\n  📦 Re-exporting NSO data...")
            subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "script", "dashboard", "export_data.py"),
                 "--domain", "nso"],
                cwd=REPO_ROOT, timeout=60
            )

            print(f"  🚀 Deploying...")
            subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "script", "dashboard", "deploy.py"),
                 "--domain", "nso"],
                cwd=REPO_ROOT, timeout=120
            )

        # Write flags for upstream scripts (bat file)
        _state_dir = os.path.join(REPO_ROOT, "output", "state", "nso")
        with open(os.path.join(_state_dir, ".has_changes"), "w") as f:
            f.write("1" if has_changes else "0")
        with open(os.path.join(_state_dir, ".mail_processed"), "w") as f:
            f.write("1")

        # Reset no-mail counter (new mail found successfully)
        _save_no_mail_count(0)

    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        # ── Pipeline summary ──
        steps = ["scan mail"]
        if not args.dry_run:
            steps.append("merge → nso_stores.json")
        if not args.no_deploy and not args.dry_run:
            steps.append("export nso.json → deploy")
        else:
            steps.append("(no deploy)")
        print(f"\n  ✅ Pipeline complete: {' → '.join(steps)}")
        print(f"{'='*55}\n")


if __name__ == "__main__":
    main()

