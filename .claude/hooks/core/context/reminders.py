#!/usr/bin/env python3
"""
Intelligent Reminder Module

Provides contextual reminders and suggestions based on user intent and context.
Part of the Claude Code hooks system for enhanced user guidance.
"""

from typing import Any

from .analyzer import ContextAnalyzer


class IntelligentReminder:
    """
    Provides intelligent, context-aware reminders for optimal Claude Code usage.

    Features:
    - Intent-based reminder generation
    - Scope-aware suggestions
    - Performance optimization tips
    - Best practice recommendations
    - Pattern-based workflow guidance
    """

    def __init__(self) -> None:
        """Initialize the intelligent reminder system."""
        try:
            self.context_analyzer: ContextAnalyzer | None = ContextAnalyzer()
        except Exception as e:
            self.context_analyzer = None
            print(
                f"Warning: IntelligentReminder initialized with limited "
                f"functionality: {e}"
            )

    def generate_reminders(self, prompt: str, context: dict[str, Any]) -> list[str]:
        """
        Generate smart reminders based on prompt and context analysis.

        Args:
            prompt: The user's input prompt
            context: Context analysis results from ContextAnalyzer

        Returns:
            List of contextual reminders and suggestions
        """
        if not prompt or not context:
            return []

        reminders: list[str] = []

        try:
            # Generate intent-specific reminders
            self._add_intent_reminders(context, reminders)

            # Generate scope-based reminders
            self._add_scope_reminders(context, reminders)

            # Generate urgency-based reminders
            self._add_urgency_reminders(context, reminders)

            # Generate pattern-based reminders
            self._add_pattern_reminders(context, reminders)

            # Generate best practice reminders
            self._add_best_practice_reminders(context, reminders)

            # Limit to most relevant reminders
            return reminders[:4]

        except Exception as e:
            print(f"Warning: Failed to generate reminders: {e}")
            return []

    def _add_intent_reminders(
        self, context: dict[str, Any], reminders: list[str]
    ) -> None:
        """Add reminders based on detected intent."""
        intent = context.get("intent", "general")

        intent_reminders = {
            "mcp_query": [
                "🔌 MCP servers: Use ListMcpResourcesTool to see all available "
                "MCP servers",
                "📋 Resource discovery: ReadMcpResourceTool for specific MCP "
                "resource content",
            ],
            "search": [
                "🔍 Search efficiently: Use 'rg' for text, 'fd' for files, "
                "Task for extensive searches",
                "🎯 Code navigation: Prefer Serena's find_symbol over reading "
                "entire files",
            ],
            "debug": [
                "🐛 Debug systematically: Task(subagent_type='debugger') handles "
                "complex issues",
                "📊 Get diagnostics: Use getDiagnostics for language server insights",
            ],
            "optimize": [
                "⚡ Measure first: Always profile before optimizing",
                "🚀 Performance focus: Use Task(subagent_type='performance-engineer')",
            ],
            "review": [
                "👁️ Comprehensive review: Use Task(subagent_type='code-reviewer')",
                "🔒 Security focus: Consider zen__secaudit for security-critical code",
            ],
            "refactor": [
                "🔄 Plan refactoring: Use Task(subagent_type='refactor') for "
                "major changes",
                "🎨 Code quality: Focus on readability and maintainability",
            ],
            "test": [
                "🧪 Test strategy: Use zen__testgen for comprehensive test suites",
                "✅ Coverage matters: Aim for edge cases and error conditions",
            ],
            "implement": [
                "📝 Plan first: Use zen__chat to strategize implementation approach",
                "🏗️ Build incrementally: Start with core functionality, then extend",
            ],
        }

        if intent in intent_reminders:
            reminders.extend(intent_reminders[intent][:2])

    def _add_scope_reminders(
        self, context: dict[str, Any], reminders: list[str]
    ) -> None:
        """Add reminders based on task scope."""
        scope = context.get("scope", "moderate")

        if scope == "extensive":
            reminders.append(
                "🌍 Extensive operations: Delegate to Task subagents to save "
                "context and enable parallel processing"
            )
        elif scope == "targeted":
            reminders.append(
                "🎯 Targeted operations: Use Serena's symbolic navigation for "
                "precise code manipulation"
            )
        else:  # moderate
            reminders.append(
                "⚖️ Balanced approach: Consider batching related operations "
                "for efficiency"
            )

    def _add_urgency_reminders(
        self, context: dict[str, Any], reminders: list[str]
    ) -> None:
        """Add reminders based on urgency level."""
        urgency = context.get("urgency", "normal")

        if urgency == "high":
            reminders.append(
                "🚀 High urgency: Batch operations, use parallel execution, "
                "delegate to specialized subagents"
            )
        elif urgency == "low":
            reminders.append(
                "🐌 Take time: Consider thorough analysis and comprehensive testing"
            )

    def _add_pattern_reminders(
        self, context: dict[str, Any], reminders: list[str]
    ) -> None:
        """Add reminders based on detected patterns."""
        if not self.context_analyzer or not self.context_analyzer.pattern_detector:
            return

        try:
            patterns = self.context_analyzer.pattern_detector.detect_workflows()
            if patterns:
                workflow_type = (
                    patterns[0].type.value
                    if hasattr(patterns[0], "type")
                    else "unknown"
                )
                reminders.append(
                    f"📊 Pattern detected: {workflow_type} workflow - consider "
                    "optimizing this recurring pattern"
                )
        except Exception as e:
            print(f"Warning: Failed to add pattern reminders: {e}")

    def _add_best_practice_reminders(
        self, context: dict[str, Any], reminders: list[str]
    ) -> None:
        """Add general best practice reminders."""
        keywords = context.get("keywords", [])

        # File operation best practices
        if any(keyword in ["file", "files", "read", "write"] for keyword in keywords):
            reminders.append(
                "📁 File operations: Prefer read_multiple_files for multiple files, "
                "use absolute paths"
            )

        # Git operation best practices
        if any(keyword in ["git", "commit", "branch", "merge"] for keyword in keywords):
            reminders.append(
                "🔄 Git operations: Use parallel git commands (status + diff + log) "
                "for comprehensive context"
            )

        # Performance best practices
        if any(
            keyword in ["performance", "slow", "optimize", "speed"]
            for keyword in keywords
        ):
            reminders.append(
                "⚡ Performance: Use modern tools (rg > grep, fd > find, bat > cat) "
                "for 10-100x improvements"
            )

    def get_tool_specific_reminders(
        self, tool_name: str, context: dict[str, Any]
    ) -> list[str]:
        """
        Get reminders specific to a particular tool being used.

        Args:
            tool_name: Name of the tool being used
            context: Context analysis results

        Returns:
            List of tool-specific reminders
        """
        reminders: list[str] = []

        try:
            tool_reminders = {
                "Read": [
                    "📚 Consider read_multiple_files for multiple file operations",
                    "🎯 Use find_symbol for specific code elements instead of "
                    "reading entire files",
                ],
                "Bash": [
                    "🔍 Use 'rg' instead of 'grep' for 10-100x performance improvement",
                    "📂 Use 'fd' instead of 'find' for faster file discovery",
                ],
                "find_symbol": [
                    "🗺️ Use get_symbols_overview first for broader context",
                    "⚡ Batch multiple symbol searches for efficiency",
                ],
                "Write": [
                    "✏️ Prefer editing existing files over creating new ones",
                    "📝 Use absolute paths for consistency",
                ],
                "zen__chat": [
                    "🧠 Enable use_websearch=true for current best practices",
                    "🎯 Be specific about complexity level for optimal subagent "
                    "allocation",
                ],
            }

            if tool_name in tool_reminders:
                reminders.extend(tool_reminders[tool_name])

            return reminders[:2]  # Limit to 2 most relevant

        except Exception as e:
            print(f"Warning: Failed to generate tool-specific reminders: {e}")
            return []

    def format_reminders_for_output(self, reminders: list[str]) -> str:
        """
        Format reminders for display in Claude's context.

        Args:
            reminders: List of reminder strings

        Returns:
            Formatted reminder text for context enhancement
        """
        if not reminders:
            return ""

        try:
            # Group similar reminders and deduplicate
            unique_reminders = list(dict.fromkeys(reminders))

            if len(unique_reminders) == 1:
                return f"💡 Context tip: {unique_reminders[0]}"
            else:
                formatted = "💡 Context-aware tips:\n"
                for reminder in unique_reminders[:3]:  # Limit to top 3
                    formatted += f"   • {reminder}\n"
                return formatted.rstrip()

        except Exception as e:
            print(f"Warning: Failed to format reminders: {e}")
            return ""

    def should_show_reminders(self, context: dict[str, Any]) -> bool:
        """
        Determine if reminders should be shown based on context.

        Args:
            context: Context analysis results

        Returns:
            True if reminders should be displayed
        """
        try:
            # Don't show reminders for trivial requests
            if context.get("confidence", 0.0) < 0.3:
                return False

            # Always show for complex operations
            if context.get("scope") == "extensive":
                return True

            # Show for high-urgency tasks
            if context.get("urgency") == "high":
                return True

            # Show for specific intents that benefit from guidance
            beneficial_intents = [
                "debug",
                "optimize",
                "review",
                "refactor",
                "implement",
            ]
            if context.get("intent") in beneficial_intents:
                return True

            return True  # Default to showing reminders

        except Exception:
            return True  # Default to showing reminders
