"""
canonforge/engines/hooks.py

CanonForge Git Pre-Commit Hook Management Engine (cf hook install|uninstall|status).
Enforces zero-slop prose, valid OKF v0.3 frontmatter, and deep POV compliance before commit.
100% Free of Universe-Specific Hardcoding.
"""

import sys
import os
import stat
import argparse
from pathlib import Path
from typing import Optional

HOOK_SCRIPT = """#!/usr/bin/env bash
# CanonForge Git Pre-Commit Gate
# Ensures zero-slop prose, deep POV, and valid frontmatter on staged chapters.
set -e

if ! command -v cf >/dev/null 2>&1; then
    echo "⚠️ CanonForge (cf) CLI not found in PATH. Skipping pre-commit audit."
    exit 0
fi

# Detect staged markdown files under manuscript/
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '^manuscript/.*\\.md$' | grep -v '_build\\|compiled\\|archive\\|exports' || true)

if [ -n "$STAGED_FILES" ]; then
    echo "🔍 [CanonForge Pre-Commit] Auditing staged manuscript chapters..."
    FAILED=0
    for ch in $STAGED_FILES; do
        if [ -f "$ch" ]; then
            echo "   • Checking: $ch"
            if ! cf audit "$ch"; then
                FAILED=1
            fi
        fi
    done

    if [ $FAILED -ne 0 ]; then
        echo "\\n❌ [CanonForge Pre-Commit] Audit failed! Fix continuity or schema errors above before committing."
        exit 1
    fi
    echo "✅ [CanonForge Pre-Commit] Staged chapters passed all integrity gates! Proceeding."
fi
exit 0
"""

def find_git_root(start_dir: Optional[Path] = None) -> Optional[Path]:
    cwd = (start_dir or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").is_dir() or (parent / ".git").is_file():
            return parent
    return None

def install_git_hook(repo_dir: Optional[Path] = None) -> Path:
    git_root = find_git_root(repo_dir)
    if not git_root:
        print("❌ Error: No Git repository found in active directory or ancestors.")
        sys.exit(1)

    hooks_dir = git_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    hook_file.write_text(HOOK_SCRIPT, encoding="utf-8")
    # Make executable (chmod +x)
    current_stat = hook_file.stat().st_mode
    hook_file.chmod(current_stat | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return hook_file

def uninstall_git_hook(repo_dir: Optional[Path] = None) -> bool:
    git_root = find_git_root(repo_dir)
    if not git_root:
        print("❌ Error: No Git repository found.")
        sys.exit(1)

    hook_file = git_root / ".git" / "hooks" / "pre-commit"
    if hook_file.is_file():
        hook_file.unlink()
        return True
    return False

def check_hook_status(repo_dir: Optional[Path] = None) -> bool:
    git_root = find_git_root(repo_dir)
    if not git_root:
        return False
    hook_file = git_root / ".git" / "hooks" / "pre-commit"
    return hook_file.is_file() and os.access(hook_file, os.X_OK)

def main():
    parser = argparse.ArgumentParser(description="CanonForge Git Pre-Commit Hook Manager")
    parser.add_argument("action", choices=["install", "uninstall", "status"], default="install", nargs="?", help="Action to perform")
    parser.add_argument("--repo", "-r", help="Target Git repository path")
    args = parser.parse_args()

    repo = Path(args.repo) if args.repo else None

    if args.action == "install":
        h_file = install_git_hook(repo)
        print(f"\n⚓ CanonForge Git Pre-Commit Hook Installed!")
        print(f"   Location : {h_file}")
        print(f"   Status   : Active & Executable (0755)")
        print("💡 All future 'git commit' calls will automatically verify staged manuscript chapters.\n")
    elif args.action == "uninstall":
        removed = uninstall_git_hook(repo)
        if removed:
            print("\n🧹 CanonForge Git Pre-Commit Hook uninstalled successfully.\n")
        else:
            print("\nℹ️  No pre-commit hook found to uninstall.\n")
    elif args.action == "status":
        active = check_hook_status(repo)
        git_root = find_git_root(repo)
        print(f"\n⚓ CanonForge Hook Status:")
        print(f"   Git Root : {git_root or 'Not in a Git repository'}")
        print(f"   Hook     : {'🟢 Active & Executable' if active else '🔴 Not installed'}\n")

if __name__ == "__main__":
    main()
