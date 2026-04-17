"""
deploy.py — Deploy dashboard to GitHub Pages
==============================================
1. Run export_data.py to generate JSON
2. Git add + commit + push docs/ to main branch
3. GitHub Pages serves from /docs on main branch

Usage:
    python script/dashboard/deploy.py [--domain all|daily|performance|inventory|nso]
    python script/dashboard/deploy.py --skip-export  # only git push, skip data export
"""
import os, sys, subprocess, argparse
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE, "docs")


def run_cmd(cmd, cwd=None):
    """Run command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or BASE, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Deploy dashboard to GitHub Pages")
    parser.add_argument("--domain", default="all",
                        choices=["all", "daily", "performance", "inventory", "nso"])
    parser.add_argument("--skip-export", action="store_true",
                        help="Skip data export, only push existing files")
    args = parser.parse_args()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n{'═'*60}")
    print(f"  🚀 Dashboard Deploy — {now}")
    print(f"{'═'*60}\n")

    # Step 1: Export data
    if not args.skip_export:
        print("📊 Step 1: Exporting data...")
        export_script = os.path.join(BASE, "script", "dashboard", "export_data.py")
        ok, out = run_cmd([sys.executable, export_script, "--domain", args.domain])
        print(out)
        if not ok:
            print("  ⚠ Export had errors, continuing with push...")
    else:
        print("⏭ Skipping data export")

    # Step 2: Check if docs/ has changes
    print("\n📁 Step 2: Checking for changes...")
    ok, status = run_cmd(["git", "status", "--porcelain", "docs/"])
    if not status.strip():
        print("  ℹ No changes in docs/ — nothing to deploy")
        return

    print(f"  Changes detected:\n{status}")

    # Step 3: Git add + commit + push
    print("📤 Step 3: Deploying to GitHub Pages...")

    # Add docs/
    ok, out = run_cmd(["git", "add", "docs/"])
    if not ok:
        print(f"  ❌ git add failed: {out}")
        return

    # Commit
    domain_str = args.domain if args.domain != "all" else "all domains"
    commit_msg = f"📊 Dashboard update: {domain_str} — {now}"
    ok, out = run_cmd(["git", "commit", "-m", commit_msg])
    if not ok:
        if "nothing to commit" in out:
            print("  ℹ Nothing to commit")
            return
        print(f"  ❌ git commit failed: {out}")
        return
    print(f"  ✅ Committed: {commit_msg}")

    # Push
    ok, out = run_cmd(["git", "push", "origin", "main"])
    if ok:
        print("  ✅ Pushed to origin/main")
        print(f"\n{'═'*60}")
        print(f"  🌐 Dashboard URL: https://tunhipham.github.io/transport_daily_report/")
        print(f"  ⏱ GitHub Pages sẽ cập nhật trong 1-2 phút")
        print(f"{'═'*60}\n")
    else:
        print(f"  ❌ git push failed: {out}")
        print("  💡 Thử chạy lại hoặc push thủ công: git push origin main")


if __name__ == "__main__":
    main()
