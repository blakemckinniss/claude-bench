#!/usr/bin/env python3
"""
Context-Aware Hook for Claude Code
Uses conversation context to provide better suggestions
"""

import json
import sys
import os
import re
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared_state import HookStateManager, SessionTracker
from pattern_detector import PatternDetector


class ContextAnalyzer:
    """Analyzes conversation context for better suggestions"""

    def __init__(self):
        self.state_manager = HookStateManager()
        self.pattern_detector = PatternDetector()
        self.session_tracker = SessionTracker()

    def analyze_prompt_context(self, prompt: str) -> Dict[str, Any]:
        """Analyze user prompt for context clues"""
        context = {
            "intent": self._detect_intent(prompt),
            "scope": self._detect_scope(prompt),
            "urgency": self._detect_urgency(prompt),
            "keywords": self._extract_keywords(prompt),
            "suggested_tools": [],
            "suggested_agents": [],
        }

        # Suggest tools based on intent
        if context["intent"] == "mcp_query":
            context["suggested_tools"].append(
                ("ListMcpResourcesTool", "Use to list available MCP servers and resources")
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

    def _extract_keywords(self, prompt: str) -> List[str]:
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
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> List[str]:
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

    def __init__(self):
        self.context_analyzer = ContextAnalyzer()

    def generate_reminders(self, prompt: str, context: Dict[str, Any]) -> List[str]:
        """Generate smart reminders based on prompt and context"""
        reminders = []

        # Base reminders on intent
        if context["intent"] == "mcp_query":
            reminders.append(
                "🔌 MCP servers: Use ListMcpResourcesTool to see all available MCP servers"
            )
        elif context["intent"] == "search":
            reminders.append(
                "🔍 Search tips: Use 'rg' for text, 'fd' for files, Task for extensive searches"
            )
        elif context["intent"] == "debug":
            reminders.append(
                "🐛 Debug efficiently: Task(subagent_type='debugger') handles complex issues"
            )
        elif context["intent"] == "optimize":
            reminders.append(
                "⚡ Always measure first! Use Task(subagent_type='performance-engineer')"
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
                "🚀 For speed: Batch operations, use parallel execution, delegate to subagents"
            )

        # Pattern-based reminders
        patterns = self.context_analyzer.pattern_detector.detect_workflows()
        if patterns:
            reminders.append(
                f"📊 Detected {patterns[0].type.value} pattern - optimize this workflow!"
            )

        return reminders


def main():
    """Main hook handler with context awareness"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")

    if hook_event == "UserPromptSubmit":
        prompt = input_data.get("prompt", "")

        # Analyze context
        analyzer = ContextAnalyzer()
        context = analyzer.analyze_prompt_context(prompt)

        # Generate intelligent reminders
        reminder_gen = IntelligentReminder()
        reminders = reminder_gen.generate_reminders(prompt, context)

        # Build output with context enhancements ONLY
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

        # Only print if we have enhancements to add
        if output_parts:
            print("\n".join(output_parts))
        # If no enhancements, print nothing (pass through original prompt)

    elif hook_event == "PreToolUse":
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Track for pattern detection
        analyzer = ContextAnalyzer()
        analyzer.pattern_detector.add_operation(
            tool_name, tool_input, input_data.get("timestamp", 0)
        )
        analyzer.session_tracker.add_tool_execution(tool_name, tool_input)

        # Get contextual suggestions
        suggestions = analyzer.get_contextual_suggestions(tool_name, tool_input)

        if suggestions:
            print("🧠 Context-Aware Suggestions:", file=sys.stderr)
            for suggestion in suggestions:
                print(f"• {suggestion}", file=sys.stderr)
            # Don't block, just inform

    sys.exit(0)


if __name__ == "__main__":
    main()
