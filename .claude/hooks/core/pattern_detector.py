#!/usr/bin/env python3
"""
Advanced Pattern Detection for Claude Code Hooks
Detects complex patterns and workflows that could be optimized
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any


class WorkflowType(Enum):
    """Common workflow patterns"""

    READ_MODIFY_WRITE = "read_modify_write"
    SEARCH_READ_EDIT = "search_read_edit"
    STATUS_DIFF_COMMIT = "status_diff_commit"
    FIND_REPLACE_ALL = "find_replace_all"
    DEBUG_TRACE_FIX = "debug_trace_fix"
    REVIEW_ANALYZE_SUGGEST = "review_analyze_suggest"
    TEST_RUN_FIX = "test_run_fix"


@dataclass
class WorkflowPattern:
    """Represents a detected workflow pattern"""

    type: WorkflowType
    steps: list[tuple[str, dict[str, Any], float]]
    timestamp: float
    optimization_suggestion: str


@dataclass
class BatchableOperation:
    """Represents operations that could be batched"""

    tool_name: str
    operations: list[dict[str, Any]]
    suggestion: str
    estimated_speedup: float  # Multiplier (e.g., 5.0 = 5x faster)


class PatternDetector:
    """Detects complex patterns in tool usage"""

    def __init__(self) -> None:
        self.operation_buffer: list[tuple[str, dict[str, Any], float]] = []
        self.max_buffer_size = 50

    def add_operation(
        self, tool_name: str, tool_input: dict[str, Any], timestamp: float
    ) -> None:
        """Add operation to buffer for pattern detection"""
        self.operation_buffer.append((tool_name, tool_input, timestamp))

        # Keep buffer size manageable
        if len(self.operation_buffer) > self.max_buffer_size:
            self.operation_buffer.pop(0)

    def detect_workflows(self) -> list[WorkflowPattern]:
        """Detect workflow patterns in recent operations"""
        workflows = []

        # Check for read-modify-write pattern
        rmw = self._detect_read_modify_write()
        if rmw:
            workflows.append(rmw)

        # Check for search-read-edit pattern
        sre = self._detect_search_read_edit()
        if sre:
            workflows.append(sre)

        # Check for git workflow
        git = self._detect_git_workflow()
        if git:
            workflows.append(git)

        # Check for debugging workflow
        debug = self._detect_debug_workflow()
        if debug:
            workflows.append(debug)

        return workflows

    def detect_batchable_operations(self) -> list[BatchableOperation]:
        """Detect operations that could be batched"""
        batchable = []

        # Group operations by tool
        tool_groups = defaultdict(list)
        for op in self.operation_buffer[-20:]:  # Look at last 20 operations
            tool_name, tool_input, timestamp = op
            tool_groups[tool_name].append((tool_input, timestamp))

        # Check Read operations
        if "Read" in tool_groups and len(tool_groups["Read"]) >= 2:
            files = [op[0].get("file_path", "") for op in tool_groups["Read"]]
            batchable.append(
                BatchableOperation(
                    tool_name="Read",
                    operations=[op[0] for op in tool_groups["Read"]],
                    suggestion=(
                        f"Batch read {len(files)} files with "
                        f"read_multiple_files: {files[:3]}..."
                    ),
                    estimated_speedup=len(files)
                    * 0.8,  # Not quite linear due to overhead
                )
            )

        # Check find_symbol operations
        if "find_symbol" in tool_groups and len(tool_groups["find_symbol"]) >= 2:
            symbols = [op[0].get("name_path", "") for op in tool_groups["find_symbol"]]
            batchable.append(
                BatchableOperation(
                    tool_name="find_symbol",
                    operations=[op[0] for op in tool_groups["find_symbol"]],
                    suggestion=f"Send {len(symbols)} find_symbol calls in parallel",
                    estimated_speedup=len(symbols) * 0.9,
                )
            )

        # Check Bash operations
        bash_ops = tool_groups.get("Bash", [])
        git_commands = [op for op in bash_ops if "git" in op[0].get("command", "")]
        if len(git_commands) >= 2:
            batchable.append(
                BatchableOperation(
                    tool_name="Bash",
                    operations=[op[0] for op in git_commands],
                    suggestion="Run git commands in parallel instead of sequentially",
                    estimated_speedup=len(git_commands) * 0.95,
                )
            )

        return batchable

    def _detect_read_modify_write(self) -> WorkflowPattern | None:
        """Detect read → modify → write pattern"""
        if len(self.operation_buffer) < 3:
            return None

        # Look for pattern in last 10 operations
        for i in range(
            max(0, len(self.operation_buffer) - 10), len(self.operation_buffer) - 2
        ):
            op1, op2, op3 = self.operation_buffer[i : i + 3]

            # Check if it's a read-modify-write sequence
            if (
                op1[0] == "Read"
                and op3[0] == "Write"
                and op1[1].get("file_path") == op3[1].get("file_path")
            ):

                return WorkflowPattern(
                    type=WorkflowType.READ_MODIFY_WRITE,
                    steps=[op1, op2, op3],
                    timestamp=op3[2],
                    optimization_suggestion=(
                        f"Use Edit or MultiEdit instead of Read→Modify→Write "
                        f"for {op1[1].get('file_path')}. "
                        "For code files, use Serena's replace_symbol_body or "
                        "replace_regex."
                    ),
                )
        return None

    def _detect_search_read_edit(self) -> WorkflowPattern | None:
        """Detect search → read → edit pattern"""
        # Look for search followed by reads
        search_indices = [
            i
            for i, op in enumerate(self.operation_buffer)
            if op[0] in ("search_for_pattern", "Grep", "find_symbol")
        ]

        for idx in search_indices:
            if idx + 2 < len(self.operation_buffer):
                following_ops = self.operation_buffer[idx : idx + 5]
                read_ops = [op for op in following_ops if op[0] == "Read"]

                if len(read_ops) >= 2:
                    return WorkflowPattern(
                        type=WorkflowType.SEARCH_READ_EDIT,
                        steps=following_ops[:3],
                        timestamp=following_ops[-1][2],
                        optimization_suggestion=(
                            "Consider using Task(subagent_type='general-purpose') "
                            "for complex searches. Or use Serena's find_symbol with "
                            "include_body=True to avoid separate reads."
                        ),
                    )
        return None

    def _detect_git_workflow(self) -> WorkflowPattern | None:
        """Detect git status → diff → commit pattern"""
        git_ops = [
            (i, op)
            for i, op in enumerate(self.operation_buffer)
            if op[0] == "Bash" and "git" in op[1].get("command", "")
        ]

        if len(git_ops) >= 2:
            # Check if they're sequential
            for i in range(len(git_ops) - 1):
                if git_ops[i + 1][0] - git_ops[i][0] == 1:  # Sequential indices
                    return WorkflowPattern(
                        type=WorkflowType.STATUS_DIFF_COMMIT,
                        steps=[op[1] for op in git_ops],
                        timestamp=git_ops[-1][1][2],
                        optimization_suggestion=(
                            "Run all git commands in parallel! Send git status, "
                            "git diff, and git log in a single message with multiple "
                            "tool calls."
                        ),
                    )
        return None

    def _detect_debug_workflow(self) -> WorkflowPattern | None:
        """Detect debugging workflow pattern"""
        # Look for error/log reading followed by code searches
        log_reads = [
            (i, op)
            for i, op in enumerate(self.operation_buffer)
            if (
                op[0] == "Read"
                and any(
                    keyword in op[1].get("file_path", "").lower()
                    for keyword in ["log", "error", "trace", "debug"]
                )
            )
        ]

        for idx, _ in log_reads:
            # Check following operations for code searches
            following = self.operation_buffer[idx : idx + 5]
            if any(op[0] in ("find_symbol", "search_for_pattern") for op in following):
                return WorkflowPattern(
                    type=WorkflowType.DEBUG_TRACE_FIX,
                    steps=following[:3],
                    timestamp=following[-1][2],
                    optimization_suggestion=(
                        "Consider using Task(subagent_type='debugger') for "
                        "complex debugging. The debugger agent can analyze logs "
                        "and trace issues more efficiently."
                    ),
                )
        return None


class SmartSuggestions:
    """Generate smart, context-aware suggestions"""

    @staticmethod
    def suggest_parallel_operations(
        operations: list[tuple[str, dict[str, Any]]],
    ) -> str:
        """Suggest how to parallelize operations"""
        tool_counts: dict[str, int] = defaultdict(int)
        for op in operations:
            tool_counts[op[0]] += 1

        if tool_counts["Read"] >= 2:
            return (
                f"🚀 Parallelize {tool_counts['Read']} Read operations! "
                "Use read_multiple_files or send multiple Read calls in one message."
            )
        elif tool_counts["Bash"] >= 2:
            return (
                f"🚀 Run {tool_counts['Bash']} Bash commands in parallel! "
                "Send all commands in a single message with multiple tool calls."
            )
        elif tool_counts["find_symbol"] >= 2:
            return (
                f"🚀 Batch {tool_counts['find_symbol']} symbol searches! "
                "Send all find_symbol calls in one message for parallel execution."
            )
        else:
            return "🚀 These operations can run in parallel - send them in one message!"

    @staticmethod
    def suggest_task_agent(context: str) -> tuple[str, str] | None:
        """Suggest appropriate task agent based on context"""
        context_lower = context.lower()

        # Mapping of keywords to agents
        agent_map = [
            (
                r"\b(debug|error|exception|trace|crash)\b",
                "debugger",
                "Use Task(subagent_type='debugger') for efficient debugging",
            ),
            (
                r"\b(review|audit|quality|smell)\b.*\b(code|function|class)\b",
                "code-reviewer",
                "Use Task(subagent_type='code-reviewer') for code quality analysis",
            ),
            (
                r"\b(security|vulnerability|injection|auth)\b",
                "security-auditor",
                "Use Task(subagent_type='security-auditor') for security analysis",
            ),
            (
                r"\b(slow|performance|optimize|profile)\b",
                "performance-engineer",
                "Use Task(subagent_type='performance-engineer') for performance issues",
            ),
            (
                r"\b(refactor|modernize|migrate|legacy)\b",
                "legacy-modernizer",
                "Use Task(subagent_type='legacy-modernizer') for code modernization",
            ),
            (
                r"\b(test|coverage|unit|integration)\b",
                "test-automator",
                "Use Task(subagent_type='test-automator') for test generation",
            ),
            (
                r"\b(find|search|locate)\s+(all|every|throughout)\b",
                "general-purpose",
                "Use Task(subagent_type='general-purpose') for extensive searches",
            ),
        ]

        for pattern, agent, suggestion in agent_map:
            if re.search(pattern, context_lower):
                return agent, suggestion

        return None

    @staticmethod
    def estimate_time_saved(batchable: list[BatchableOperation]) -> str:
        """Estimate time saved by batching operations"""
        total_speedup = sum(op.estimated_speedup for op in batchable)

        if total_speedup > 10:
            return (
                f"⚡ Potential {total_speedup:.1f}x speedup by batching "
                "these operations!"
            )
        elif total_speedup > 5:
            return (
                f"🚀 Save significant time: {total_speedup:.1f}x faster with batching!"
            )
        elif total_speedup > 2:
            return f"⏱️ {total_speedup:.1f}x faster by running these in parallel!"
        else:
            return "💡 Small performance gain possible through batching"
