#!/usr/bin/env python3
"""
Claude Code Hook: Enforce CLAUDE.md guidelines (Optimized Version)
This hook validates tool usage against performance optimization guidelines.
Performance improvements:
- Pre-compiled regex patterns
- Early exit optimizations
- Caching for repeated validations
- Batch detection logic
"""

import json
import re
import sys
import os
from typing import Dict, List, Tuple, Any
from functools import lru_cache
from collections import defaultdict
import time


# Pre-compile all regex patterns for better performance
class CompiledPatterns:
    """Pre-compiled regex patterns to avoid compilation overhead"""

    # Bash command patterns
    GREP_RECURSIVE = re.compile(r"\bgrep\s+-r\b")
    GREP_STANDALONE = re.compile(r"\bgrep\b(?!.*\|)")
    FIND_NAME = re.compile(r"\bfind\s+.*-name\b")
    FIND_TYPE_F = re.compile(r"\bfind\s+.*-type\s+f\b")
    CAT_CODE_FILES = re.compile(r"\bcat\s+\S+\.(?:py|js|ts|java|cpp|go|rs)\b")
    JSON_CHAIN = re.compile(r"cat\s+\S+\.json\s*\|\s*(?:grep|sed|awk)")
    JSON_PARSE = re.compile(r"(?:sed|awk).*\.json")

    # Tool usage patterns
    CODE_FILE_PATTERN = re.compile(r"\.(?:py|js|ts|java|cpp|go|rs)$")

    # Complex task patterns
    SEARCH_ALL = re.compile(r"(?i)(search|find|locate)\s+(all|every|throughout)")
    CODE_REVIEW = re.compile(r"(?i)(review|audit|analyze)\s+.*code")
    DEBUG_FIX = re.compile(r"(?i)(debug|fix|troubleshoot)\s+.*error")
    OPTIMIZE_PERF = re.compile(r"(?i)(optimize|improve)\s+.*performance")
    REFACTOR = re.compile(r"(?i)(refactor|modernize|migrate)")

    # Batch operation patterns
    SEQUENTIAL_READS = re.compile(
        r"(?i)(read|check|view|open)\s+(multiple|several|all)"
    )
    GIT_CHAIN = re.compile(r"&&.*git\s+(status|diff|log)")


# Optimized rule sets using pre-compiled patterns
BASH_RULES_OPTIMIZED = [
    (
        CompiledPatterns.GREP_RECURSIVE,
        "Use 'rg' (ripgrep) instead of 'grep -r' for recursive search - it's 10-100x faster",
    ),
    (
        CompiledPatterns.GREP_STANDALONE,
        "Use 'rg' (ripgrep) instead of 'grep' for better performance. If you need grep in a pipeline, that's OK.",
    ),
    (
        CompiledPatterns.FIND_NAME,
        "Use 'fd' instead of 'find -name' for faster file discovery",
    ),
    (
        CompiledPatterns.FIND_TYPE_F,
        "Use 'fd -t f' instead of 'find -type f' for faster file discovery",
    ),
    (
        CompiledPatterns.CAT_CODE_FILES,
        "Use 'bat' instead of 'cat' for syntax-highlighted code viewing",
    ),
    (
        CompiledPatterns.JSON_CHAIN,
        "Use 'jq' for JSON processing instead of sed/awk/grep chains",
    ),
    (
        CompiledPatterns.JSON_PARSE,
        "Use 'jq' for JSON processing - it's cleaner and more reliable",
    ),
]


# Session state for tracking patterns
class SessionState:
    """Track session state for better pattern detection"""

    def __init__(self):
        self.recent_tools: List[Tuple[str, Dict[str, Any], float]] = []
        self.file_access_count = defaultdict(int)
        self.similar_operations = defaultdict(list)
        self.last_git_command_time = 0

    def add_tool_use(self, tool_name: str, tool_input: Dict[str, Any]):
        """Track tool usage for pattern detection"""
        timestamp = time.time()
        self.recent_tools.append((tool_name, tool_input, timestamp))

        # Keep only last 20 operations
        if len(self.recent_tools) > 20:
            self.recent_tools.pop(0)

        # Track file access
        if tool_name == "Read" and "file_path" in tool_input:
            self.file_access_count[tool_input["file_path"]] += 1

    def detect_batch_opportunities(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> List[str]:
        """Detect missed batching opportunities"""
        suggestions = []
        current_time = time.time()

        # Check for multiple Read operations that could be batched
        if tool_name == "Read":
            recent_reads = [
                (t[1].get("file_path"), t[2])
                for t in self.recent_tools[-5:]
                if t[0] == "Read" and current_time - t[2] < 30
            ]
            if len(recent_reads) >= 2:
                suggestions.append(
                    f"Consider using read_multiple_files - you've read {len(recent_reads)} files recently. "
                    f"Batch reading is much faster!"
                )

        # Check for sequential git commands
        if tool_name == "Bash" and "git" in tool_input.get("command", ""):
            if current_time - self.last_git_command_time < 5:
                suggestions.append(
                    "Run git commands in parallel! Send multiple Bash calls in one message "
                    "instead of waiting for each result."
                )
            self.last_git_command_time = current_time

        # Check for repeated find_symbol calls
        recent_symbols = [
            t
            for t in self.recent_tools[-5:]
            if t[0] == "find_symbol" and current_time - t[2] < 30
        ]
        if len(recent_symbols) >= 2:
            suggestions.append(
                "Batch find_symbol calls! Send multiple symbol searches in one message "
                "for parallel execution."
            )

        return suggestions


# Global session state (would be better with proper state management)
session_state = SessionState()


@lru_cache(maxsize=128)
def validate_bash_command_cached(command: str) -> Tuple[bool, List[str]]:
    """Cached validation of bash commands"""
    issues = []

    # Skip if using explicit path to tool
    if command.startswith(("/usr/bin/grep", "/bin/grep")):
        return True, issues

    # Check each pattern - early exit on first match for blocking rules
    for pattern, message in BASH_RULES_OPTIMIZED:
        if pattern.search(command):
            issues.append(message)
            # For critical issues, return immediately
            if "grep" in message or "jq" in message:
                return False, issues

    # Check for sequential operations
    if CompiledPatterns.GIT_CHAIN.search(command):
        issues.append(
            "Run git commands in parallel using multiple Bash tool calls instead of chaining with &&"
        )

    return len(issues) == 0, issues


def check_tool_usage_optimized(
    tool_name: str, tool_input: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Optimized tool usage checking with early exits"""

    # Fast path for blocked tools
    if tool_name in ("WebSearch", "WebFetch"):
        if tool_name == "WebSearch":
            return False, [
                "WebSearch is BLOCKED. Use mcp__tavily-remote__tavily_search instead"
            ]
        else:
            return False, [
                "WebFetch is BLOCKED. Use mcp__tavily-remote__tavily_extract instead"
            ]

    reminders = []

    # Check Read tool usage for code files
    if tool_name == "Read" and "file_path" in tool_input:
        if CompiledPatterns.CODE_FILE_PATTERN.search(tool_input["file_path"]):
            reminders.append(
                "Consider using Serena's find_symbol or get_symbols_overview for code files instead of Read"
            )

    # Detect batch opportunities
    batch_suggestions = session_state.detect_batch_opportunities(tool_name, tool_input)
    reminders.extend(batch_suggestions)

    return len(reminders) == 0, reminders


def check_complex_tasks_optimized(tool_input: Dict[str, Any]) -> List[str]:
    """Optimized complex task detection"""
    suggestions = []

    # Combine text fields for single pass checking
    text_content = " ".join(
        filter(
            None,
            [
                tool_input.get("command", ""),
                tool_input.get("description", ""),
                tool_input.get("prompt", ""),
            ],
        )
    )

    if not text_content:
        return suggestions

    # Check patterns with early exit
    pattern_checks = [
        (
            CompiledPatterns.SEARCH_ALL,
            "Consider using Task with general-purpose agent for extensive searches",
        ),
        (
            CompiledPatterns.CODE_REVIEW,
            "Consider using Task with code-reviewer or security-auditor agent",
        ),
        (CompiledPatterns.DEBUG_FIX, "Consider using Task with debugger agent"),
        (
            CompiledPatterns.OPTIMIZE_PERF,
            "Consider using Task with performance-engineer agent",
        ),
        (CompiledPatterns.REFACTOR, "Consider using Task with legacy-modernizer agent"),
    ]

    for pattern, suggestion in pattern_checks:
        if pattern.search(text_content):
            suggestions.append(suggestion)
            # Only suggest one task agent at a time
            break

    return suggestions


def write_state_to_file(state_data: Dict[str, Any]):
    """Write state to shared file for inter-hook communication"""
    state_file = "/tmp/claude_hook_state.json"
    try:
        with open(state_file, "w") as f:
            json.dump(state_data, f)
    except (OSError, ValueError):
        pass  # Fail silently


def read_state_from_file() -> Dict[str, Any]:
    """Read shared state from file"""
    state_file = "/tmp/claude_hook_state.json"
    try:
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def main():
    """Main hook handler with performance optimizations"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Track tool usage
    session_state.add_tool_use(tool_name, tool_input)

    all_issues = []
    should_block = False

    if hook_event == "PreToolUse":
        # Validate Bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if command:
                valid, issues = validate_bash_command_cached(command)
                all_issues.extend(issues)
                if not valid:
                    should_block = True

        # Check tool usage patterns
        valid, tool_issues = check_tool_usage_optimized(tool_name, tool_input)
        all_issues.extend(tool_issues)
        if not valid:
            should_block = True

        # Check for complex tasks (skip if already using Task)
        if tool_name != "Task":
            complex_suggestions = check_complex_tasks_optimized(tool_input)
            all_issues.extend(complex_suggestions)

        # Write state for other hooks
        state_data = {
            "recent_tools": [(t[0], t[2]) for t in session_state.recent_tools[-10:]],
            "file_access_count": dict(session_state.file_access_count),
            "timestamp": time.time(),
        }
        write_state_to_file(state_data)

        # Handle blocking
        if should_block:
            for issue in all_issues:
                print(f"❌ {issue}", file=sys.stderr)
            sys.exit(2)

        # Provide feedback without blocking
        if all_issues:
            print("⚡ Performance Optimization Suggestions:", file=sys.stderr)
            for issue in all_issues:
                print(f"• {issue}", file=sys.stderr)
            print("\nRefer to CLAUDE.md for more details.", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
