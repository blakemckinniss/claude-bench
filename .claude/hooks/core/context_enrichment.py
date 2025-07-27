#!/usr/bin/env python3
"""
Context-Aware Hook for Claude Code
Uses conversation context to provide better suggestions
"""

import json
import os
import re
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pattern_detector import PatternDetector  # type: ignore[import-not-found]
from shared_state import (  # type: ignore[import-not-found]
    HookStateManager,
    SessionTracker,
)


class ContextAnalyzer:
    """Analyzes conversation context for better suggestions"""

    def __init__(self) -> None:
        self.state_manager = HookStateManager()
        self.pattern_detector = PatternDetector()
        self.session_tracker = SessionTracker()

    def analyze_prompt_context(self, prompt: str) -> dict[str, Any]:
        """Analyze user prompt for context clues"""
        suggested_tools: list[tuple[str, str]] = []
        suggested_agents: list[tuple[str, str]] = []

        context: dict[str, Any] = {
            "intent": self._detect_intent(prompt),
            "scope": self._detect_scope(prompt),
            "urgency": self._detect_urgency(prompt),
            "keywords": self._extract_keywords(prompt),
            "suggested_tools": suggested_tools,
            "suggested_agents": suggested_agents,
        }

        # Suggest tools based on intent
        if context["intent"] == "mcp_query":
            context["suggested_tools"].append(
                (
                    "ListMcpResourcesTool",
                    "Use to list available MCP servers and resources",
                )
            )
        elif context["intent"] == "search":
            if context["scope"] == "extensive":
                context["suggested_agents"].append(
                    (
                        "general-purpose",
                        "Use Task for extensive searches to save context",
                    )
                )
            else:
                context["suggested_tools"].append(
                    (
                        "search_for_pattern",
                        "Use with context lines for efficient searching",
                    )
                )

        elif context["intent"] == "debug":
            context["suggested_agents"].append(
                (
                    "debugger",
                    'Consider Task(subagent_type="debugger") for complex debugging',
                )
            )

        elif context["intent"] == "optimize":
            context["suggested_agents"].append(
                (
                    "performance-engineer",
                    'Use Task(subagent_type="performance-engineer") for optimization',
                )
            )

        return context

    def _detect_intent(self, prompt: str) -> str:
        """Detect primary intent from prompt"""
        prompt_lower = prompt.lower()

        intent_patterns = [
            (r"\b(mcp|mcp server|servers.*access|what.*servers)\b", "mcp_query"),
            (r"\b(find|search|locate|look for)\b", "search"),
            (r"\b(debug|fix|error|bug|issue)\b", "debug"),
            (r"\b(optimize|improve|speed up|performance)\b", "optimize"),
            (r"\b(review|audit|check|analyze)\b", "review"),
            (r"\b(refactor|modernize|clean up)\b", "refactor"),
            (r"\b(test|coverage|unit test)\b", "test"),
            (r"\b(implement|add|create|build)\b", "implement"),
        ]

        for pattern, intent in intent_patterns:
            if re.search(pattern, prompt_lower):
                return intent

        return "general"

    def _detect_scope(self, prompt: str) -> str:
        """Detect scope of the task"""
        prompt_lower = prompt.lower()

        if any(
            word in prompt_lower
            for word in ["all", "every", "entire", "whole", "throughout"]
        ):
            return "extensive"
        elif any(
            word in prompt_lower
            for word in ["specific", "particular", "single", "just"]
        ):
            return "targeted"
        else:
            return "moderate"

    def _detect_urgency(self, prompt: str) -> str:
        """Detect urgency level"""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["asap", "urgent", "quickly", "fast"]):
            return "high"
        elif any(
            word in prompt_lower for word in ["when you can", "eventually", "later"]
        ):
            return "low"
        else:
            return "normal"

    def _extract_keywords(self, prompt: str) -> list[str]:
        """Extract important keywords"""
        # Remove common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        words = re.findall(r"\b\w+\b", prompt.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Prioritize technical terms
        tech_terms = [w for w in keywords if re.match(r".*\.(py|js|ts|java|cpp|go)", w)]
        return tech_terms[:5] + [w for w in keywords if w not in tech_terms][:5]

    def get_contextual_suggestions(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> list[str]:
        """Get suggestions based on context and history"""
        suggestions = []

        # Get recent operations
        recent_ops = self.session_tracker.get_recent_operations(seconds=60)

        # Check for patterns
        if tool_name == "Read":
            # Count recent reads
            recent_reads = [op for op in recent_ops if op["tool"] == "Read"]
            if len(recent_reads) >= 2:
                files = [op.get("file_path", "unknown") for op in recent_reads[-3:]]
                suggestions.append(
                    f"📚 You've read {len(recent_reads)} files recently. "
                    f"Consider batching with read_multiple_files: {files}"
                )

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            # Check for inefficient commands in context
            if "grep" in command:
                recent_greps = [
                    op
                    for op in recent_ops
                    if op["tool"] == "Bash" and "grep" in op.get("command", "")
                ]
                if len(recent_greps) >= 2:
                    suggestions.append(
                        "🔍 Multiple grep commands detected. Switch to 'rg' (ripgrep) "
                        "for 10-100x performance improvement!"
                    )

        elif tool_name == "find_symbol":
            # Check if symbols are related
            recent_symbols = [op for op in recent_ops if op["tool"] == "find_symbol"]
            if len(recent_symbols) >= 3:
                suggestions.append(
                    "🎯 Multiple symbol searches detected. Send them in parallel "
                    "or use get_symbols_overview for a broader view first."
                )

        # Get workflow-based suggestions
        workflows = self.pattern_detector.detect_workflows()
        for workflow in workflows:
            suggestions.append(f"🔄 {workflow.optimization_suggestion}")

        return suggestions


class IntelligentReminder:
    """Provides intelligent, context-aware reminders"""

    def __init__(self) -> None:
        self.context_analyzer = ContextAnalyzer()

    def generate_reminders(self, prompt: str, context: dict[str, Any]) -> list[str]:
        """Generate smart reminders based on prompt and context"""
        reminders = []

        # Base reminders on intent
        if context["intent"] == "mcp_query":
            reminders.append(
                "🔌 MCP servers: Use ListMcpResourcesTool to see all available "
                "MCP servers"
            )
        elif context["intent"] == "search":
            reminders.append(
                "🔍 Search tips: Use 'rg' for text, 'fd' for files, "
                "Task for extensive searches"
            )
        elif context["intent"] == "debug":
            reminders.append(
                "🐛 Debug efficiently: Task(subagent_type='debugger') "
                "handles complex issues"
            )
        elif context["intent"] == "optimize":
            reminders.append(
                "⚡ Always measure first! "
                "Use Task(subagent_type='performance-engineer')"
            )

        # Scope-based reminders
        if context["scope"] == "extensive":
            reminders.append(
                "🌍 Extensive operations: Delegate to Task subagents to save context"
            )
        elif context["scope"] == "targeted":
            reminders.append(
                "🎯 For specific targets: Use Serena's symbolic navigation for code"
            )

        # Add urgency-based advice
        if context["urgency"] == "high":
            reminders.append(
                "🚀 For speed: Batch operations, use parallel execution, "
                "delegate to subagents"
            )

        # Pattern-based reminders
        patterns = self.context_analyzer.pattern_detector.detect_workflows()
        if patterns:
            reminders.append(
                f"📊 Detected {patterns[0].type.value} pattern - "
                "optimize this workflow!"
            )

        return reminders


def _get_relevant_mcp_tools(context: dict[str, Any]) -> str:
    """Get the 3 most relevant MCP tools based on context"""
    intent = context.get("intent", "general")

    # Map intents to relevant MCP tools
    mcp_tool_suggestions = {
        "mcp_query": [
            "• mcp__zen__chat (use_websearch=true) - Consult Zen with web search",
            "• mcp__ListMcpResourcesTool - List all available MCP servers",
            "• mcp__ReadMcpResourceTool - Read specific MCP resources",
        ],
        "search": [
            "• mcp__zen__chat (use_websearch=true) - Zen analyzes search strategy",
            "• mcp__serena__search_for_pattern - Search code patterns",
            "• mcp__filesystem__search_files - Search files by name",
        ],
        "debug": [
            "• mcp__zen__debug - Zen manages debug investigation",
            "• mcp__serena__find_symbol - Find code symbols",
            "• mcp__ide__getDiagnostics - Get language diagnostics",
        ],
        "optimize": [
            "• mcp__zen__analyze - Zen analyzes optimization needs",
            "• mcp__ruv-swarm__benchmark_run - Run performance benchmarks",
            "• mcp__zen__refactor - Zen-guided refactoring",
        ],
        "review": [
            "• mcp__zen__codereview - Zen-managed code review",
            "• mcp__zen__secaudit - Zen security audit",
            "• mcp__github__get_pull_request_diff - Review PR changes",
        ],
        "refactor": [
            "• mcp__zen__refactor - Zen plans refactoring strategy",
            "• mcp__serena__replace_symbol_body - Replace code symbols",
            "• mcp__filesystem__move_file - Reorganize files",
        ],
        "test": [
            "• mcp__zen__testgen - Zen designs test strategy",
            "• mcp__playwright__browser_snapshot - Browser testing",
            "• mcp__ide__executeCode - Execute test code",
        ],
        "implement": [
            "• mcp__zen__chat (use_websearch=true) - Zen plans implementation",
            "• mcp__serena__insert_after_symbol - Add new code",
            "• mcp__filesystem__write_file - Create new files",
        ],
        "general": [
            "• mcp__zen__chat (use_websearch=true) - Zen as project manager",
            "• mcp__serena__get_symbols_overview - Understand code structure",
            "• mcp__filesystem__directory_tree - Explore project structure",
        ],
    }

    tools = mcp_tool_suggestions.get(intent, mcp_tool_suggestions["general"])
    return "\n".join(tools)


def main() -> None:
    """Main hook handler with context awareness"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")

    if hook_event == "UserPromptSubmit":
        prompt = input_data.get("prompt", "")

        # Check if this is a trivial request that should skip enhancement
        trivial_patterns = [
            r"^(yes|no|ok|okay|sure|alright|fine|got it|understood)\.?$",
            r"^(please do|do it|go ahead|proceed|continue|thanks|thank you)\.?$",
            r"^(yep|yeah|nope|nah|cool|great|good|perfect|exactly)\.?$",
            r"^(right|correct|indeed|absolutely)\.?$",
            r"^\d+\s*[\+\-\*/]\s*\d+\s*\??$",  # Simple math like "2 + 2?"
            r"^what is \d+\s*[\+\-\*/]\s*\d+\s*\??$",  # Simple math questions
        ]

        prompt_lower = prompt.lower().strip()
        is_trivial = any(
            re.match(pattern, prompt_lower) for pattern in trivial_patterns
        )

        # Skip enhancement for trivial requests
        if is_trivial:
            sys.exit(0)

        # Analyze context
        analyzer = ContextAnalyzer()
        context = analyzer.analyze_prompt_context(prompt)

        # Generate intelligent reminders
        reminder_gen = IntelligentReminder()
        reminders = reminder_gen.generate_reminders(prompt, context)

        # Build context enhancements
        output_parts = []

        # Add context-aware enhancements
        if context["suggested_agents"]:
            agent_suggestions = "🤖 Suggested agents: " + ", ".join(
                f"{agent[0]}" for agent in context["suggested_agents"][:2]
            )
            output_parts.append(agent_suggestions)

        # Add reminders if relevant
        if reminders:
            reminder_text = "💡 Context-aware tips:\n" + "\n".join(reminders[:3])
            output_parts.append(reminder_text)

        # Build the additional context
        if output_parts:
            enhanced_context = "\n".join(output_parts)
            context_tips = f"Think deeply: {enhanced_context}\n\n"
        else:
            context_tips = ""

        # Get relevant MCP tools based on context
        relevant_mcp_tools = _get_relevant_mcp_tools(context)

        # Build the comprehensive additional context with all required statements
        additional_context = f"""{context_tips}PROJECT MANAGEMENT APPROACH:

🧠 ZEN is your co-pilot project manager. Consult FIRST for:
   • Task analysis & strategy (mcp__zen__chat with use_websearch=true)
   • Hiring specialized workers: 0-3 subagents based on complexity
   • Current best practices via Tavily web search

🛠️ EXECUTION PRIORITIES:
   1. Batch operations: Multiple files → read_multiple_files
   2. Code navigation: Always Serena (find_symbol > Read)
   3. Parallel execution: Never sequential when parallel possible

📋 RESPONSE FORMAT:
   • State subagent count (even if 0)
   • End with 3 actionable next steps
   • Skip docs unless explicitly requested

🎯 RECOMMENDED TOOLS:
{relevant_mcp_tools}"""

        # For UserPromptSubmit, simply print to stdout with exit code 0
        # This makes the output visible to Claude as additional context
        print(additional_context)
        sys.exit(0)

    elif hook_event == "PreToolUse":
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Track for pattern detection
        analyzer = ContextAnalyzer()
        analyzer.pattern_detector.add_operation(
            tool_name, tool_input, input_data.get("timestamp", time.time())
        )
        analyzer.session_tracker.add_tool_execution(tool_name, tool_input)

        # Get contextual suggestions
        suggestions = analyzer.get_contextual_suggestions(tool_name, tool_input)

        if suggestions:
            # For PreToolUse with suggestions (non-blocking)
            # We'll use simple output that shows only in transcript mode
            suggestion_text = "🧠 Context-Aware Suggestions:\n" + "\n".join(
                f"• {s}" for s in suggestions
            )

            # Use JSON output for clean control
            output = {"suppressOutput": False}  # Show in transcript mode

            # Print suggestions to stdout (visible in transcript mode)
            print(suggestion_text)
            print(json.dumps(output))

        # Exit code 0 - continue normally
        sys.exit(0)


if __name__ == "__main__":
    main()
