#!/usr/bin/env python3
"""
Python Tools Hook for Claude Code
Integrates refurb, ruff, black, pyupgrade, autoflake, and codemod for Python files
"""

import json
import sys
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple


class PythonToolsManager:
    """Manages Python linting and formatting tools"""

    def __init__(self):
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

    def get_available_tools(self) -> List[str]:
        """Get list of available Python tools"""
        available = []
        for tool_name in self.tools:
            if self.tool_available(tool_name):
                available.append(tool_name)
        return available

    def run_tool_on_file(self, tool_name: str, file_path: str) -> Tuple[bool, str]:
        """Run a specific tool on a file"""
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}"

        tool_config = self.tools[tool_name]
        command = tool_config["command"] + [file_path]

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=30, cwd=os.getcwd()
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, f"Tool {tool_name} timed out"
        except Exception as e:
            return False, f"Error running {tool_name}: {str(e)}"

    def suggest_python_tools(self, file_path: str, operation: str) -> List[str]:
        """Suggest appropriate Python tools based on operation"""
        if not self.is_python_file(file_path):
            return []

        suggestions = []
        available_tools = self.get_available_tools()

        if operation in ["write", "edit", "create"]:
            # Pre-write tools (formatting and cleanup)
            pre_write_tools = [
                tool
                for tool in available_tools
                if self.tools[tool]["hook_type"] == "pre_write"
            ]
            if pre_write_tools:
                tools_list = ", ".join(pre_write_tools)
                suggestions.append(
                    f"🐍 Python file detected! Consider running formatting tools: {tools_list}"
                )

            # Post-write tools (linting)
            post_write_tools = [
                tool
                for tool in available_tools
                if self.tools[tool]["hook_type"] == "post_write"
            ]
            if post_write_tools:
                tools_list = ", ".join(post_write_tools)
                suggestions.append(f"🔍 After editing, run linting tools: {tools_list}")

        return suggestions

    def run_python_pipeline(self, file_path: str, tools: List[str]) -> Dict[str, Any]:
        """Run a pipeline of Python tools on a file"""
        results = {}

        for tool_name in tools:
            if tool_name in self.get_available_tools():
                success, output = self.run_tool_on_file(tool_name, file_path)
                results[tool_name] = {"success": success, "output": output}
            else:
                results[tool_name] = {
                    "success": False,
                    "output": f"Tool {tool_name} not available",
                }

        return results

    def format_python_file(self, file_path: str) -> Dict[str, Any]:
        """Run formatting pipeline on Python file"""
        formatting_tools = ["pyupgrade", "autoflake", "black"]
        available_formatting = [t for t in formatting_tools if self.tool_available(t)]

        if not available_formatting:
            return {"success": False, "message": "No Python formatting tools available"}

        return self.run_python_pipeline(file_path, available_formatting)

    def lint_python_file(self, file_path: str) -> Dict[str, Any]:
        """Run linting pipeline on Python file"""
        linting_tools = ["ruff", "refurb"]
        available_linting = [t for t in linting_tools if self.tool_available(t)]

        if not available_linting:
            return {"success": False, "message": "No Python linting tools available"}

        return self.run_python_pipeline(file_path, available_linting)


def detect_python_operation(
    tool_name: str, tool_input: Dict[str, Any]
) -> Optional[Tuple[str, str]]:
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
    elif tool_name == "mcp__serena__replace_symbol_body":
        file_path = tool_input.get("relative_path")
        operation = "edit"
    elif tool_name in [
        "mcp__serena__insert_after_symbol",
        "mcp__serena__insert_before_symbol",
    ]:
        file_path = tool_input.get("relative_path")
        operation = "edit"

    if file_path and operation and file_path.endswith(".py"):
        return file_path, operation

    return None


def check_pylance_issues(file_path: str) -> List[str]:
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


def main():
    """Main hook handler for Python tools - LOUD AND BLOCKING VERSION"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"❌ HOOK ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    python_manager = PythonToolsManager()
    should_block = False
    critical_issues = []

    if hook_event == "PreToolUse":
        # Detect Python file operations
        python_op = detect_python_operation(tool_name, tool_input)

        if python_op:
            file_path, operation = python_op

            # LOUD warnings about Python operations
            print("=" * 60, file=sys.stderr)
            print("🐍 PYTHON FILE OPERATION DETECTED!", file=sys.stderr)
            print(f"📁 File: {file_path}", file=sys.stderr)
            print(f"🔧 Operation: {operation}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)

            # Check available tools
            available = python_manager.get_available_tools()
            if not available:
                print("🚨 CRITICAL: NO PYTHON TOOLS AVAILABLE!", file=sys.stderr)
                print(
                    "🚨 Install immediately: pip install ruff black pyupgrade autoflake refurb mypy",
                    file=sys.stderr,
                )
                print(
                    "🚨 Code quality cannot be verified without these tools!",
                    file=sys.stderr,
                )
                should_block = True
                critical_issues.append("Missing Python development tools")
            else:
                print(f"✅ Available tools: {', '.join(available)}", file=sys.stderr)

            # Check for existing type issues if file exists
            if os.path.exists(file_path):
                print("🔍 Checking for existing type issues...", file=sys.stderr)
                type_issues = check_pylance_issues(file_path)

                if type_issues:
                    print("🚨 TYPE CHECKING ERRORS FOUND:", file=sys.stderr)
                    for issue in type_issues[:5]:  # Show first 5 issues
                        print(f"   ❌ {issue}", file=sys.stderr)

                    if len(type_issues) > 5:
                        print(
                            f"   ... and {len(type_issues) - 5} more issues",
                            file=sys.stderr,
                        )

                    print(
                        "🚨 FIX THESE TYPE ISSUES BEFORE PROCEEDING!", file=sys.stderr
                    )
                    should_block = True
                    critical_issues.extend(type_issues)
                else:
                    print("✅ No type checking issues found", file=sys.stderr)

            print("=" * 60, file=sys.stderr)

    elif hook_event == "PostToolUse":
        # AGGRESSIVELY check Python files after modification
        python_op = detect_python_operation(tool_name, tool_input)

        if python_op:
            file_path, operation = python_op

            print("=" * 60, file=sys.stderr)
            print("🐍 POST-MODIFICATION PYTHON VALIDATION", file=sys.stderr)
            print(f"📁 File: {file_path}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)

            if os.path.exists(file_path):
                # ALWAYS run type checking after modification
                print("🔍 Running mandatory type checking...", file=sys.stderr)
                type_issues = check_pylance_issues(file_path)

                if type_issues:
                    print("🚨🚨🚨 TYPE CHECKING FAILED! 🚨🚨🚨", file=sys.stderr)
                    print("The following issues were introduced:", file=sys.stderr)
                    for issue in type_issues:
                        print(f"   ❌ {issue}", file=sys.stderr)

                    print("🚨 THESE ISSUES MUST BE FIXED!", file=sys.stderr)
                    should_block = True
                    critical_issues.extend(type_issues)

                # Run linting tools and be loud about results
                available = python_manager.get_available_tools()
                if available:
                    print("🔧 Running Python tools validation...", file=sys.stderr)

                    # Run ruff check (no fix, just check)
                    if "ruff" in available:
                        try:
                            result = subprocess.run(
                                ["ruff", "check", file_path],
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )

                            if result.returncode != 0:
                                print("🚨 RUFF LINTING ISSUES:", file=sys.stderr)
                                if result.stdout:
                                    for line in result.stdout.strip().split("\n"):
                                        if line.strip():
                                            print(f"   ❌ {line}", file=sys.stderr)
                                should_block = True
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
                                print("🚨 BLACK FORMATTING ISSUES:", file=sys.stderr)
                                print(
                                    "   ❌ File is not properly formatted!",
                                    file=sys.stderr,
                                )
                                print(f"   💡 Run: black {file_path}", file=sys.stderr)
                                # Don't block on formatting, but warn loudly
                            else:
                                print("✅ Black: Properly formatted", file=sys.stderr)

                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            print("⚠️  Could not run black check", file=sys.stderr)

                if not critical_issues:
                    print("🎉 Python file validation PASSED!", file=sys.stderr)

            print("=" * 60, file=sys.stderr)

    # BLOCK if there are critical issues
    if should_block and critical_issues:
        print("🛑🛑🛑 OPERATION BLOCKED! 🛑🛑🛑", file=sys.stderr)
        print("Critical Python issues detected:", file=sys.stderr)
        for issue in critical_issues[:10]:  # Limit to first 10 to avoid spam
            print(f"   🚨 {issue}", file=sys.stderr)

        if len(critical_issues) > 10:
            print(
                f"   ... and {len(critical_issues) - 10} more issues", file=sys.stderr
            )

        print("🛑 Fix these issues before proceeding!", file=sys.stderr)
        print("🛑🛑🛑 OPERATION BLOCKED! 🛑🛑🛑", file=sys.stderr)
        sys.exit(2)  # Block the operation

    sys.exit(0)


if __name__ == "__main__":
    main()
