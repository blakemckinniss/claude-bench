#!/usr/bin/env python3
"""
Cleanup Enforcer Hook - Blocks 'stop' command if cleanup is needed
Tracks temporary files, disabled hooks, and other resources that need cleanup
"""

import json
import sys
import os
import glob
from typing import List, Dict, Any


class CleanupTracker:
    """Tracks resources that need cleanup before stopping"""

    CLEANUP_STATE_FILE = os.path.expanduser("~/.claude/cleanup_state.json")

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load cleanup state from file"""
        if os.path.exists(self.CLEANUP_STATE_FILE):
            try:
                with open(self.CLEANUP_STATE_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "temp_files": [],
            "disabled_hooks": [],
            "open_connections": [],
            "running_processes": [],
            "modified_python_files": [],
            "quality_check_done": False,
        }

    def _save_state(self):
        """Save cleanup state to file"""
        os.makedirs(os.path.dirname(self.CLEANUP_STATE_FILE), exist_ok=True)
        with open(self.CLEANUP_STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def add_temp_file(self, filepath: str):
        """Track a temporary file"""
        if filepath not in self.state["temp_files"]:
            self.state["temp_files"].append(filepath)
            self._save_state()
    
    def add_modified_python_file(self, filepath: str):
        """Track a modified Python file"""
        if filepath not in self.state["modified_python_files"] and filepath.endswith(".py"):
            self.state["modified_python_files"].append(filepath)
            self.state["quality_check_done"] = False
            self._save_state()
    
    def mark_quality_check_done(self):
        """Mark that quality checks have been run"""
        self.state["quality_check_done"] = True
        self._save_state()
    
    def clear_python_files(self):
        """Clear the list of modified Python files after quality check"""
        self.state["modified_python_files"] = []
        self.state["quality_check_done"] = True
        self._save_state()

    def remove_temp_file(self, filepath: str):
        """Remove a temporary file from tracking"""
        if filepath in self.state["temp_files"]:
            self.state["temp_files"].remove(filepath)
            self._save_state()

    def add_disabled_hook(self, hookpath: str):
        """Track a disabled hook"""
        if hookpath not in self.state["disabled_hooks"]:
            self.state["disabled_hooks"].append(hookpath)
            self._save_state()

    def remove_disabled_hook(self, hookpath: str):
        """Remove a disabled hook from tracking"""
        if hookpath in self.state["disabled_hooks"]:
            self.state["disabled_hooks"].remove(hookpath)
            self._save_state()

    def get_cleanup_needed(self) -> List[Dict[str, str]]:
        """Get list of items needing cleanup"""
        cleanup_items = []

        # Check temporary files
        for temp_file in self.state["temp_files"]:
            if os.path.exists(temp_file):
                cleanup_items.append(
                    {
                        "type": "temp_file",
                        "path": temp_file,
                        "action": f"rm {temp_file}",
                    }
                )

        # Check disabled hooks
        for hook in self.state["disabled_hooks"]:
            if os.path.exists(hook + ".disabled"):
                cleanup_items.append(
                    {
                        "type": "disabled_hook",
                        "path": hook,
                        "action": f"mv {hook}.disabled {hook}",
                    }
                )

        # Check for common temp patterns in .claude directory
        claude_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude")
        temp_patterns = [
            os.path.join(claude_dir, "test_*"),
            os.path.join(claude_dir, "temp_*"),
            os.path.join(claude_dir, "*.tmp"),
            os.path.join(claude_dir, "*.bak"),
            os.path.join(claude_dir, "*.swp"),
        ]

        for pattern in temp_patterns:
            for file in glob.glob(pattern):
                if file not in self.state["temp_files"] and os.path.isfile(file):
                    cleanup_items.append(
                        {"type": "untracked_temp", "path": file, "action": f"rm {file}"}
                    )
        
        # Check if Python files were modified and quality check not done
        if self.state["modified_python_files"] and not self.state["quality_check_done"]:
            cleanup_items.append(
                {
                    "type": "python_quality_check",
                    "path": "Python files modified",
                    "action": f"{os.environ.get('CLAUDE_PROJECT_DIR', '.')}"
                    f"/.claude/scripts/python_quality_checker.sh && "
                    f"{os.environ.get('CLAUDE_PROJECT_DIR', '.')}"
                    f"/.claude/scripts/python_quality_fixer.sh",
                }
            )

        return cleanup_items


def detect_cleanup_from_command(command: str, tracker: CleanupTracker, tool_name: str = "Bash"):
    """Detect cleanup actions from bash commands"""
    # Track temp file creation in .claude directory
    claude_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude")
    if ">" in command and claude_dir in command:
        # Extract filename from redirect
        parts = command.split(">")
        if len(parts) > 1:
            filename = parts[1].strip().split()[0]
            if claude_dir in filename:
                tracker.add_temp_file(filename)

    # Track hook disabling
    if "mv" in command and ".disabled" in command:
        parts = command.split()
        for i, part in enumerate(parts):
            if (
                part.endswith(".py")
                and i + 1 < len(parts)
                and parts[i + 1].endswith(".disabled")
            ):
                tracker.add_disabled_hook(part.replace(".disabled", ""))

    # Track cleanup actions
    claude_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude")
    if "rm" in command:
        parts = command.split()
        for i, part in enumerate(parts):
            if i > 0 and claude_dir in part:
                tracker.remove_temp_file(part)

    # Track hook re-enabling
    if "mv" in command and ".disabled" in command:
        parts = command.split()
        for i, part in enumerate(parts):
            if part.endswith(".disabled") and i + 1 < len(parts):
                tracker.remove_disabled_hook(parts[i + 1])
    
    # Track quality script execution
    if "python_quality_checker.sh" in command and "python_quality_fixer.sh" in command:
        tracker.mark_quality_check_done()
    elif "python_quality_checker.sh" in command:
        # Only checker run, not fixer - still need to run fixer
        pass


def main():
    """Main hook handler"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")
    tracker = CleanupTracker()

    if hook_event == "UserPromptSubmit":
        prompt = input_data.get("prompt", "").strip().lower()

        # Check if user is trying to stop
        if prompt in ["stop", "exit", "quit", "bye", "goodbye"]:
            cleanup_needed = tracker.get_cleanup_needed()

            if cleanup_needed:
                print("🛑 CLEANUP REQUIRED BEFORE STOPPING! 🛑", file=sys.stderr)
                print("\nThe following items need cleanup:", file=sys.stderr)

                for item in cleanup_needed:
                    print(
                        f"\n• {item['type'].replace('_', ' ').title()}:",
                        file=sys.stderr,
                    )
                    print(f"  Path: {item['path']}", file=sys.stderr)
                    print(f"  Action: {item['action']}", file=sys.stderr)

                print(
                    "\n❌ Please clean up these items before stopping.", file=sys.stderr
                )
                print(
                    "💡 Tip: You can run the suggested actions above to clean up.",
                    file=sys.stderr,
                )

                # Block the stop command
                sys.exit(1)

    elif hook_event == "PreToolUse":
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Track bash commands for cleanup detection
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            detect_cleanup_from_command(command, tracker, tool_name)

        # Track file writes to .claude directory
        elif tool_name in ["Write", "mcp__filesystem__write_file"]:
            filepath = tool_input.get("file_path") or tool_input.get("path", "")
            claude_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude")
            if filepath and claude_dir in filepath and any(pattern in filepath for pattern in ["test_", "temp_", ".tmp", ".bak", ".swp"]):
                tracker.add_temp_file(filepath)
        
        # Track Python file modifications
        elif tool_name in ["Write", "Edit", "MultiEdit", "mcp__filesystem__write_file", "mcp__filesystem__edit_file"]:
            filepath = tool_input.get("file_path") or tool_input.get("path", "")
            if filepath and filepath.endswith(".py"):
                tracker.add_modified_python_file(filepath)
        
        # Track Serena operations on Python files
        elif tool_name and "serena" in tool_name and "replace" in tool_name:
            filepath = tool_input.get("relative_path", "")
            if filepath and filepath.endswith(".py"):
                project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
                full_path = os.path.join(project_dir, filepath)
                tracker.add_modified_python_file(full_path)

    # Pass through
    sys.exit(0)


if __name__ == "__main__":
    main()
