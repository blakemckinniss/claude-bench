#!/usr/bin/env python3
"""
Context Analyzer Module

Provides intelligent context analysis for user prompts and intent detection.
Part of the Claude Code hooks system for enhanced context awareness.
"""

import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..pattern_detector import PatternDetector
    from ..shared_state import HookStateManager, SessionTracker
else:
    # Runtime imports with graceful fallbacks
    PatternDetector = None
    HookStateManager = None
    SessionTracker = None

    try:
        # First try relative imports (when used as a package)
        from ..pattern_detector import PatternDetector
        from ..shared_state import HookStateManager, SessionTracker
    except ImportError:
        try:
            # Try absolute imports from parent directory
            import os
            import sys

            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from pattern_detector import PatternDetector  # type: ignore
            from shared_state import HookStateManager, SessionTracker  # type: ignore
        except ImportError:
            # Keep as None for graceful fallback
            pass


class ContextAnalyzer:
    """
    Analyzes conversation context for better suggestions and tool recommendations.

    Features:
    - Intent detection from user prompts
    - Scope and urgency analysis
    - Keyword extraction and prioritization
    - Contextual suggestion generation
    - Pattern-based workflow detection
    """

    # Cached compiled regex patterns for performance
    _intent_patterns: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (
            re.compile(r"\b(mcp|mcp server|servers.*access|what.*servers)\b"),
            "mcp_query",
        ),
        (re.compile(r"\b(find|search|locate|look for)\b"), "search"),
        (re.compile(r"\b(debug|fix|error|bug|issue)\b"), "debug"),
        (re.compile(r"\b(optimize|improve|speed up|performance)\b"), "optimize"),
        (re.compile(r"\b(review|audit|check|analyze)\b"), "review"),
        (re.compile(r"\b(refactor|modernize|clean up)\b"), "refactor"),
        (re.compile(r"\b(test|coverage|unit test)\b"), "test"),
        (re.compile(r"\b(implement|add|create|build)\b"), "implement"),
    ]

    _scope_extensive_pattern = re.compile(r"\b(all|every|entire|whole|throughout)\b")
    _scope_targeted_pattern = re.compile(r"\b(specific|particular|single|just)\b")
    _urgency_high_pattern = re.compile(r"\b(asap|urgent|quickly|fast)\b")
    _urgency_low_pattern = re.compile(r"\b(when you can|eventually|later)\b")
    _word_pattern = re.compile(r"\b\w+\b")
    _tech_file_pattern = re.compile(r".*\.(py|js|ts|java|cpp|go|rb|php|swift|kt)")

    def __init__(self) -> None:
        """Initialize the context analyzer with required dependencies."""
        try:
            self.state_manager: HookStateManager | None = HookStateManager()
            self.pattern_detector: PatternDetector | None = PatternDetector()
            self.session_tracker: SessionTracker | None = SessionTracker()
        except Exception as e:
            # Graceful fallback if dependencies aren't available
            self.state_manager = None
            self.pattern_detector = None
            self.session_tracker = None
            # Log error but don't fail initialization
            print(
                f"Warning: ContextAnalyzer initialized with limited "
                f"functionality: {e}"
            )

    def analyze_prompt_context(self, prompt: str) -> dict[str, Any]:
        """
        Analyze user prompt for context clues and intent.

        Args:
            prompt: The user's input prompt to analyze

        Returns:
            Dictionary containing analysis results:
            - intent: Primary intent detected
            - scope: Task scope (extensive, targeted, moderate)
            - urgency: Urgency level (high, normal, low)
            - keywords: Important keywords extracted
            - suggested_tools: Tool suggestions based on intent
            - suggested_agents: Agent suggestions for complex tasks
        """
        if not prompt or not isinstance(prompt, str):
            return self._get_default_context()

        try:
            suggested_tools: list[tuple[str, str]] = []
            suggested_agents: list[tuple[str, str]] = []

            context: dict[str, Any] = {
                "intent": self._detect_intent(prompt),
                "scope": self._detect_scope(prompt),
                "urgency": self._detect_urgency(prompt),
                "keywords": list(self._extract_keywords(prompt)),
                "suggested_tools": suggested_tools,
                "suggested_agents": suggested_agents,
                "confidence": self._calculate_confidence(prompt),
            }

            # Add intent-specific suggestions
            self._add_intent_suggestions(context)

            return context

        except Exception as e:
            print(f"Error analyzing prompt context: {e}")
            return self._get_default_context()

    def _get_default_context(self) -> dict[str, Any]:
        """Return default context when analysis fails."""
        return {
            "intent": "general",
            "scope": "moderate",
            "urgency": "normal",
            "keywords": [],
            "suggested_tools": [],
            "suggested_agents": [],
            "confidence": 0.0,
        }

    @staticmethod
    @lru_cache(maxsize=256)
    def _detect_intent(prompt: str) -> str:
        """
        Detect primary intent from prompt using regex patterns.

        Args:
            prompt: User input to analyze

        Returns:
            Intent string (mcp_query, search, debug, optimize, etc.)
        """
        try:
            prompt_lower = prompt.lower()

            for pattern, intent in ContextAnalyzer._intent_patterns:
                if pattern.search(prompt_lower):
                    return intent

            return "general"
        except Exception:
            return "general"

    def _detect_scope(self, prompt: str) -> str:
        """
        Detect scope of the task from prompt content.

        Args:
            prompt: User input to analyze

        Returns:
            Scope string (extensive, targeted, moderate)
        """
        try:
            prompt_lower = prompt.lower()

            if self._scope_extensive_pattern.search(prompt_lower):
                return "extensive"
            elif self._scope_targeted_pattern.search(prompt_lower):
                return "targeted"
            else:
                return "moderate"
        except Exception:
            return "moderate"

    def _detect_urgency(self, prompt: str) -> str:
        """
        Detect urgency level from prompt language.

        Args:
            prompt: User input to analyze

        Returns:
            Urgency string (high, normal, low)
        """
        try:
            prompt_lower = prompt.lower()

            if self._urgency_high_pattern.search(prompt_lower):
                return "high"
            elif self._urgency_low_pattern.search(prompt_lower):
                return "low"
            else:
                return "normal"
        except Exception:
            return "normal"

    @staticmethod
    @lru_cache(maxsize=256)
    def _extract_keywords(prompt: str) -> tuple[str, ...]:
        """
        Extract important keywords from prompt, prioritizing technical terms.

        Args:
            prompt: User input to analyze

        Returns:
            Tuple of extracted keywords (hashable for caching)
        """
        try:
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
                "with",
                "by",
                "from",
                "up",
                "about",
                "into",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "if",
                "when",
                "where",
                "why",
                "how",
                "what",
                "which",
                "who",
                "whom",
                "whose",
                "this",
                "that",
                "these",
                "those",
                "i",
                "me",
                "my",
                "myself",
                "we",
                "our",
                "ours",
                "ourselves",
                "you",
                "your",
                "yours",
                "yourself",
                "yourselves",
                "he",
                "him",
                "his",
                "himself",
                "she",
                "her",
                "hers",
                "herself",
                "it",
                "its",
                "itself",
                "they",
                "them",
                "their",
                "theirs",
                "themselves",
            }

            words = ContextAnalyzer._word_pattern.findall(prompt.lower())
            keywords = [w for w in words if w not in stop_words and len(w) > 2]

            # Prioritize technical terms and file extensions
            tech_terms = []
            regular_terms = []

            for word in keywords:
                if ContextAnalyzer._tech_file_pattern.match(f"test.{word}") or word in {
                    "api",
                    "json",
                    "xml",
                    "html",
                    "css",
                    "sql",
                    "git",
                    "docker",
                    "kubernetes",
                    "aws",
                    "azure",
                    "gcp",
                }:
                    tech_terms.append(word)
                else:
                    regular_terms.append(word)

            # Return top 10 keywords with tech terms prioritized
            result = tech_terms[:5] + regular_terms[:5]
            return tuple(result[:10])

        except Exception:
            return ()

    def _calculate_confidence(self, prompt: str) -> float:
        """
        Calculate confidence score for the analysis based on prompt characteristics.

        Args:
            prompt: User input to analyze

        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            score = 0.5  # Base confidence

            # Higher confidence for longer, more specific prompts
            word_count = len(prompt.split())
            if word_count > 10:
                score += 0.2
            elif word_count > 5:
                score += 0.1

            # Higher confidence if technical keywords are present
            keywords = self._extract_keywords(prompt)
            if len(keywords) >= 3:
                score += 0.2

            # Higher confidence if intent patterns match strongly
            intent_matches = sum(
                1
                for pattern, _ in self._intent_patterns
                if pattern.search(prompt.lower())
            )
            if intent_matches > 1:
                score += 0.1

            return min(1.0, score)

        except Exception:
            return 0.5

    def _add_intent_suggestions(self, context: dict[str, Any]) -> None:
        """
        Add intent-specific tool and agent suggestions to context.

        Args:
            context: Context dictionary to modify with suggestions
        """
        intent = context["intent"]
        scope = context["scope"]

        try:
            # Tool suggestions based on intent
            if intent == "mcp_query":
                context["suggested_tools"].append(
                    ("ListMcpResourcesTool", "List available MCP servers and resources")
                )
                context["suggested_tools"].append(
                    ("ReadMcpResourceTool", "Read specific MCP resource content")
                )

            elif intent == "search":
                if scope == "extensive":
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
                    context["suggested_tools"].append(
                        ("find_symbol", "Navigate code symbols directly")
                    )

            elif intent == "debug":
                context["suggested_agents"].append(
                    (
                        "debugger",
                        'Use Task(subagent_type="debugger") for complex debugging',
                    )
                )
                context["suggested_tools"].append(
                    ("getDiagnostics", "Get language server diagnostics")
                )

            elif intent == "optimize":
                context["suggested_agents"].append(
                    (
                        "performance-engineer",
                        'Use Task(subagent_type="performance-engineer")',
                    )
                )
                context["suggested_tools"].append(
                    ("benchmark_run", "Run performance benchmarks")
                )

            elif intent == "review":
                context["suggested_agents"].append(
                    ("code-reviewer", 'Use Task(subagent_type="code-reviewer")')
                )
                context["suggested_tools"].append(
                    ("zen__codereview", "Zen-managed comprehensive code review")
                )

            elif intent == "refactor":
                context["suggested_agents"].append(
                    ("refactor", 'Use Task(subagent_type="refactor") for modernization')
                )
                context["suggested_tools"].append(
                    ("replace_symbol_body", "Replace code symbols efficiently")
                )

            elif intent == "test":
                context["suggested_tools"].append(
                    ("zen__testgen", "Generate comprehensive test suites")
                )
                context["suggested_tools"].append(
                    ("executeCode", "Execute test code in IDE")
                )

            elif intent == "implement":
                context["suggested_tools"].append(
                    ("zen__chat", "Plan implementation strategy with Zen")
                )
                context["suggested_tools"].append(
                    ("insert_after_symbol", "Add new code after existing symbols")
                )

        except Exception as e:
            print(f"Warning: Failed to add intent suggestions: {e}")

    def get_contextual_suggestions(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> list[str]:
        """
        Get context-aware suggestions based on tool usage patterns.

        Args:
            tool_name: Name of the tool being used
            tool_input: Input parameters for the tool

        Returns:
            List of contextual suggestions
        """
        suggestions: list[str] = []

        try:
            if not self.session_tracker:
                return suggestions

            # Get recent operations for pattern detection
            recent_ops = self.session_tracker.get_recent_operations(seconds=60)

            # File reading patterns
            if tool_name == "Read":
                recent_reads = [op for op in recent_ops if op["tool"] == "Read"]
                if len(recent_reads) >= 2:
                    files = [op.get("file_path", "unknown") for op in recent_reads[-3:]]
                    suggestions.append(
                        f"📚 Multiple file reads detected. Consider batching with "
                        f"read_multiple_files: {files[:3]}"
                    )

            # Command execution patterns
            elif tool_name == "Bash":
                command = tool_input.get("command", "")
                if "grep" in command:
                    recent_greps = [
                        op
                        for op in recent_ops
                        if op["tool"] == "Bash" and "grep" in op.get("command", "")
                    ]
                    if len(recent_greps) >= 2:
                        suggestions.append(
                            "🔍 Multiple grep commands detected. Switch to 'rg' "
                            "(ripgrep) for 10-100x performance improvement!"
                        )

            # Symbol search patterns
            elif tool_name == "find_symbol":
                recent_symbols = [
                    op for op in recent_ops if op["tool"] == "find_symbol"
                ]
                if len(recent_symbols) >= 3:
                    suggestions.append(
                        "🎯 Multiple symbol searches detected. Consider batching or "
                        "using get_symbols_overview for broader context first."
                    )

            # Get workflow-based suggestions from pattern detector
            if self.pattern_detector:
                workflows = self.pattern_detector.detect_workflows()
                for workflow in workflows:
                    if hasattr(workflow, "optimization_suggestion"):
                        suggestions.append(f"🔄 {workflow.optimization_suggestion}")

        except Exception as e:
            print(f"Warning: Failed to generate contextual suggestions: {e}")

        return suggestions

    def is_trivial_request(self, prompt: str) -> bool:
        """
        Check if the request is trivial and should skip enhancement.

        Args:
            prompt: User input to check

        Returns:
            True if the request is trivial
        """
        if not prompt or not isinstance(prompt, str):
            return True

        trivial_patterns = [
            r"^(yes|no|ok|okay|sure|alright|fine|got it|understood)\.?$",
            r"^(please do|do it|go ahead|proceed|continue|thanks|thank you)\.?$",
            r"^(yep|yeah|nope|nah|cool|great|good|perfect|exactly)\.?$",
            r"^(right|correct|indeed|absolutely)\.?$",
            r"^\d+\s*[\+\-\*/]\s*\d+\s*\??$",  # Simple math like "2 + 2?"
            r"^what is \d+\s*[\+\-\*/]\s*\d+\s*\??$",  # Simple math questions
        ]

        prompt_lower = prompt.lower().strip()
        return any(re.match(pattern, prompt_lower) for pattern in trivial_patterns)
