"""
deploy.py — Auto-deploy external dashboard files
==================================================
Dành cho external collaborator (ThanhPhammm111).
Tự động tạo PR để update dữ liệu lên dashboard.

Flow:
  1. Kiểm tra chỉ có file trong WHITELIST thay đổi
  2. Tạo branch mới (auto-tên theo timestamp)
  3. Commit + push
  4. Tạo PR qua GitHub CLI (gh)
  5. GitHub Actions auto-approve + auto-merge

Nếu có file NGOÀI whitelist → BLOCK, không deploy.

Usage:
    python script/external/deploy.py
    python script/external/deploy.py --message "Update data T05"
"""
import os
import sys
import subprocess
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══════════════════════════════════════════════════════════
# WHITELIST — chỉ các file này được auto-deploy
# Thêm file mới vào đây CẦN owner (tunhipham) duyệt trước
# ═══════════════════════════════════════════════════════════
WHITELIST = [
    "docs/external/nhap_xuat_dm.html",
    "docs/external/claim_aba.html",
]


def run(cmd, cwd=None):
    """Run command, return (success, output)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd or BASE,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


def get_changed_files():
    """Get list of changed files in docs/external/ (staged + unstaged)."""
    changed = set()

    # Unstaged changes
    ok, out = run(["git", "diff", "--name-only", "--", "docs/external/"])
    if ok and out:
        changed.update(out.splitlines())

    # Staged changes
    ok, out = run(["git", "diff", "--cached", "--name-only", "--", "docs/external/"])
    if ok and out:
        changed.update(out.splitlines())

    # Untracked new files
    ok, out = run(["git", "ls-files", "--others", "--exclude-standard", "--", "docs/external/"])
    if ok and out:
        changed.update(out.splitlines())

    return [f.strip() for f in changed if f.strip()]


def check_gh_cli():
    """Check if GitHub CLI (gh) is installed and authenticated."""
    ok, out = run(["gh", "auth", "status"])
    return ok


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deploy external dashboard files")
    parser.add_argument("--message", "-m", default=None,
                        help="Custom commit message")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only check, don't actually deploy")
    args = parser.parse_args()

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M")
    date_str = now.strftime("%d/%m/%Y %H:%M")

    print(f"\n{'═' * 55}")
    print(f"  📊 External Dashboard Deploy — {date_str}")
    print(f"{'═' * 55}\n")

    # ── Step 1: Check changed files ──
    print("🔍 Step 1: Kiểm tra file thay đổi...")
    changed = get_changed_files()

    if not changed:
        print("  ℹ Không có file nào thay đổi trong docs/external/")
        print("  💡 Sửa file trước rồi chạy lại script này.")
        return

    print(f"  📁 {len(changed)} file thay đổi:")
    for f in changed:
        print(f"     → {f}")

    # ── Step 2: Validate whitelist ──
    print("\n🔒 Step 2: Kiểm tra whitelist...")
    blocked = [f for f in changed if f not in WHITELIST]

    if blocked:
        print(f"\n  🚨 {'═' * 45}")
        print(f"  🚨  BLOCK — Có {len(blocked)} file NGOÀI whitelist!")
        print(f"  🚨 {'═' * 45}")
        for f in blocked:
            print(f"  ❌ {f}")
        print()
        print("  Whitelist hiện tại:")
        for f in WHITELIST:
            print(f"  ✅ {f}")
        print()
        print("  ⚠ Không thể auto-deploy.")
        print("  💡 Nếu muốn thêm tab mới → liên hệ @tunhipham để duyệt.")
        print("  💡 Nếu chỉ update data → chỉ sửa 2 file trong whitelist.")
        sys.exit(1)

    whitelisted = [f for f in changed if f in WHITELIST]
    print(f"  ✅ Tất cả {len(whitelisted)} file đều trong whitelist")

    if args.dry_run:
        print("\n  🏁 Dry-run — không deploy. Dùng lại KHÔNG có --dry-run để deploy.")
        return

    # ── Step 3: Check gh CLI ──
    print("\n🔧 Step 3: Kiểm tra GitHub CLI...")
    if not check_gh_cli():
        print("  ❌ GitHub CLI (gh) chưa login.")
        print("  💡 Chạy: gh auth login")
        sys.exit(1)
    print("  ✅ GitHub CLI đã authenticated")

    # ── Step 4: Make sure we're on latest main ──
    print("\n📥 Step 4: Pull latest main...")
    ok, out = run(["git", "checkout", "main"])
    if not ok:
        print(f"  ⚠ git checkout main: {out}")

    ok, out = run(["git", "pull", "origin", "main"])
    if not ok:
        print(f"  ⚠ git pull: {out}")
    else:
        print("  ✅ Đã pull latest")

    # Re-check changed files after pull
    changed = get_changed_files()
    if not changed:
        print("  ℹ Sau khi pull, không còn thay đổi (có thể đã merge rồi)")
        return

    # ── Step 5: Create branch ──
    branch = f"external-update-{timestamp}"
    print(f"\n🌿 Step 5: Tạo branch [{branch}]...")
    ok, out = run(["git", "checkout", "-b", branch])
    if not ok:
        print(f"  ❌ Không tạo được branch: {out}")
        sys.exit(1)
    print(f"  ✅ Branch: {branch}")

    # ── Step 6: Stage + commit ──
    print("\n📝 Step 6: Commit...")
    for f in changed:
        run(["git", "add", f])

    file_names = ", ".join(os.path.basename(f) for f in changed)
    commit_msg = args.message or f"📊 Update external data — {date_str}"

    ok, out = run(["git", "commit", "-m", commit_msg])
    if not ok:
        if "nothing to commit" in out:
            print("  ℹ Nothing to commit")
            run(["git", "checkout", "main"])
            run(["git", "branch", "-D", branch])
            return
        print(f"  ❌ Commit failed: {out}")
        run(["git", "checkout", "main"])
        sys.exit(1)
    print(f"  ✅ Committed: {commit_msg}")

    # ── Step 7: Push ──
    print(f"\n📤 Step 7: Push branch [{branch}]...")
    ok, out = run(["git", "push", "origin", branch])
    if not ok:
        print(f"  ❌ Push failed: {out}")
        run(["git", "checkout", "main"])
        sys.exit(1)
    print("  ✅ Pushed!")

    # ── Step 8: Create PR ──
    print("\n🔀 Step 8: Tạo Pull Request...")
    pr_title = f"📊 External update: {file_names} — {date_str}"
    pr_body = (
        f"## Auto-deploy external data\n\n"
        f"Files updated:\n"
        + "\n".join(f"- `{f}`" for f in changed)
        + f"\n\n---\n"
        f"🤖 Tạo tự động bởi `script/external/deploy.py`\n"
        f"GitHub Actions sẽ auto-approve + auto-merge nếu chỉ chứa file whitelisted."
    )
    ok, out = run([
        "gh", "pr", "create",
        "--base", "main",
        "--head", branch,
        "--title", pr_title,
        "--body", pr_body,
    ])
    if not ok:
        print(f"  ❌ Tạo PR thất bại: {out}")
        print(f"  💡 Thử tạo PR thủ công: https://github.com/tunhipham/transport_daily_report/compare/main...{branch}")
        run(["git", "checkout", "main"])
        sys.exit(1)

    # Extract PR URL from output
    pr_url = out.strip().split("\n")[-1].strip()
    print(f"  ✅ PR đã tạo: {pr_url}")

    # ── Step 9: Switch back to main ──
    run(["git", "checkout", "main"])

    # ── Done ──
    print(f"\n{'═' * 55}")
    print(f"  🎉 Deploy thành công!")
    print(f"  📋 PR: {pr_url}")
    print(f"  ⏱ GitHub Actions sẽ auto-approve + merge trong ~1 phút")
    print(f"  🌐 Dashboard: https://tunhipham.github.io/transport_daily_report/")
    print(f"{'═' * 55}\n")


if __name__ == "__main__":
    main()
