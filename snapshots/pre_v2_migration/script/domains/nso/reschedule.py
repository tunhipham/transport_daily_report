"""
reschedule.py — Update NSO store opening dates (reschedule/defer)

Usage:
  python script/domains/nso/reschedule.py --code A194 --date 06/06/2026
  python script/domains/nso/reschedule.py --code A194 --date 06/06/2026 --deploy

Reads from nso_stores.json, updates opening_date, sets original_date,
re-exports nso.json + Excel, optionally deploys dashboard.
"""
import os, sys, json, subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STORES_PATH = os.path.join(REPO_ROOT, "data", "nso", "nso_stores.json")

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load_stores():
    with open(STORES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_stores(stores):
    with open(STORES_PATH, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)


def reschedule(code, new_date):
    """Update store opening_date. Returns (old_date, store_name) or raises."""
    stores = load_stores()
    found = None
    for s in stores:
        if s.get("code") == code:
            found = s
            break
    if not found:
        raise ValueError(f"Store code '{code}' không tìm thấy trong nso_stores.json")

    old_date = found["opening_date"]
    if old_date == new_date:
        print(f"  ℹ️  {code} đã có opening_date = {new_date}, không thay đổi.")
        return old_date, found.get("name_full", "")

    # Shift current date → original_date, set new date
    found["original_date"] = old_date
    found["opening_date"] = new_date

    save_stores(stores)
    name = found.get("name_full") or found.get("name_mail", "")
    print(f"  ✅ {code} — {name}")
    print(f"     {old_date} → {new_date}")
    return old_date, name


def main():
    code = None
    new_date = None
    do_deploy = "--deploy" in sys.argv

    if "--code" in sys.argv:
        idx = sys.argv.index("--code")
        code = sys.argv[idx + 1]
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        new_date = sys.argv[idx + 1]

    if not code or not new_date:
        print("Usage: python reschedule.py --code <CODE> --date DD/MM/YYYY [--deploy]")
        sys.exit(1)

    # Validate date format
    import re
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', new_date):
        print(f"  ❌ Ngày không hợp lệ: {new_date} (cần DD/MM/YYYY)")
        sys.exit(1)

    print(f"\n🔄 NSO Reschedule: {code} → {new_date}")
    print("=" * 50)

    old_date, name = reschedule(code, new_date)

    # Re-export nso.json + Excel
    print(f"\n📊 Re-exporting...")
    export_data = os.path.join(REPO_ROOT, "script", "dashboard", "export_data.py")
    subprocess.run([sys.executable, export_data, "--domain", "nso"],
                   cwd=REPO_ROOT, encoding="utf-8", errors="replace")

    export_excel = os.path.join(REPO_ROOT, "script", "domains", "nso", "export_excel.py")
    subprocess.run([sys.executable, export_excel],
                   cwd=REPO_ROOT, encoding="utf-8", errors="replace")

    # Deploy if requested
    if do_deploy:
        print(f"\n🚀 Deploying dashboard...")
        deploy_script = os.path.join(REPO_ROOT, "script", "dashboard", "deploy.py")
        subprocess.run([sys.executable, deploy_script, "--domain", "nso"],
                       cwd=REPO_ROOT, encoding="utf-8", errors="replace")

    print(f"\n{'=' * 50}")
    print(f"  DONE — {code}: {old_date} → {new_date}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
