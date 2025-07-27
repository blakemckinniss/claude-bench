"""
Core Hook Functionality

Contains fundamental components for the Claude Code hooks system:
- shared_state: Cross-hook state management and communication
- pattern_detector: Advanced pattern detection for optimization suggestions
- context_enrichment: Intelligent context analysis and enhancement
"""

from .shared_state import HookStateManager, SessionTracker, PerformanceMonitor
from .pattern_detector import PatternDetector, WorkflowPattern, SmartSuggestions
from .context_enrichment import ContextAnalyzer, IntelligentReminder

__all__ = [
    "HookStateManager",
    "SessionTracker",
    "PerformanceMonitor",
    "PatternDetector",
    "WorkflowPattern",
    "SmartSuggestions",
    "ContextAnalyzer",
    "IntelligentReminder",
]
