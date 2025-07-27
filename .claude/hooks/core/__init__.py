"""
Core Hook Functionality

Contains fundamental components for the Claude Code hooks system:
- shared_state: Cross-hook state management and communication
- pattern_detector: Advanced pattern detection for optimization suggestions
- context_enrichment: Intelligent context analysis and enhancement
"""

from .context import ContextAnalyzer, IntelligentReminder
from .pattern_detector import PatternDetector, SmartSuggestions, WorkflowPattern
from .shared_state import HookStateManager, PerformanceMonitor, SessionTracker

__all__ = [
    "ContextAnalyzer",
    "HookStateManager",
    "IntelligentReminder",
    "PatternDetector",
    "PerformanceMonitor",
    "SessionTracker",
    "SmartSuggestions",
    "WorkflowPattern",
]
