"""
inject_haraworks.py - Selenium automation: paste composed mail into Haraworks CKEditor

Opens Haraworks internal mail, finds or creates the right email thread,
pastes HTML content into CKEditor, and saves as draft.
NEVER clicks Send.

Usage:
  python script/inject_haraworks.py --kho "ĐÔNG MÁT" --date 07/04/2026 --week W15
  python script/inject_haraworks.py --kho DRY --session sang --date 07/04/2026 --week W15
  python script/inject_haraworks.py --kho DRY --session toi --date 06/04/2026 --week W15

Requires: selenium, Chrome/Edge browser
"""
import os, sys, json, time, argparse, re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT = os.path.join(BASE, "output")

HARAWORKS_URL = "https://ic.haraworks.vn/internal_mail"
HARAWORKS_INBOX = f"{HARAWORKS_URL}/inbox"
HARAWORKS_CREATE = f"{HARAWORKS_URL}/create"
HARAWORKS_SENT = f"{HARAWORKS_URL}/sent"

# ── Mail metadata per kho ──
MAIL_CONFIG = {
    "KRC": {
        "subject_tpl": "KẾ HOẠCH GIAO HÀNG KRC {week}",
        "to": [],  # user adds manually or from thread
        "is_reply_thread": False,  # first mail of week = new thread; subsequent = reply
    },
    "DRY_sang": {
        "subject_tpl": "KẾ HOẠCH GIAO HÀNG KHO DRY {week}",
        "to": [],
        "is_reply_thread": False,  # first DRY mail of week = new; DRY Tối = reply
    },
    "DRY_toi": {
        "subject_tpl": "KẾ HOẠCH GIAO HÀNG KHO DRY {week}",
        "to": [],
        "is_reply_thread": True,  # always reply into DRY thread
    },
    "ĐÔNG MÁT": {
        "subject_tpl": "KẾ HOẠCH GIAO HÀNG KHO ĐÔNG MÁT {week}",
        "to": [],
        "is_reply_thread": False,
    },
    "THỊT CÁ": {
        "subject_tpl": "KẾ HOẠCH GIAO HÀNG KHO ABA THỊT CÁ {week}",
        "to": [],
        "is_reply_thread": False,
    },
}


def get_mail_key(kho, session):
    """Get config key for kho/session combo."""
    if kho == "DRY" and session:
        return f"DRY_{session}"
    return kho


def get_html_body_path(kho, session):
    """Get path to the composed HTML body file.
    
    ALWAYS prefers kho-specific file to prevent cross-kho contamination.
    Generic file is only used as fallback when kho-specific doesn't exist
    (e.g. compose_mail was run manually without --kho).
    """
    suffix = f"_{kho}"
    if session:
        suffix += f"_{session}"
    MAIL_DIR = os.path.join(OUTPUT, "mail")
    kho_path = os.path.join(MAIL_DIR, f"_mail{suffix}_body.html")
    generic_path = os.path.join(MAIL_DIR, "_mail_body.html")

    if os.path.exists(kho_path):
        return kho_path
    elif os.path.exists(generic_path):
        print(f"  ⚠ Kho-specific file not found, using generic _mail_body.html")
        return generic_path
    else:
        print(f"  ❌ No HTML body found for {kho}")
        return generic_path


def get_clip_ps1_path(kho, session):
    """Get path to the PowerShell clipboard script."""
    suffix = f"_{kho}"
    if session:
        suffix += f"_{session}"
    MAIL_DIR = os.path.join(OUTPUT, "mail")
    path = os.path.join(MAIL_DIR, f"_clip{suffix}_html.ps1")
    if os.path.exists(path):
        return path
    return os.path.join(MAIL_DIR, "_clip_html.ps1")


def _kill_stale_drivers():
    """Kill leftover msedgedriver.exe from previous interrupted sessions.
    Prevents profile lock conflicts when resuming after interruption.
    """
    import subprocess as _sp
    try:
        # Only kill msedgedriver (the Selenium-managed process), not user's Edge
        result = _sp.run(
            ["taskkill", "/f", "/im", "msedgedriver.exe"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("  🧹 Killed stale msedgedriver.exe")
            time.sleep(1)
    except Exception:
        pass
    # Also clean up lockfile if present
    lock_path = os.path.join(os.path.expanduser("~"), ".edge_automail", "lockfile")
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
            print("  🧹 Removed stale lockfile")
        except Exception:
            pass


def setup_driver():
    """Setup Selenium WebDriver with Edge (Chromium).
    Uses a SEPARATE profile directory ('AutoMail') to avoid conflicts
    with the user's existing Edge session.
    """
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions

    # Clean up stale processes from previous interrupted sessions
    _kill_stale_drivers()

    # Use LOCAL disk for browser profile — Google Drive streaming FS causes Edge to hang
    auto_profile_dir = os.path.join(os.path.expanduser("~"), ".edge_automail")
    os.makedirs(auto_profile_dir, exist_ok=True)

    options = EdgeOptions()
    options.page_load_strategy = 'eager'  # Don't wait for full page load (prevents SSO redirect hanging)
    options.add_argument(f"--user-data-dir={auto_profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1400,900")
    # Suppress DevTools logging
    options.add_argument("--log-level=3")

    try:
        driver = webdriver.Edge(options=options)
    except Exception as e:
        print(f"  ⚠ Edge failed ({e}), trying Chrome...")
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        chrome_options = ChromeOptions()
        chrome_options.page_load_strategy = 'eager'
        chrome_auto_dir = os.path.join(BASE, ".chrome_automail")
        os.makedirs(chrome_auto_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={chrome_auto_dir}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1400,900")
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=chrome_options)

    driver.implicitly_wait(10)
    driver.set_page_load_timeout(20)  # Prevent hanging on SSO redirects
    return driver


def ensure_logged_in(driver):
    """Check if logged into Haraworks. If not, auto-login via SSO.
    
    Login flow (Haravan SSO):
    1. Navigate to Haraworks → redirects to SSO if not logged in
    2. Click "Dismiss" on first screen (e.g. cookie/notification banner)
    3. Click "Sign in with password" 
    4. Enter username (SC012433) and password
    5. Click login button
    6. Session is saved in .edge_automail/ profile for future runs
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    print(f"  🔑 Checking login status...")
    try:
        driver.get(HARAWORKS_INBOX)
    except Exception as nav_err:
        # Page load timeout on SSO redirect is expected
        print(f"  ⚠ Page load timeout (SSO redirect): {type(nav_err).__name__}")
    time.sleep(3)
    
    # Check if already logged in
    if _is_logged_in(driver):
        print(f"  ✅ Already logged in")
        return True
    
    # Not logged in → attempt auto-login
    print(f"  🔐 Not logged in. Attempting auto-login...")
    
    try:
        return _auto_login(driver)
    except Exception as e:
        print(f"  ⚠ Auto-login error: {e}")
        print(f"  🔄 Falling back to manual login...")
        return _wait_manual_login(driver)


def _auto_login(driver):
    """Perform automated login through Haravan SSO."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    LOGIN_USER = "SC012433"
    LOGIN_PASS = "@Ptn240400"
    
    # ── Step 1: Click "Dismiss" on the first screen ──
    print(f"  📌 Step 1: Looking for Dismiss button...")
    try:
        dismiss_clicked = False
        # Try multiple selectors for dismiss/close buttons
        dismiss_selectors = [
            "//button[contains(text(), 'Dismiss')]",
            "//a[contains(text(), 'Dismiss')]",
            "//button[contains(text(), 'dismiss')]",
            "//span[contains(text(), 'Dismiss')]/..",
            "//button[contains(@class, 'dismiss')]",
            "//button[contains(text(), 'Bỏ qua')]",
            "//button[contains(text(), 'Đóng')]",
            "//button[contains(text(), 'Close')]",
        ]
        for xpath in dismiss_selectors:
            try:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        btn.click()
                        dismiss_clicked = True
                        print(f"  ✅ Dismissed (xpath)")
                        break
            except Exception:
                continue
            if dismiss_clicked:
                break
        
        if not dismiss_clicked:
            # Try JS approach — find any button/link with "Dismiss" text
            dismissed = driver.execute_script("""
                var els = document.querySelectorAll('button, a, span, div[role="button"]');
                for (var i = 0; i < els.length; i++) {
                    var text = (els[i].textContent || '').trim().toLowerCase();
                    if (text === 'dismiss' || text === 'bỏ qua' || text === 'đóng' || text === 'close') {
                        if (els[i].offsetParent !== null) {
                            els[i].click();
                            return true;
                        }
                    }
                }
                return false;
            """)
            if dismissed:
                dismiss_clicked = True
                print(f"  ✅ Dismissed (JS)")
        
        if not dismiss_clicked:
            print(f"  ⏩ No dismiss button found, continuing anyway...")
        
        time.sleep(2)
    except Exception as e:
        print(f"  ⏩ Dismiss step skipped: {e}")
        time.sleep(1)
    
    # ── Step 2: Click "Sign in with password" ──
    print(f"  📌 Step 2: Looking for 'Sign in with password'...")
    try:
        pw_clicked = False
        pw_selectors = [
            "//button[contains(text(), 'Sign in with password')]",
            "//a[contains(text(), 'Sign in with password')]",
            "//span[contains(text(), 'Sign in with password')]/..",
            "//button[contains(text(), 'sign in with password')]",
            "//a[contains(text(), 'sign in with password')]",
            "//button[contains(text(), 'Đăng nhập bằng mật khẩu')]",
            "//a[contains(text(), 'Đăng nhập bằng mật khẩu')]",
            "//button[contains(text(), 'password')]",
            "//a[contains(text(), 'password')]",
        ]
        for xpath in pw_selectors:
            try:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        btn.click()
                        pw_clicked = True
                        print(f"  ✅ 'Sign in with password' clicked")
                        break
            except Exception:
                continue
            if pw_clicked:
                break
        
        if not pw_clicked:
            pw_clicked = driver.execute_script("""
                var els = document.querySelectorAll('button, a, span, div[role="button"]');
                for (var i = 0; i < els.length; i++) {
                    var text = (els[i].textContent || '').trim().toLowerCase();
                    if (text.includes('sign in with password') || text.includes('đăng nhập bằng mật khẩu')) {
                        if (els[i].offsetParent !== null) {
                            els[i].click();
                            return true;
                        }
                    }
                }
                return false;
            """)
            if pw_clicked:
                print(f"  ✅ 'Sign in with password' clicked (JS)")
        
        if not pw_clicked:
            print(f"  ⚠ 'Sign in with password' button not found")
        
        time.sleep(2)
    except Exception as e:
        print(f"  ⚠ Step 2 error: {e}")
        time.sleep(1)
    
    # ── Step 3: Enter credentials ──
    print(f"  📌 Step 3: Entering credentials...")
    try:
        # Find username/email input
        username_input = None
        user_selectors = [
            "input[name='Username']",
            "input[name='username']",
            "input[name='email']",
            "input[name='account']",
            "input[name='login']",
            "input[type='email']",
            "input[type='text'][name*='user']",
            "input[type='text'][name*='email']",
            "input[type='text'][name*='account']",
            "input[id*='user']",
            "input[id*='email']",
            "input[id*='account']",
            "input[placeholder*='email']",
            "input[placeholder*='username']",
            "input[placeholder*='tài khoản']",
            "input[placeholder*='Tài khoản']",
            "input[placeholder*='Nhập email']",
        ]
        for sel in user_selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        username_input = el
                        break
            except Exception:
                continue
            if username_input:
                break
        
        if not username_input:
            # Fallback: first visible text/email input
            for input_type in ['email', 'text']:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, f"input[type='{input_type}']")
                    for el in els:
                        if el.is_displayed():
                            username_input = el
                            break
                except Exception:
                    continue
                if username_input:
                    break
        
        if username_input:
            username_input.clear()
            username_input.send_keys(LOGIN_USER)
            print(f"  ✅ Username entered: {LOGIN_USER}")
        else:
            print(f"  ❌ Username input not found")
            return _wait_manual_login(driver)
        
        # Find password input
        password_input = None
        try:
            els = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            for el in els:
                if el.is_displayed():
                    password_input = el
                    break
        except Exception:
            pass
        
        if not password_input:
            # Maybe password field appears after entering username
            time.sleep(1)
            try:
                els = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                for el in els:
                    if el.is_displayed():
                        password_input = el
                        break
            except Exception:
                pass
        
        if password_input:
            password_input.clear()
            password_input.send_keys(LOGIN_PASS)
            print(f"  ✅ Password entered")
        else:
            print(f"  ❌ Password input not found")
            return _wait_manual_login(driver)
        
        time.sleep(1)
    except Exception as e:
        print(f"  ❌ Credential entry error: {e}")
        return _wait_manual_login(driver)
    
    # ── Step 4: Click login button ──
    print(f"  📌 Step 4: Clicking login button...")
    try:
        login_clicked = False
        login_selectors = [
            "//button[@type='submit']",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'Đăng nhập')]",
            "//button[contains(text(), 'đăng nhập')]",
            "//button[contains(text(), 'Sign in')]",
            "//button[contains(text(), 'sign in')]",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'login')]",
            "//button[contains(text(), 'Log in')]",
            "//input[@type='submit']",
            "//a[contains(text(), 'Đăng nhập')]",
        ]
        for xpath in login_selectors:
            try:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        btn.click()
                        login_clicked = True
                        print(f"  ✅ Login button clicked")
                        break
            except Exception:
                continue
            if login_clicked:
                break
        
        if not login_clicked:
            # Try Enter key as fallback
            from selenium.webdriver.common.keys import Keys
            password_input.send_keys(Keys.RETURN)
            login_clicked = True
            print(f"  ✅ Login submitted via Enter key")
        
        time.sleep(5)
    except Exception as e:
        print(f"  ⚠ Login button error: {e}")
        time.sleep(3)
    
    # ── Step 5: Verify login success ──
    print(f"  🔍 Verifying login...")
    for i in range(12):  # 12 × 5s = 60s timeout
        try:
            if _is_logged_in(driver):
                print(f"  ✅ Auto-login successful!")
                return True
        except Exception:
            pass
        time.sleep(5)
        if (i + 1) % 4 == 0:
            print(f"  ⏳ Waiting for redirect... ({(i+1)*5}s)")
    
    print(f"  ⚠ Auto-login may have failed — checking one more time...")
    driver.get(HARAWORKS_INBOX)
    time.sleep(4)
    if _is_logged_in(driver):
        print(f"  ✅ Login confirmed after redirect!")
        return True
    
    print(f"  ❌ Auto-login failed. Falling back to manual login.")
    return _wait_manual_login(driver)


def _wait_manual_login(driver):
    """Fallback: wait for user to login manually."""
    print(f"  🔐 Please login manually in the automation browser window")
    print(f"  💡 Session will be saved → future runs won't need login")
    print(f"  ⏳ Waiting for login (checking every 5s, timeout 5 min)...")
    
    for i in range(60):  # 60 × 5s = 5 min timeout
        time.sleep(5)
        try:
            if _is_logged_in(driver):
                print(f"  ✅ Login detected! Continuing...")
                return True
        except Exception:
            pass
        if (i + 1) % 12 == 0:  # Every 60s
            print(f"  ⏳ Still waiting for login... ({(i+1)*5}s)")
    
    print(f"  ❌ Login timeout (5 min). Please try again.")
    return False


def _is_logged_in(driver):
    """Check if currently on Haraworks internal mail (logged in)."""
    url = driver.current_url
    source = driver.page_source
    return (
        "internal_mail" in url or 
        "Hộp Thư Đến" in source or 
        "Tạo Thư Mới" in source or
        "Kingfoodmart" in source
    )


def find_existing_thread(driver, subject_prefix):
    """Search Sent then Inbox for existing thread with matching subject.
    Returns thread URL or None.

    Strategy: Sent first (we sent the thread), JS textContent search
    (handles Vietnamese diacritics better than XPath), then XPath fallback.
    """
    from selenium.webdriver.common.by import By

    print(f"  🔍 Searching for thread: {subject_prefix}...")

    # Search Sent first (we sent original → guaranteed in Sent folder)
    for folder_name, folder_url in [("Sent", HARAWORKS_SENT), ("Inbox", HARAWORKS_INBOX)]:
        try:
            driver.get(folder_url)
            time.sleep(5)  # Longer wait for full page load

            # Strategy 1: JavaScript textContent search (robust for Vietnamese)
            thread_found = driver.execute_script("""
                var subject = arguments[0];
                // Try structured mail item selectors first
                var candidates = document.querySelectorAll(
                    'tr, a, [class*="mail"], [class*="item"], [class*="row"], [class*="list"] > *'
                );
                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el.textContent && el.textContent.includes(subject)) {
                        var clickTarget = el;
                        // Prefer inner <a> if exists
                        var innerLink = el.querySelector('a');
                        if (innerLink && innerLink.textContent.includes(subject)) {
                            clickTarget = innerLink;
                        }
                        clickTarget.click();
                        return 'structured';
                    }
                }
                // Fallback: search leaf-ish elements
                var all = document.querySelectorAll('b, strong, span, a, td, div, p');
                for (var i = 0; i < all.length; i++) {
                    var el = all[i];
                    var text = el.textContent || '';
                    if (text.includes(subject) && text.length < 500) {
                        // Navigate up to clickable parent
                        var target = el;
                        for (var j = 0; j < 8; j++) {
                            var p = target.parentElement;
                            if (!p) break;
                            var tag = p.tagName.toLowerCase();
                            var cls = (p.className || '').toLowerCase();
                            if (tag === 'tr' || tag === 'a' || tag === 'li' ||
                                cls.includes('mail') || cls.includes('item') || cls.includes('row')) {
                                target = p;
                                break;
                            }
                            target = p;
                        }
                        target.click();
                        return 'fallback';
                    }
                }
                return null;
            """, subject_prefix)

            if thread_found:
                time.sleep(4)
                thread_url = driver.current_url
                if thread_url != folder_url and "internal_mail" in thread_url:
                    print(f"  ✅ Found thread in {folder_name} ({thread_found}): {thread_url}")
                    return thread_url
                else:
                    print(f"  ⚠ Clicked in {folder_name} but URL didn't change, trying next...")

            # Strategy 2: XPath with multiple tag selectors (fallback)
            for tag in ['b', 'strong', 'span', 'a', 'td', 'div']:
                try:
                    matches = driver.find_elements(By.XPATH,
                        f"//{tag}[contains(text(), '{subject_prefix}')]")
                    for match in matches:
                        try:
                            clickable = match
                            for _ in range(8):
                                parent = clickable.find_element(By.XPATH, "..")
                                ptag = parent.tag_name.lower()
                                cls = parent.get_attribute('class') or ''
                                if ptag in ('tr', 'a', 'li') or \
                                   any(k in cls for k in ['mail', 'item', 'row']):
                                    clickable = parent
                                    break
                                clickable = parent
                            clickable.click()
                            time.sleep(4)
                            thread_url = driver.current_url
                            if thread_url != folder_url and "internal_mail" in thread_url:
                                print(f"  ✅ Found thread in {folder_name} (xpath/{tag}): {thread_url}")
                                return thread_url
                        except Exception:
                            continue
                except Exception:
                    continue

        except Exception as e:
            print(f"  ⚠ {folder_name} search error: {e}")

    print(f"  📝 No existing thread found")
    return None


def open_compose_new(driver):
    """Navigate to compose new mail page."""
    print(f"  📝 Opening compose new mail...")
    driver.get(HARAWORKS_CREATE)
    time.sleep(3)
    return True


def open_reply_in_thread(driver, thread_url):
    """Open thread and click Reply All. Handles icon-only buttons.
    
    Haraworks thread detail has reply/reply-all/forward icons at the top-right.
    Must be careful NOT to click sidebar navigation icons (calendar, mail, etc.)
    """
    from selenium.webdriver.common.by import By

    print(f"  ↩ Opening thread for reply...")
    driver.get(thread_url)
    time.sleep(5)  # Longer wait for thread to fully load

    original_url = driver.current_url

    def _verify_still_on_thread():
        """Check we didn't navigate away after clicking."""
        time.sleep(3)
        cur = driver.current_url
        if cur != original_url and "detail" not in cur and "create" not in cur:
            print(f"  ⚠ Navigated away to {cur}, going back...")
            driver.get(original_url)
            time.sleep(3)
            return False
        return True

    # Strategy 1: Look for text-based reply buttons
    try:
        reply_btns = driver.find_elements(By.XPATH,
            "//button[contains(text(), 'Trả lời tất cả')] | "
            "//button[contains(text(), 'Trả lời')] | "
            "//span[contains(text(), 'Trả lời')]/.."
        )
        if reply_btns:
            reply_btns[0].click()
            if _verify_still_on_thread():
                print(f"  ✅ Reply form opened (text button)")
                return True
    except Exception as e:
        print(f"  ⚠ Text button search error: {e}")

    # Strategy 2: Icon buttons with title/aria-label
    try:
        icons = driver.find_elements(By.CSS_SELECTOR,
            "[title*='Trả lời'], [title*='Reply'], [aria-label*='reply'], "
            "[title*='trả lời'], [title*='Phản hồi']"
        )
        if icons:
            # Prefer "Reply All" (usually last icon)
            icons[-1].click()
            if _verify_still_on_thread():
                print(f"  ✅ Reply form opened (icon button)")
                return True
    except Exception:
        pass

    # Strategy 3: JavaScript - find reply/reply-all/forward buttons in action bar
    # These are the 3 arrow icons at top-right of mail detail (↰ ↰↰ ↱)
    try:
        clicked = driver.execute_script("""
            // Find reply buttons ONLY in the mail detail toolbar area
            // The mail action bar contains reply/reply-all/forward as icon buttons
            // Filter out sidebar/nav elements by checking parent containers
            
            var btns = document.querySelectorAll('button, [role="button"], a[class*="btn"]');
            var candidates = [];
            
            for (var i = 0; i < btns.length; i++) {
                var btn = btns[i];
                var title = (btn.title || btn.getAttribute('aria-label') || '').toLowerCase();
                var text = (btn.textContent || '').trim();
                
                // Skip if inside sidebar/nav
                var inSidebar = false;
                var parent = btn;
                for (var p = 0; p < 10; p++) {
                    parent = parent.parentElement;
                    if (!parent) break;
                    var cls = String(parent.className || '').toLowerCase();
                    var tag = parent.tagName.toLowerCase();
                    if (tag === 'nav' || cls.includes('sidebar') || cls.includes('navigation') || 
                        cls.includes('menu') || cls.includes('aside')) {
                        inSidebar = true;
                        break;
                    }
                }
                if (inSidebar) continue;
                
                if (title.includes('reply') || title.includes('trả lời') ||
                    title.includes('phản hồi') || text === 'Trả lời') {
                    candidates.push({btn: btn, priority: 1});
                }
            }
            
            // Sort: prefer Reply All
            if (candidates.length > 0) {
                // Click the last one (usually Reply All)
                candidates[candidates.length - 1].btn.click();
                return 'reply_button';
            }
            
            // Fallback: look for reply-like icon buttons in the top action bar
            // These are typically right after the mail header, before the mail body
            // Look for SVGs inside button-like elements that are NOT in the sidebar
            var actionBtns = document.querySelectorAll('.detail-mail button, .mail-detail button, [class*="action"] button, [class*="toolbar"] button');
            if (actionBtns.length === 0) {
                // Broader search: buttons containing SVGs, but not in left sidebar
                var allBtns = document.querySelectorAll('button');
                for (var i = 0; i < allBtns.length; i++) {
                    var btn = allBtns[i];
                    var rect = btn.getBoundingClientRect();
                    // Must be in the main content area (x > 100 to skip sidebar)
                    // and in the upper portion of the page (y < 200 for toolbar)
                    if (rect.x > 100 && rect.y < 200 && rect.y > 50) {
                        var hasSvg = btn.querySelector('svg');
                        if (hasSvg) {
                            actionBtns = Array.from(actionBtns || []);
                            actionBtns.push(btn);
                        }
                    }
                }
            }
            
            // Click the reply button (usually 1st or 2nd from the reply/reply-all/forward group)
            // The reply-all icon is typically the 2nd one
            if (actionBtns.length >= 2) {
                actionBtns[1].click();  // Reply-all (2nd icon)
                return 'action_bar_2';
            } else if (actionBtns.length === 1) {
                actionBtns[0].click();
                return 'action_bar_1';
            }
            
            return null;
        """)
        if clicked:
            if _verify_still_on_thread():
                # Check if CKEditor appeared
                time.sleep(2)
                editors = driver.find_elements(By.CSS_SELECTOR,
                    ".ck-editor__editable, [role='textbox'][contenteditable='true']")
                if editors:
                    print(f"  ✅ Reply form opened (JS: {clicked})")
                    return True
                else:
                    print(f"  ⚠ Clicked {clicked} but no editor appeared")
    except Exception as e:
        print(f"  ⚠ JS reply search error: {e}")

    # Strategy 4: Scroll down and try to find reply area (some UIs auto-show)
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        editors = driver.find_elements(By.CSS_SELECTOR,
            ".ck-editor__editable, [role='textbox'][contenteditable='true']")
        if editors:
            print(f"  ✅ Reply editor already visible (auto-reply)")
            return True
    except Exception:
        pass

    # Strategy 5: Try clicking reply icons at absolute positions (top-right area)
    # Haraworks puts 3 arrow icons at top-right: reply, reply-all, forward
    try:
        clicked = driver.execute_script("""
            // The 3 icons at the top-right of mail detail view
            // Position: rightmost area of the toolbar, coordinates typically (1000-1150, 80-100)
            var btns = document.querySelectorAll('button, a');
            var topRight = [];
            for (var i = 0; i < btns.length; i++) {
                var r = btns[i].getBoundingClientRect();
                if (r.x > 900 && r.y > 60 && r.y < 130 && r.width < 60) {
                    topRight.push(btns[i]);
                }
            }
            // Click the 2nd one (reply-all) or 1st (reply)
            if (topRight.length >= 2) {
                topRight[1].click();
                return 'topright_2';
            } else if (topRight.length >= 1) {
                topRight[0].click();
                return 'topright_1';
            }
            return null;
        """)
        if clicked:
            if _verify_still_on_thread():
                time.sleep(3)
                editors = driver.find_elements(By.CSS_SELECTOR,
                    ".ck-editor__editable, [role='textbox'][contenteditable='true']")
                if editors:
                    print(f"  ✅ Reply form opened (JS: {clicked})")
                    return True
    except Exception as e:
        print(f"  ⚠ Top-right icon search error: {e}")

    print(f"  ❌ Could not find reply button")
    return False


def fill_subject(driver, subject):
    """Fill in the subject field."""
    from selenium.webdriver.common.by import By

    try:
        subj_input = driver.find_element(By.CSS_SELECTOR,
            "input.internal__mail_create__title, input[placeholder*='Tiêu đề']")
        subj_input.clear()
        subj_input.send_keys(subject)
        print(f"  ✅ Subject: {subject}")
        return True
    except Exception as e:
        print(f"  ⚠ Subject field error: {e}")
        return False


def inject_html_body(driver, html_content, kho="", session=None):
    """Inject HTML content into CKEditor.
    
    PRIMARY method: JS base64 inject + CKEditor setData()
      - Encodes HTML as base64, sends via execute_script() in chunks
      - Decodes in browser, calls ckeditorInstance.setData()
      - Session-independent: works from any terminal/session context
    
    FALLBACK: Clipboard paste (Ctrl+V)
      - Only used when JS inject fails (rare)
    
    Root cause of previous clipboard failures: clipboard is per-session
    on Windows. When run from a different session (e.g. Antigravity terminal),
    the clipboard copy goes to session 0 but browser reads from session 1.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    import subprocess as _sp

    print(f"  📋 Injecting HTML into CKEditor ({len(html_content)} chars)...")

    SELECTORS = [
        '.ck-editor__editable_inline',
        'div[role="textbox"].ck-content',
        '.ck-editor__editable',
        '[role="textbox"][contenteditable="true"]',
        '[contenteditable="true"].ck-content',
        'div[contenteditable="true"][data-placeholder]',
        'div[contenteditable="true"]',
    ]

    # JS to check editor exists (no large HTML argument)
    check_editor_js = """
    (function() {
        var SELS = [
            '.ck-editor__editable_inline',
            'div[role="textbox"].ck-content',
            '.ck-editor__editable',
            '[role="textbox"][contenteditable="true"]',
            '[contenteditable="true"].ck-content',
            'div[contenteditable="true"][data-placeholder]',
            'div[contenteditable="true"]'
        ];
        for (var s = 0; s < SELS.length; s++) {
            try {
                var el = document.querySelector(SELS[s]);
                if (el && el.contentEditable === 'true') {
                    var cn = '';
                    try { cn = String(el.className || '').substring(0, 100); } catch(e) { cn = '?'; }
                    return {
                        found: true,
                        selector: SELS[s],
                        hasInstance: !!el.ckeditorInstance,
                        tag: el.tagName,
                        className: cn
                    };
                }
            } catch(e) {}
        }
        return {found: false};
    })();
    """

    # JS to verify content was injected — checks ONLY the editor element
    verify_js = """
    (function() {
        var SELS = [
            '.ck-editor__editable_inline',
            'div[role="textbox"].ck-content',
            '.ck-editor__editable',
            '[role="textbox"][contenteditable="true"]',
            'div[contenteditable="true"]'
        ];
        for (var s = 0; s < SELS.length; s++) {
            try {
                var el = document.querySelector(SELS[s]);
                if (el && el.contentEditable === 'true') {
                    var html = el.innerHTML || '';
                    var len = html.length;
                    var text = el.textContent || '';
                    var hasTable = html.indexOf('<table') >= 0 || html.indexOf('<TABLE') >= 0;
                    return {content_length: len, text_length: text.length, has_table: hasTable};
                }
            } catch(e) {}
        }
        return {content_length: 0, text_length: 0, has_table: false};
    })();
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Scroll to ensure editor is visible
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Step 1: Find the editor element using Selenium (more reliable than JS)
            editor_el = None
            matched_sel = None
            for sel in SELECTORS:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        # Check if it's visible and likely a CKEditor editable
                        if el.is_displayed():
                            ce = el.get_attribute('contenteditable')
                            if ce and ce.lower() == 'true':
                                editor_el = el
                                matched_sel = sel
                                break
                except Exception:
                    continue
                if editor_el:
                    break

            # Also try JS check for metadata
            editor_info = {}
            try:
                editor_info = driver.execute_script(check_editor_js) or {}
            except Exception:
                pass

            if not editor_el:
                # Fallback: try with just data-placeholder
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, '[data-placeholder="Nhập nội dung"]')
                    for el in els:
                        if el.is_displayed():
                            editor_el = el
                            matched_sel = '[data-placeholder="Nhập nội dung"]'
                            break
                except Exception:
                    pass

            if not editor_el:
                if attempt < max_retries - 1:
                    print(f"  ⏳ Editor not found, waiting... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(4)
                    continue
                else:
                    print(f"  ❌ CKEditor not found after {max_retries} attempts")
                    return False

            has_ck_instance = editor_info.get('hasInstance', False)
            print(f"  📍 Editor found via Selenium: {matched_sel} "
                  f"(JS info: {editor_info.get('found', '?')}, "
                  f"instance: {has_ck_instance})")

            # ══════════════════════════════════════════════════════
            # METHOD 1: JS base64 inject (PRIMARY — session-independent)
            # Encodes HTML as base64, sends in JS chunks, decodes
            # in browser, and calls CKEditor setData() directly.
            # Does NOT depend on clipboard → works from any session.
            # ══════════════════════════════════════════════════════
            print(f"  🔄 Method 1: JS base64 + setData (session-independent)...")
            try:
                import base64 as _b64
                b64 = _b64.b64encode(html_content.encode('utf-8')).decode('ascii')
                JS_CHUNK = 50000
                b64_chunks = [b64[i:i+JS_CHUNK] for i in range(0, len(b64), JS_CHUNK)]

                # Initialize accumulator
                driver.execute_script("window.__inject_b64 = '';")
                print(f"  📋 Sending {len(b64)} base64 chars in {len(b64_chunks)} chunks...")
                for ci, chunk in enumerate(b64_chunks):
                    driver.execute_script(f"window.__inject_b64 += '{chunk}';")

                # Decode and inject via CKEditor setData
                js_result = driver.execute_script("""
                    try {
                        var b64 = window.__inject_b64;
                        if (!b64) return {ok: false, error: 'no_b64_data'};
                        var bytes = Uint8Array.from(atob(b64), function(c) { return c.charCodeAt(0); });
                        var html = new TextDecoder('utf-8').decode(bytes);

                        // CKEditor 5 setData (preferred)
                        var editables = document.querySelectorAll('[contenteditable="true"]');
                        for (var i = 0; i < editables.length; i++) {
                            var inst = editables[i].ckeditorInstance;
                            if (inst && inst.setData) {
                                inst.setData(html);
                                delete window.__inject_b64;
                                return {ok: true, method: 'ck5_setData', len: html.length,
                                        has_table: html.indexOf('<table') >= 0};
                            }
                        }

                        // Fallback: innerHTML on CK-styled editor
                        for (var i = 0; i < editables.length; i++) {
                            var cls = editables[i].className || '';
                            if (cls.includes('ck-')) {
                                editables[i].innerHTML = html;
                                ['input', 'change', 'keyup'].forEach(function(evt) {
                                    editables[i].dispatchEvent(new Event(evt, {bubbles: true}));
                                });
                                delete window.__inject_b64;
                                return {ok: true, method: 'innerHTML', len: html.length,
                                        has_table: html.indexOf('<table') >= 0};
                            }
                        }

                        delete window.__inject_b64;
                        return {ok: false, error: 'no_ck_editor_found'};
                    } catch(e) {
                        return {ok: false, error: e.toString()};
                    }
                """)

                if js_result and js_result.get('ok'):
                    print(f"  ✅ HTML injected (method: {js_result.get('method')}, "
                          f"len={js_result.get('len')}, table={js_result.get('has_table')})")

                    # Verify injection by checking editor content
                    time.sleep(2)
                    verify_result = driver.execute_script(verify_js) or {}
                    v_len = verify_result.get('content_length', 0)
                    v_table = verify_result.get('has_table', False)
                    v_text = verify_result.get('text_length', 0)
                    if v_len > 100 or v_text > 50:
                        print(f"  ✅ Verified: editor has {v_len} chars, table={v_table}, text={v_text}")
                    else:
                        print(f"  ⚠ Verify: editor content may be empty (len={v_len}, text={v_text})")

                    return True
                else:
                    print(f"  ⚠ JS base64 inject result: {js_result}")
            except Exception as e:
                print(f"  ⚠ JS base64 method error: {e}")

            # ══════════════════════════════════════════════════════
            # METHOD 2: Clipboard Paste (FALLBACK)
            # Only works when run in same session as browser.
            # ══════════════════════════════════════════════════════
            print(f"  📋 Method 2: Clipboard paste (fallback)...")

            clip_copied = False
            try:
                tmp_html = os.path.join(OUTPUT, "mail", "_inject_temp.html")
                with open(tmp_html, "w", encoding="utf-8") as f:
                    f.write(html_content)

                clip_candidates = []
                if kho:
                    clip_candidates.append(get_clip_ps1_path(kho, session))
                clip_candidates.append(get_clip_ps1_path("", None))

                for clip_candidate in clip_candidates:
                    if os.path.exists(clip_candidate):
                        cp = _sp.run(
                            ["powershell", "-ExecutionPolicy", "Bypass",
                             "-File", clip_candidate, "_inject_temp.html"],
                            capture_output=True, text=True, timeout=15,
                            encoding='utf-8', errors='replace'
                        )
                        if cp.returncode == 0:
                            clip_copied = True
                            print(f"  ✅ HTML copied to clipboard via {os.path.basename(clip_candidate)}")
                            break
            except Exception as clip_err:
                print(f"  ⚠ Clip script error: {clip_err}")

            if clip_copied and editor_el:
                editor_el.click()
                time.sleep(0.5)
                ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                time.sleep(0.3)
                ActionChains(driver).send_keys(Keys.DELETE).perform()
                time.sleep(0.3)
                ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(4)

                # Verify using ONLY the editor element (not page_source)
                paste_ok = False
                for verify_attempt in range(5):
                    time.sleep(2)
                    try:
                        verify_result = driver.execute_script(verify_js) or {}
                        v_len = verify_result.get('content_length', 0)
                        v_table = verify_result.get('has_table', False)
                        v_text = verify_result.get('text_length', 0)

                        if v_len > 100 or v_text > 50:
                            print(f"  ✅ HTML injected (method: clipboard_paste, "
                                  f"editor_len={v_len}, text={v_text}, table={v_table})")
                            paste_ok = True
                            break

                        if verify_attempt < 4:
                            print(f"  ⏳ Verifying paste... (editor_len={v_len}, text={v_text})")
                    except Exception as ve:
                        print(f"  ⚠ Verify attempt {verify_attempt+1}: {ve}")

                if paste_ok:
                    return True
                else:
                    print(f"  ⚠ Clipboard paste failed — editor still empty")

            # If all methods failed for this attempt
            if attempt < max_retries - 1:
                print(f"  ⏳ Attempt {attempt + 1}/{max_retries} failed, retrying...")
                time.sleep(4)
            else:
                print(f"  ❌ All injection methods failed after {max_retries} attempts")
                return False

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⏳ Injection error (attempt {attempt + 1}): {e}, retrying...")
                time.sleep(4)
            else:
                print(f"  ❌ Injection error: {e}")
                return False
    return False


def wait_for_autosave(driver, timeout=10):
    """Wait for Haraworks auto-save to complete."""
    from selenium.webdriver.common.by import By

    print(f"  💾 Waiting for auto-save...")
    for _ in range(timeout):
        try:
            status_el = driver.find_elements(By.XPATH, "//*[contains(text(), 'Đã lưu')]")
            if status_el:
                print(f"  ✅ Draft saved (Đã lưu)")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"  ⚠ Auto-save status not confirmed (may still be saving)")
    return False


def take_screenshot(driver, filename):
    """Save screenshot for verification."""
    logs_dir = os.path.join(OUTPUT, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    path = os.path.join(logs_dir, filename)
    driver.save_screenshot(path)
    print(f"  📸 Screenshot: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Inject composed mail into Haraworks CKEditor")
    parser.add_argument("--kho", required=True, help="Warehouse: KRC, DRY, 'ĐÔNG MÁT', 'THỊT CÁ'")
    parser.add_argument("--session", choices=["sang", "toi"], help="Session for DRY")
    parser.add_argument("--date", required=True, help="Delivery date: DD/MM/YYYY")
    parser.add_argument("--week", required=True, help="Week: W15")
    parser.add_argument("--reply", action="store_true",
                        help="Force reply mode (search existing thread)")
    parser.add_argument("--new", action="store_true",
                        help="Force compose new mail (don't search thread)")
    parser.add_argument("--no-close", action="store_true",
                        help="Don't close browser after injection")
    args = parser.parse_args()

    kho = args.kho.upper()
    if kho == "DONG MAT":
        kho = "ĐÔNG MÁT"
    elif kho == "THIT CA":
        kho = "THỊT CÁ"

    mail_key = get_mail_key(kho, args.session)
    config = MAIL_CONFIG.get(mail_key)
    if not config:
        print(f"❌ Unknown kho/session: {mail_key}")
        print(f"   Available: {list(MAIL_CONFIG.keys())}")
        sys.exit(1)

    subject = config["subject_tpl"].format(week=args.week)
    session_label = ""
    if args.session:
        session_label = " Sáng" if args.session == "sang" else " Tối"

    # Load HTML body
    html_path = get_html_body_path(kho, args.session)
    if not os.path.exists(html_path):
        print(f"❌ HTML body not found: {html_path}")
        print(f"   Run compose_mail.py first!")
        sys.exit(1)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    print("=" * 60)
    print(f"  🚀 INJECT HARAWORKS — {kho}{session_label}")
    print(f"  Subject: {subject}")
    print(f"  Date: {args.date}")
    print(f"  HTML: {html_path} ({len(html_content)} chars)")
    print("=" * 60)

    # Setup browser
    print(f"\n  🌐 Opening browser...")
    driver = setup_driver()

    try:
        # Step 0: Ensure logged in
        if not ensure_logged_in(driver):
            print(f"\n  ❌ Cannot login to Haraworks!")
            print(f"  💡 First run: login manually in the Edge automation browser,")
            print(f"     session will be saved in .edge_automail/ for future runs.")
            sys.exit(1)

        # Step 1: Try reply to existing thread (default behavior)
        # Business rule: 1 thread per week per kho → reply into existing thread
        if args.new:
            # Force new compose
            print(f"  📝 --new flag: composing new mail")
            open_compose_new(driver)
            fill_subject(driver, subject)
        else:
            # Search for existing thread (in Sent folder)
            thread_url = find_existing_thread(driver, subject)
            if thread_url:
                success = open_reply_in_thread(driver, thread_url)
                if not success:
                    print(f"  ⚠ Reply failed, falling back to compose new")
                    open_compose_new(driver)
                    fill_subject(driver, subject)
            else:
                print(f"  📝 No existing thread → composing new mail")
                open_compose_new(driver)
                fill_subject(driver, subject)

        # Step 2: Wait a moment for page to stabilize
        time.sleep(2)

        # Step 3: Inject HTML body into CKEditor
        injected = inject_html_body(driver, html_content, kho=kho, session=args.session)

        if not injected:
            print(f"\n  ⚠ CKEditor injection failed — copying to clipboard for manual paste...")
            take_screenshot(driver, f"_inject_fail_{kho}.png")

            # Clipboard fallback: copy HTML so user can paste manually
            try:
                clip_script = os.path.join(OUTPUT, "_clip_KRC_html.ps1")
                mail_key_clip = get_mail_key(kho, args.session)
                html_file_arg = f"_mail_{kho}{'_' + args.session if args.session else ''}_body.html"
                import subprocess
                subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass",
                    "-File", clip_script, "-File", html_file_arg
                ], capture_output=True, timeout=10)
                print(f"  📋 HTML copied to clipboard! Ctrl+V to paste.")
            except Exception as clip_err:
                print(f"  ⚠ Clipboard copy also failed: {clip_err}")

            # Windows notification
            try:
                from plyer import Notification
                Notification().notify(
                    title=f"⚠ {kho}{session_label} — Paste thủ công",
                    message=f"Inject CKEditor fail — HTML đã copy vào clipboard. Ctrl+V để paste.",
                    timeout=15
                )
            except Exception:
                # Fallback: use PowerShell toast
                try:
                    import subprocess
                    toast_msg = f"{kho}{session_label}: Inject fail — HTML da copy clipboard. Ctrl+V de paste."
                    subprocess.run([
                        "powershell", "-Command",
                        f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                        f"[System.Windows.Forms.MessageBox]::Show('{toast_msg}', 'Haraworks Inject', 'OK', 'Warning')"
                    ], capture_output=True, timeout=10)
                except Exception:
                    pass

            print(f"\n  ❌ INJECTION FAILED — nhưng HTML đã copy clipboard!")
            print(f"  👉 Mở reply form trên Haraworks → Ctrl+V paste")
            sys.exit(1)

        # Step 4: Wait for auto-save
        time.sleep(2)
        wait_for_autosave(driver)

        # Step 5: Screenshot for verification
        time.sleep(1)
        screenshot = take_screenshot(driver, f"_inject_{kho}{'_' + args.session if args.session else ''}.png")

        print(f"\n{'=' * 60}")
        print(f"  ✅ DONE — Mail injected as DRAFT")
        print(f"  ⚠ KHÔNG GỬI — chờ user review & gửi thủ công")
        print(f"  📸 Screenshot: {screenshot}")
        print(f"{'=' * 60}")

        if args.no_close:
            print(f"\n  Browser left open (--no-close). Press Enter to close...")
            input()

    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            take_screenshot(driver, f"_inject_error_{kho}.png")
        except Exception:
            pass
    finally:
        if not args.no_close:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
