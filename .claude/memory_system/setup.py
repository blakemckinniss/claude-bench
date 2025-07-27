#!/usr/bin/env python3
"""
Setup script for Claude Code Memory System
Handles installation and configuration for new projects
"""
import json
import os
import sys
import shutil
from pathlib import Path
from typing import Union


def setup_memory_system(project_path: Union[str, os.PathLike, None] = None) -> bool:
    """Setup memory system for a project"""
    if not project_path:
        project_path = os.getcwd()

    project_path = Path(project_path)

    print(f"Setting up Claude Code Memory System for: {project_path}")

    # Create directory structure
    memory_system_path = project_path / ".claude/memory_system"
    hooks_path = project_path / ".claude/hooks"

    memory_system_path.mkdir(parents=True, exist_ok=True)
    hooks_path.mkdir(parents=True, exist_ok=True)

    # Copy memory system files
    source_dir = Path(__file__).parent

    # Copy core files
    files_to_copy = [
        ("memory_manager.py", memory_system_path),
        ("config.json", memory_system_path),
        ("requirements.txt", memory_system_path),
    ]

    for filename, dest_dir in files_to_copy:
        source_file = source_dir / filename
        dest_file = dest_dir / filename

        if source_file.exists():
            shutil.copy2(source_file, dest_file)
            print(f"  ✓ Copied {filename}")
        else:
            print(f"  ✗ Warning: {filename} not found")

    # Copy hook files
    hook_files = ["memory_store_hook.py", "memory_retrieve_hook.py"]

    source_hooks_dir = source_dir.parent / "hooks"
    for hook_file in hook_files:
        source_hook = source_hooks_dir / hook_file
        dest_hook = hooks_path / hook_file

        if source_hook.exists():
            shutil.copy2(source_hook, dest_hook)
            # Make executable
            dest_hook.chmod(dest_hook.stat().st_mode | 0o111)
            print(f"  ✓ Copied hook: {hook_file}")
        else:
            print(f"  ✗ Warning: Hook {hook_file} not found")

    # Update settings.json
    settings_file = project_path / ".claude/settings.json"

    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)
    else:
        settings = {
            "cleanupPeriodDays": 30,
            "includeCoAuthoredBy": False,
            "enableAllProjectMcpServers": True,
            "hooks": {},
        }

    # Add memory hooks to settings
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Add UserPromptSubmit hook
    if "UserPromptSubmit" not in settings["hooks"]:
        settings["hooks"]["UserPromptSubmit"] = []

    # Check if memory retrieve hook already exists
    memory_retrieve_exists = False
    for hook_group in settings["hooks"]["UserPromptSubmit"]:
        if "hooks" in hook_group:
            for hook in hook_group["hooks"]:
                if "memory_retrieve_hook.py" in hook.get("command", ""):
                    memory_retrieve_exists = True
                    break

    if not memory_retrieve_exists:
        # Add to existing or create new hook group
        if settings["hooks"]["UserPromptSubmit"]:
            settings["hooks"]["UserPromptSubmit"][0]["hooks"].append(
                {
                    "type": "command",
                    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory_retrieve_hook.py",
                }
            )
        else:
            settings["hooks"]["UserPromptSubmit"].append(
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory_retrieve_hook.py",
                        }
                    ]
                }
            )

    # Add PostToolUse hook
    if "PostToolUse" not in settings["hooks"]:
        settings["hooks"]["PostToolUse"] = []

    # Check if memory store hook already exists
    memory_store_exists = False
    for hook_group in settings["hooks"]["PostToolUse"]:
        if "hooks" in hook_group:
            for hook in hook_group["hooks"]:
                if "memory_store_hook.py" in hook.get("command", ""):
                    memory_store_exists = True
                    break

    if not memory_store_exists:
        # Find or create the * matcher group
        wildcard_group_index = None
        for i, hook_group in enumerate(settings["hooks"]["PostToolUse"]):
            if hook_group.get("matcher") == "*":
                wildcard_group_index = i
                break

        if wildcard_group_index is not None:
            settings["hooks"]["PostToolUse"][wildcard_group_index]["hooks"].append(
                {
                    "type": "command",
                    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory_store_hook.py",
                }
            )
        else:
            settings["hooks"]["PostToolUse"].append(
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memory_store_hook.py",
                        }
                    ],
                }
            )

    # Write updated settings
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print("  ✓ Updated settings.json")

    # Install Python dependencies
    print("\nInstalling Python dependencies...")
    requirements_file = memory_system_path / "requirements.txt"

    if requirements_file.exists():
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--break-system-packages",
                "-r",
                str(requirements_file),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("  ✓ Dependencies installed")
        else:
            print("  ✗ Warning: Failed to install some dependencies")
            print(f"    Error: {result.stderr}")
            print("    You may need to install them manually with:")
            print(f"    pip install --break-system-packages -r {requirements_file}")

    print("\n✅ Memory system setup complete!")
    print("\nThe memory system will now:")
    print("  • Automatically store relevant code patterns and solutions")
    print("  • Provide context-aware suggestions based on project history")
    print("  • Keep memories isolated per project")
    print("\nTo customize behavior, edit: .claude/memory_system/config.json")

    return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Setup Claude Code Memory System")
    parser.add_argument(
        "--project-path",
        default=os.getcwd(),
        help="Path to project (default: current directory)",
    )

    args = parser.parse_args()

    success = setup_memory_system(args.project_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
