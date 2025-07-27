#!/usr/bin/env python3
"""
Tool suggestion mappings for different intents

Enhanced version combining the best of both implementations.
Provides comprehensive MCP tool suggestions based on user context.
"""

from typing import Any


def get_relevant_mcp_tools(context: dict[str, Any]) -> str:
    """
    Get the 3 most relevant MCP tools based on context analysis.

    Args:
        context: Context analysis results containing intent, scope, etc.

    Returns:
        Formatted string with relevant MCP tool suggestions
    """
    intent = context.get("intent", "general")

    # Map intents to relevant MCP tools with comprehensive coverage
    mcp_tool_suggestions = {
        "mcp_query": [
            "• mcp__zen__chat (use_websearch=true) - Consult Zen with web search",
            "• ListMcpResourcesTool - List all available MCP servers",
            "• ReadMcpResourceTool - Read specific MCP resources",
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


def get_tool_suggestions_by_scope(scope: str) -> list[str]:
    """
    Get tool suggestions based on task scope.

    Args:
        scope: Task scope (extensive, targeted, moderate)

    Returns:
        List of scope-specific suggestions
    """
    scope_suggestions = {
        "extensive": [
            "Consider using Task subagents for extensive operations",
            "Use parallel execution to handle large scope efficiently",
            "Break down into smaller, manageable chunks",
        ],
        "targeted": [
            "Use Serena's symbolic navigation for precise operations",
            "Direct tool usage is likely sufficient",
            "Focus on specific tools for targeted tasks",
        ],
        "moderate": [
            "Balance between direct tools and Task delegation",
            "Consider batching related operations",
            "Use appropriate tools for the task complexity",
        ],
    }

    return scope_suggestions.get(scope, scope_suggestions["moderate"])


def get_urgency_suggestions(urgency: str) -> list[str]:
    """
    Get suggestions based on urgency level.

    Args:
        urgency: Urgency level (high, normal, low)

    Returns:
        List of urgency-specific suggestions
    """
    urgency_suggestions = {
        "high": [
            "Use parallel execution for maximum speed",
            "Delegate complex tasks to specialized subagents",
            "Batch operations to reduce overhead",
        ],
        "normal": [
            "Use standard optimization practices",
            "Consider delegating if complexity is high",
            "Balance speed with thoroughness",
        ],
        "low": [
            "Take time for thorough analysis",
            "Consider comprehensive testing",
            "Focus on quality over speed",
        ],
    }

    return urgency_suggestions.get(urgency, urgency_suggestions["normal"])
