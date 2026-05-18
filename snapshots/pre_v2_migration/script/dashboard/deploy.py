"""
deploy.py — Deploy dashboard to GitHub Pages
==============================================
1. Run export_data.py to generate JSON
2. Validate no unauthorized external changes
3. Git add + commit + push docs/ to main branch
4. GitHub Pages serves from /docs on main branch

Usage:
    python script/dashboard/deploy.py [--domain all|daily|performance|inventory|nso]
    python script/dashboard/deploy.py --skip-export  # only git push, skip data export
"""
import os, sys, subprocess, argparse, json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE, "docs")
ACCESS_CFG = os.path.join(BASE, "config", "external_access.json")


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


def check_external_tampering():
    """
    🔒 SECURITY CHECK: Detect unauthorized changes from external collaborators.

    Scans recent git history for commits by non-owner authors that touched
    protected files (index.html, data/, scripts/, etc).

    Returns list of violations found.
    """
    violations = []

    # Load access config
    if not os.path.exists(ACCESS_CFG):
        return violations  # No config = skip check

    with open(ACCESS_CFG, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    allowed_paths = set(cfg.get("external_allowed_paths", []))
    protected_prefixes = cfg.get("protected_files", [])
    external_authors = set(cfg.get("allowed_external_authors", []))

    if not external_authors:
        return violations

    # Check last 20 commits for external author changes to protected files
    ok, log_out = run_cmd([
        "git", "log", "--format=%H|%an", "-20",
        "--diff-filter=ACDMR", "--name-only"
    ])

    if not ok:
        return violations

    lines = log_out.strip().split('\n')
    current_hash = None
    current_author = None
    is_external = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '|' in line and len(line.split('|')[0]) == 40:
            # This is a commit header: hash|author
            parts = line.split('|', 1)
            current_hash = parts[0]
            current_author = parts[1]
            is_external = current_author in external_authors
        elif is_external and line:
            # This is a file path from an external author's commit
            file_path = line
            # Check if this file is outside their allowed scope
            if file_path in allowed_paths:
                continue
            # Check if file starts with an allowed path prefix
            is_allowed = False
            for ap in allowed_paths:
                if file_path == ap or (ap.endswith('/') and file_path.startswith(ap)):
                    is_allowed = True
                    break
            if not is_allowed:
                # Check if it's a protected file
                for pf in protected_prefixes:
                    if file_path == pf or file_path.startswith(pf):
                        violations.append({
                            "commit": current_hash[:7],
                            "author": current_author,
                            "file": file_path,
                            "protected_by": pf
                        })
                        break

    return violations


def main():
    parser = argparse.ArgumentParser(description="Deploy dashboard to GitHub Pages")
    parser.add_argument("--domain", default="all",
                        choices=["all", "daily", "performance", "inventory", "nso", "weekly_plan"])
    parser.add_argument("--skip-export", action="store_true",
                        help="Skip data export, only push existing files")
    parser.add_argument("--skip-security", action="store_true",
                        help="Skip external tampering check (use with caution)")
    args = parser.parse_args()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n{'═'*60}")
    print(f"  🚀 Dashboard Deploy — {now}")
    print(f"{'═'*60}\n")

    # Step 0: Security check — detect external tampering
    if not args.skip_security:
        print("🔒 Step 0: Security check — scanning for unauthorized changes...")
        violations = check_external_tampering()
        if violations:
            print(f"\n  🚨 {'═'*50}")
            print(f"  🚨  CẢNH BÁO: Phát hiện {len(violations)} thay đổi TRÁI PHÉP!")
            print(f"  🚨 {'═'*50}")
            for v in violations:
                print(f"  ❌ [{v['commit']}] {v['author']} sửa: {v['file']}")
                print(f"     → File này thuộc vùng bảo vệ: {v['protected_by']}")
            print()
            print(f"  ⚠ Deploy bị CHẶN. External đã sửa file ngoài scope cho phép.")
            print(f"  💡 Kiểm tra và revert các commit trên trước khi deploy.")
            print(f"     Hoặc dùng --skip-security để bỏ qua (KHÔNG KHUYẾN KHÍCH).")
            print(f"  🚨 {'═'*50}\n")
            sys.exit(1)
        else:
            print("  ✅ Không phát hiện thay đổi trái phép từ external\n")
    else:
        print("⏭ Skipping security check\n")

    # Step 1: Export data
    if not args.skip_export:
        print("📊 Step 1: Exporting data...")
        export_script = os.path.join(BASE, "script", "dashboard", "export_data.py")
        ok, out = run_cmd([sys.executable, export_script, "--domain", args.domain])
        print(out)
        if not ok:
            print("  ⚠ Export had errors, continuing...")

        # Also export weekly plan if domain is all or weekly_plan
        if args.domain in ("all", "weekly_plan"):
            print("\n📅 Exporting weekly transport plan...")
            wk_script = os.path.join(BASE, "script", "dashboard", "export_weekly_plan.py")
            ok2, out2 = run_cmd([sys.executable, wk_script])
            print(out2)
            if not ok2:
                print("  ⚠ Weekly plan export had errors, continuing...")
    else:
        print("⏭ Skipping data export")

    # Step 2: Check if docs/ has changes
    print("\n📁 Step 2: Checking for changes...")
    ok, status = run_cmd(["git", "status", "--porcelain"])
    if not status.strip():
        print("  ℹ No changes in docs/ — nothing to deploy")
        return

    print(f"  Changes detected:\n{status}")

    # Step 3: Git add + commit + push
    print("📤 Step 3: Deploying to GitHub Pages...")

    # Add all tracked changes (docs + scripts + agents)
    ok, out = run_cmd(["git", "add", "-A"])
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
