#!/usr/bin/env python3
"""
Python Tools Hook for Claude Code
Validates Python files POST modification only - allows changes but enforces
quality after modifications are made
"""

import json
import os
import subprocess
import sys
from typing import Any


class PythonToolsManager:
    """Manages Python linting and formatting tools"""

    def __init__(self) -> None:
        self.tools = {
            "pyupgrade": {
                "description": "Automatically upgrade syntax for newer Python versions",
                "hook_type": "pre_write",
                "command": ["pyupgrade", "--py38-plus"],
                "file_extensions": [".py"],
            },
            "autoflake": {
                "description": "Remove unused imports and variables",
                "hook_type": "pre_write",
                "command": [
                    "autoflake",
                    "--remove-all-unused-imports",
                    "--remove-unused-variables",
                    "--in-place",
                ],
                "file_extensions": [".py"],
            },
            "black": {
                "description": "Format Python code",
                "hook_type": "pre_write",
                "command": ["black", "--quiet"],
                "file_extensions": [".py"],
            },
            "ruff": {
                "description": "Fast Python linter",
                "hook_type": "post_write",
                "command": ["ruff", "check", "--fix"],
                "file_extensions": [".py"],
            },
            "refurb": {
                "description": "Modern Python idioms checker",
                "hook_type": "post_write",
                "command": ["refurb"],
                "file_extensions": [".py"],
            },
        }

    def is_python_file(self, file_path: str) -> bool:
        """Check if file is a Python file"""
        return file_path.endswith(".py")

    def tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available in the system"""
        try:
            subprocess.run(
                [tool_name, "--version"], capture_output=True, check=False, timeout=5
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_available_tools(self) -> list[str]:
        """Get list of available Python tools"""
        available = []
        for tool_name in self.tools:
            if self.tool_available(tool_name):
                available.append(tool_name)
        return available


def detect_python_operation(
    tool_name: str, tool_input: dict[str, Any]
) -> tuple[str, str] | None:
    """Detect Python file operations"""
    file_path = None
    operation = None

    if tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path")
        operation = "write"
    elif tool_name == "mcp__filesystem__write_file":
        file_path = tool_input.get("path")
        operation = "write"
    elif tool_name == "mcp__filesystem__edit_file":
        file_path = tool_input.get("path")
        operation = "edit"
    elif tool_name == "mcp__serena__replace_symbol_body" or tool_name in [
        "mcp__serena__insert_after_symbol",
        "mcp__serena__insert_before_symbol",
    ]:
        file_path = tool_input.get("relative_path")
        operation = "edit"

    if file_path and operation and file_path.endswith(".py"):
        return file_path, operation

    return None


def check_pylance_issues(file_path: str) -> list[str]:
    """Check for Pylance/type issues using mypy or pyright"""
    issues = []

    # Try pyright first (what Pylance uses)
    try:
        result = subprocess.run(
            ["pyright", "--outputformat", "json", file_path],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                diagnostics = data.get("generalDiagnostics", [])
                for diag in diagnostics:
                    severity = diag.get("severity", "error")
                    message = diag.get("message", "")
                    line = diag.get("range", {}).get("start", {}).get("line", 0) + 1
                    if severity in ["error", "warning"]:
                        issues.append(f"Line {line}: {message} [{severity}]")
            except json.JSONDecodeError:
                pass

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback to mypy
        try:
            result = subprocess.run(
                ["mypy", "--show-error-codes", "--no-error-summary", file_path],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip() and ":" in line:
                        issues.append(line.strip())

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return issues


def main() -> None:
    """Main hook handler - POST validation only with exit code 2 on issues"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"❌ HOOK ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Skip PreToolUse - let operations proceed
    if hook_event == "PreToolUse":
        sys.exit(0)

    # Only validate on PostToolUse
    if hook_event == "PostToolUse":
        python_manager = PythonToolsManager()
        critical_issues = []

        # Detect Python file operations
        python_op = detect_python_operation(tool_name, tool_input)

        if python_op:
            file_path, operation = python_op

            # Skip test files (files starting with test_)
            base_name = os.path.basename(file_path)
            if base_name.startswith("test_"):
                print(
                    f"⏭️  Skipping validation for test file: {file_path}",
                    file=sys.stderr,
                )
                sys.exit(0)

            print("=" * 60, file=sys.stderr)
            print("🐍 POST-MODIFICATION PYTHON VALIDATION", file=sys.stderr)
            print(f"📁 File: {file_path}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)

            if os.path.exists(file_path):
                # Run type checking
                print("🔍 Running type checking...", file=sys.stderr)
                type_issues = check_pylance_issues(file_path)

                if type_issues:
                    print("🚨 TYPE CHECKING ERRORS FOUND:", file=sys.stderr)
                    for issue in type_issues:
                        print(f"   ❌ {issue}", file=sys.stderr)
                    print("🚨 THESE ISSUES MUST BE FIXED!", file=sys.stderr)
                    critical_issues.extend(type_issues)
                else:
                    print("✅ No type checking issues found", file=sys.stderr)

                # Run linting tools
                available = python_manager.get_available_tools()
                if available:
                    print("🔧 Running Python tools validation...", file=sys.stderr)

                    # Run ruff check
                    if "ruff" in available:
                        try:
                            result = subprocess.run(
                                ["ruff", "check", file_path],
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )

                            if result.returncode != 0:
                                print("🚨 RUFF LINTING ERRORS:", file=sys.stderr)
                                if result.stdout:
                                    for line in result.stdout.strip().split("\n"):
                                        if line.strip():
                                            print(f"   ❌ {line}", file=sys.stderr)
                                critical_issues.append("Ruff linting failures")
                            else:
                                print("✅ Ruff: No issues", file=sys.stderr)

                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            print("⚠️  Could not run ruff check", file=sys.stderr)

                    # Check if black would make changes
                    if "black" in available:
                        try:
                            result = subprocess.run(
                                ["black", "--check", "--quiet", file_path],
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )

                            if result.returncode != 0:
                                print("⚠️  BLACK FORMATTING WARNING:", file=sys.stderr)
                                print(
                                    "   ⚠️  File could be better formatted",
                                    file=sys.stderr,
                                )
                                print(f"   💡 Run: black {file_path}", file=sys.stderr)
                                # Don't add to critical issues - formatting is a warning
                            else:
                                print("✅ Black: Properly formatted", file=sys.stderr)

                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            print("⚠️  Could not run black check", file=sys.stderr)

                else:
                    print(
                        "⚠️  No Python tools available for validation", file=sys.stderr
                    )

            print("=" * 60, file=sys.stderr)

            # Exit with code 2 if there are critical issues
            if critical_issues:
                print("🛑 PYTHON QUALITY ISSUES DETECTED! 🛑", file=sys.stderr)
                print(
                    "The operation completed, but issues were found:", file=sys.stderr
                )
                for issue in critical_issues[:10]:
                    print(f"   🚨 {issue}", file=sys.stderr)

                if len(critical_issues) > 10:
                    print(
                        f"   ... and {len(critical_issues) - 10} more issues",
                        file=sys.stderr,
                    )

                print("🛑 YOU MUST FIX THESE ISSUES! 🛑", file=sys.stderr)
                sys.exit(2)  # Exit 2 to signal issues

    # No issues or not a Python operation
    sys.exit(0)


if __name__ == "__main__":
    main()
