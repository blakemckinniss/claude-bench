#!/usr/bin/env python3
"""
Context-aware hooks for Claude Code
Modular architecture with clean separation of concerns
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analyzer import ContextAnalyzer
    from .reminders import IntelligentReminder
    from .tools import get_relevant_mcp_tools
else:
    try:
        from .analyzer import ContextAnalyzer
        from .reminders import IntelligentReminder
        from .tools import get_relevant_mcp_tools
    except ImportError:
        # Fallback for direct execution
        from analyzer import ContextAnalyzer  # type: ignore
        from reminders import IntelligentReminder  # type: ignore
        from tools import get_relevant_mcp_tools  # type: ignore

__all__ = ["ContextAnalyzer", "IntelligentReminder", "get_relevant_mcp_tools"]
