#!/usr/bin/env python3
"""
Context Enrichment Hook Entry Point

Clean executable entry point that uses the modular context system.
Uses proper Python import handling and registry pattern for expandability.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, cast


def setup_python_path() -> None:
    """Setup Python path to enable proper imports."""
    current_dir = Path(__file__).parent
    context_dir = current_dir / "context"

    for path_dir in [str(current_dir), str(context_dir)]:
        if path_dir not in sys.path:
            sys.path.insert(0, path_dir)


def main() -> None:
    """Hook entry point that coordinates modular context enrichment."""
    setup_python_path()

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")

    if hook_event == "UserPromptSubmit":
        result = handle_user_prompt_submit(input_data)
        if result["status"] == "success":
            print(result["enhanced_context"])
        sys.exit(0)

    elif hook_event == "PreToolUse":
        result = handle_pre_tool_use(input_data)
        if result["status"] == "success":
            print(result["formatted_output"])
            print(json.dumps({"suppressOutput": False}))
        sys.exit(0)

    sys.exit(0)


def handle_user_prompt_submit(input_data: dict[str, Any]) -> dict[str, Any]:
    """Handle UserPromptSubmit hook events with context enhancement."""
    prompt = input_data.get("prompt", "")

    if not prompt:
        return {"status": "ignored", "reason": "Empty prompt"}

    try:
        # Import context modules with error handling
        try:
            from context.analyzer import (
                ContextAnalyzer,  # type: ignore[import-not-found]
            )
            from context.reminders import (
                IntelligentReminder,  # type: ignore[import-not-found]
            )
            from context.tools import (
                get_relevant_mcp_tools,  # type: ignore[import-not-found]
            )
        except ImportError as e:
            print(f"Warning: Context modules not available: {e}", file=sys.stderr)
            return {"status": "error", "reason": f"Import error: {e}"}

        # Initialize components
        analyzer = ContextAnalyzer()
        reminder_gen = IntelligentReminder()

        # Check if this is a trivial request
        if analyzer.is_trivial_request(prompt):
            return {"status": "ignored", "reason": "Trivial request"}

        # Analyze context
        context = cast(dict[str, Any], analyzer.analyze_prompt_context(prompt))

        # Generate intelligent reminders
        reminders = reminder_gen.generate_reminders(prompt, context)

        # Build context enhancements
        output_parts = []

        # Add context-aware enhancements
        if context.get("suggested_agents"):
            agent_suggestions = "🤖 Suggested agents: " + ", ".join(
                str(agent[0]) for agent in context["suggested_agents"][:2]
            )
            output_parts.append(agent_suggestions)

        # Add reminders if relevant
        if reminders and reminder_gen.should_show_reminders(context):
            formatted_reminders = reminder_gen.format_reminders_for_output(reminders)
            if formatted_reminders:
                output_parts.append(formatted_reminders)

        # Build enhanced context
        if output_parts:
            enhanced_context = "\n".join(output_parts)
            context_tips = f"Think deeply: {enhanced_context}\n\n"
        else:
            context_tips = ""

        # Get relevant MCP tools
        relevant_mcp_tools = get_relevant_mcp_tools(context)

        # Build comprehensive context
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

        return {
            "status": "success",
            "enhanced_context": additional_context,
            "context_analysis": context,
            "reminders_count": len(reminders),
        }

    except Exception as e:
        print(f"Error in context enrichment: {e}", file=sys.stderr)
        return {"status": "error", "reason": str(e)}


def handle_pre_tool_use(input_data: dict[str, Any]) -> dict[str, Any]:
    """Handle PreToolUse hook events with contextual suggestions."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if not tool_name:
        return {"status": "ignored", "reason": "No tool name"}

    try:
        # Import context modules with error handling
        try:
            from context.analyzer import ContextAnalyzer
        except ImportError as e:
            print(f"Warning: Context analyzer not available: {e}", file=sys.stderr)
            return {"status": "error", "reason": f"Import error: {e}"}

        # Initialize analyzer
        analyzer = ContextAnalyzer()

        # Track for pattern detection
        if analyzer.pattern_detector:
            analyzer.pattern_detector.add_operation(
                tool_name, tool_input, input_data.get("timestamp", time.time())
            )

        if analyzer.session_tracker:
            analyzer.session_tracker.add_tool_execution(tool_name, tool_input)

        # Get contextual suggestions
        suggestions = analyzer.get_contextual_suggestions(tool_name, tool_input)

        if not suggestions:
            return {"status": "ignored", "reason": "No suggestions available"}

        # Format suggestions
        suggestion_text = "🧠 Context-Aware Suggestions:\n" + "\n".join(
            f"• {s}" for s in suggestions
        )

        return {
            "status": "success",
            "suggestions": suggestions,
            "formatted_output": suggestion_text,
            "suppress_output": False,
        }

    except Exception as e:
        print(f"Error in pre-tool use handler: {e}", file=sys.stderr)
        return {"status": "error", "reason": str(e)}


# Standalone API functions for programmatic usage
def analyze_context(prompt: str) -> dict[str, Any]:
    """Standalone function to analyze context without hook infrastructure."""
    setup_python_path()

    try:
        from context.analyzer import ContextAnalyzer

        analyzer = ContextAnalyzer()
        result = analyzer.analyze_prompt_context(prompt)
        return cast(dict[str, Any], result)
    except Exception:
        return {
            "intent": "general",
            "scope": "moderate",
            "urgency": "normal",
            "keywords": [],
            "suggested_tools": [],
            "suggested_agents": [],
            "confidence": 0.0,
        }


def get_suggestions_for_tool(tool_name: str, tool_input: dict[str, Any]) -> list[str]:
    """Standalone function to get tool suggestions without hook infrastructure."""
    setup_python_path()

    try:
        from context.analyzer import ContextAnalyzer  # type: ignore[import-not-found]

        analyzer = ContextAnalyzer()
        result = analyzer.get_contextual_suggestions(tool_name, tool_input)
        return cast(list[str], result)
    except Exception:
        return []


if __name__ == "__main__":
    main()
