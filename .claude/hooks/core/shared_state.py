#!/usr/bin/env python3
"""
Shared State Manager for Claude Code Hooks
Provides inter-hook communication and state persistence
"""

import fcntl
import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


class HookStateManager:
    """Thread-safe shared state manager for hooks"""

    STATE_FILE = "/tmp/claude_hook_shared_state.json"
    LOCK_FILE = "/tmp/claude_hook_state.lock"

    def __init__(self) -> None:
        self.state_file = Path(self.STATE_FILE)
        self.lock_file = Path(self.LOCK_FILE)
        self._ensure_files_exist()

    def _ensure_files_exist(self) -> None:
        """Ensure state files exist"""
        if not self.state_file.exists():
            self.state_file.write_text("{}")
        if not self.lock_file.exists():
            self.lock_file.touch()

    def _acquire_lock(self, timeout: float = 1.0) -> int | None:
        """Acquire file lock for thread-safe operations"""
        lock_fd = os.open(str(self.lock_file), os.O_RDWR)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_fd
            except BlockingIOError:
                time.sleep(0.01)

        os.close(lock_fd)
        return None

    def _release_lock(self, lock_fd: int) -> None:
        """Release file lock"""
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

    def read_state(self) -> dict[str, Any]:
        """Read current state with locking"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return {}

        try:
            with open(self.state_file) as f:
                state: dict[str, Any] = json.load(f)
                return state
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        finally:
            self._release_lock(lock_fd)

    def write_state(self, state: dict[str, Any]) -> None:
        """Write state with locking"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return

        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        finally:
            self._release_lock(lock_fd)

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update specific fields in state"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return

        try:
            # Read current state
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                state = {}

            # Apply updates
            state.update(updates)
            state["last_updated"] = time.time()

            # Write back
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        finally:
            self._release_lock(lock_fd)


class SessionTracker:
    """Track session-specific patterns and metrics"""

    def __init__(self) -> None:
        self.state_manager = HookStateManager()

    def add_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        execution_time: float | None = None,
    ) -> None:
        """Track tool execution"""
        state = self.state_manager.read_state()

        # Initialize structures
        if "tool_executions" not in state:
            state["tool_executions"] = []
        if "tool_metrics" not in state:
            state["tool_metrics"] = {}

        # Add execution record
        execution = {
            "tool": tool_name,
            "timestamp": time.time(),
            "execution_time": execution_time,
        }

        # Store file paths for pattern detection
        if tool_name == "Read" and "file_path" in tool_input:
            execution["file_path"] = tool_input["file_path"]
        elif tool_name == "Bash" and "command" in tool_input:
            execution["command"] = tool_input["command"]

        state["tool_executions"].append(execution)

        # Keep only last 100 executions
        if len(state["tool_executions"]) > 100:
            state["tool_executions"] = state["tool_executions"][-100:]

        # Update metrics
        if tool_name not in state["tool_metrics"]:
            state["tool_metrics"][tool_name] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
            }

        metrics = state["tool_metrics"][tool_name]
        metrics["count"] += 1
        if execution_time:
            metrics["total_time"] += execution_time
            metrics["avg_time"] = metrics["total_time"] / metrics["count"]

        self.state_manager.write_state(state)

    def get_recent_operations(
        self, tool_name: str | None = None, seconds: int = 30
    ) -> list[dict[str, Any]]:
        """Get recent operations within time window"""
        state = self.state_manager.read_state()
        executions = state.get("tool_executions", [])

        current_time = time.time()
        recent = [
            ex
            for ex in executions
            if current_time - ex["timestamp"] < seconds
            and (tool_name is None or ex["tool"] == tool_name)
        ]

        return recent

    def detect_patterns(self) -> dict[str, list[str]]:
        """Detect common patterns that could be optimized"""
        patterns = defaultdict(list)

        # Check for multiple reads
        recent_reads = self.get_recent_operations("Read", seconds=30)
        if len(recent_reads) >= 2:
            files = [r.get("file_path", "unknown") for r in recent_reads]
            patterns["batch_reads"].append(
                f"Multiple Read operations detected: {files}. "
                "Use read_multiple_files for better performance!"
            )

        # Check for sequential git commands
        recent_bash = self.get_recent_operations("Bash", seconds=10)
        git_commands = [b for b in recent_bash if "git" in b.get("command", "")]
        if len(git_commands) >= 2:
            patterns["sequential_git"].append(
                "Sequential git commands detected. Run them in parallel!"
            )

        # Check for repeated searches
        recent_searches = self.get_recent_operations("search_for_pattern", seconds=60)
        if len(recent_searches) >= 3:
            patterns["repeated_searches"].append(
                "Multiple searches detected. Consider using Task with "
                "general-purpose agent."
            )

        return dict(patterns)


class PerformanceMonitor:
    """Monitor and track performance metrics"""

    def __init__(self) -> None:
        self.state_manager = HookStateManager()

    def record_validation_time(self, hook_name: str, duration: float) -> None:
        """Record hook validation time"""
        state = self.state_manager.read_state()

        if "hook_performance" not in state:
            state["hook_performance"] = {}

        if hook_name not in state["hook_performance"]:
            state["hook_performance"][hook_name] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "max_time": 0,
            }

        perf = state["hook_performance"][hook_name]
        perf["count"] += 1
        perf["total_time"] += duration
        perf["avg_time"] = perf["total_time"] / perf["count"]
        perf["max_time"] = max(perf["max_time"], duration)

        self.state_manager.write_state(state)

    def get_slow_operations(self, threshold_ms: float = 100) -> list[dict[str, Any]]:
        """Get operations that exceeded time threshold"""
        state = self.state_manager.read_state()
        slow_ops = []

        for tool_name, metrics in state.get("tool_metrics", {}).items():
            if metrics.get("avg_time", 0) * 1000 > threshold_ms:
                slow_ops.append(
                    {
                        "tool": tool_name,
                        "avg_time_ms": metrics["avg_time"] * 1000,
                        "count": metrics["count"],
                    }
                )

        return slow_ops


# Convenience functions for hooks
def track_tool_use(tool_name: str, tool_input: dict[str, Any]) -> None:
    """Quick function to track tool usage"""
    tracker = SessionTracker()
    tracker.add_tool_execution(tool_name, tool_input)


def get_optimization_suggestions() -> list[str]:
    """Get current optimization suggestions based on patterns"""
    tracker = SessionTracker()
    patterns = tracker.detect_patterns()

    suggestions = []
    for _, pattern_messages in patterns.items():
        suggestions.extend(pattern_messages)

    return suggestions


def cleanup_old_state(max_age_seconds: int = 3600) -> None:
    """Clean up old state data"""
    state_manager = HookStateManager()
    state = state_manager.read_state()

    current_time = time.time()

    # Clean old executions
    if "tool_executions" in state:
        state["tool_executions"] = [
            ex
            for ex in state["tool_executions"]
            if current_time - ex["timestamp"] < max_age_seconds
        ]

    state_manager.write_state(state)
