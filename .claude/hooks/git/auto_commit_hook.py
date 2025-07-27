#!/usr/bin/env python3
"""Auto-commit hook for Claude - commits changes on stop."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_git_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a git command and return exit code, stdout, and stderr."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def get_git_status(repo_path: str) -> tuple[bool, list[str], list[str]]:
    """Check if there are changes to commit."""
    # Check for uncommitted changes
    returncode, stdout, _ = run_git_command(["git", "status", "--porcelain"], repo_path)

    if returncode != 0:
        return False, [], []

    if not stdout:
        return False, [], []

    # Parse the status output
    staged = []
    unstaged = []

    for line in stdout.split("\n"):
        if line:
            status = line[:2]
            filepath = line[3:]

            if status[0] != " " and status[0] != "?":  # Staged
                staged.append(filepath)
            if status[1] != " ":  # Unstaged or untracked
                unstaged.append(filepath)

    return True, staged, unstaged


def create_commit_message(staged: list[str], unstaged: list[str]) -> str:
    """Generate a descriptive commit message based on changes."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count file types
    file_types: dict[str, int] = {}
    all_files = staged + unstaged

    for file in all_files:
        ext = Path(file).suffix.lower()
        if ext:
            file_types[ext] = file_types.get(ext, 0) + 1

    # Build commit message
    message_parts = [f"Auto-commit: Session ended at {timestamp}"]

    if file_types:
        type_summary = []
        for ext, count in sorted(file_types.items()):
            type_summary.append(f"{count} {ext} file{'s' if count > 1 else ''}")
        message_parts.append(f"\nModified: {', '.join(type_summary)}")

    message_parts.append(f"\nTotal files changed: {len(set(all_files))}")

    return "\n".join(message_parts)


def auto_commit(repo_path: str | None = None) -> bool:
    """Perform auto-commit if there are changes."""
    if repo_path is None:
        repo_path = os.getcwd()

    # Check if we're in a git repository
    returncode, _, _ = run_git_command(["git", "rev-parse", "--git-dir"], repo_path)
    if returncode != 0:
        print("❌ Not in a git repository")
        return False

    # Check for changes
    has_changes, staged, unstaged = get_git_status(repo_path)

    if not has_changes:
        print("✅ No changes to commit")
        return True

    # Stage all changes
    if unstaged:
        print(f"📝 Staging {len(unstaged)} file(s)...")
        returncode, _, stderr = run_git_command(["git", "add", "-A"], repo_path)
        if returncode != 0:
            print(f"❌ Failed to stage files: {stderr}")
            return False

    # Create commit
    commit_message = create_commit_message(staged, unstaged)
    print("💾 Creating commit...")

    returncode, stdout, stderr = run_git_command(
        ["git", "commit", "-m", commit_message], repo_path
    )

    if returncode != 0:
        print(f"❌ Failed to commit: {stderr}")
        return False

    print("✅ Successfully committed changes")
    print(f"   {stdout}")

    # Optional: Show what was committed
    returncode, stdout, _ = run_git_command(
        ["git", "log", "-1", "--oneline"], repo_path
    )
    if returncode == 0:
        print(f"   Latest commit: {stdout}")

    return True


def main() -> int:
    """Main entry point for the hook."""
    # Check if auto-commit is enabled
    auto_commit_enabled = os.environ.get("CLAUDE_AUTO_COMMIT", "true").lower() == "true"

    if not auto_commit_enabled:
        print("[INFO] Auto-commit is disabled (set CLAUDE_AUTO_COMMIT=true to enable)")
        return 0

    print("\n🔄 Running auto-commit hook...")

    # Get the project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Perform auto-commit
    success = auto_commit(project_dir)

    # Return appropriate exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
