# Claude Code Hooks Organization Guide

## Overview

The Claude Code hooks directory has been completely reorganized into a clean, maintainable structure following Python best practices and software engineering conventions.

## Directory Structure

```
.claude/hooks/
├── __init__.py                    # Main package initialization
├── ORGANIZATION_GUIDE.md          # This guide
│
├── core/                          # Core functionality and shared utilities
│   ├── __init__.py
│   ├── shared_state.py           # Cross-hook state management and communication
│   ├── pattern_detector.py       # Advanced pattern detection and optimization suggestions
│   └── context_enrichment.py     # Intelligent context analysis and enhancement (formerly additional_context.py)
│
├── memory/                        # Memory system integration hooks
│   ├── __init__.py
│   ├── retrieve_hook.py          # Context-aware memory retrieval
│   ├── store_hook.py             # Automatic memory storage of patterns and solutions
│   ├── notification_hook.py      # Memory-based notifications
│   ├── stop_hook.py              # Memory cleanup on session end
│   ├── subagent_stop_hook.py     # Subagent memory management
│   ├── precompact_hook.py        # Memory optimization before compaction
│   └── pretool_hook.py           # Pre-tool memory preparation
│
├── validation/                    # Code quality and guidelines enforcement
│   ├── __init__.py
│   ├── claude_guidelines_enforcer.py  # Performance optimization guidelines (formerly enforce_claude_md.py)
│   └── python_quality_validator.py    # Python code quality and tooling (formerly python_tools_hook.py)
│
├── integrations/                  # Third-party service integrations
│   ├── __init__.py
│   └── tavily_redirect.py        # Web tool redirection to Tavily MCP (formerly redirect-to-tavily.py)
│
├── monitoring/                    # Performance and usage monitoring
│   ├── __init__.py
│   └── performance_monitor.py    # Real-time performance monitoring (formerly performance_monitor_hook.py)
│
└── docs/                         # Documentation and guides
    ├── README.md
    ├── CLEANUP_COMPLETE.md
    ├── CLEANUP_PLAN.md
    └── HOOK_VISIBILITY.md
```

## Key Improvements

### 1. **Clear Separation of Concerns**
- **core/**: Fundamental shared functionality
- **memory/**: All memory-related operations
- **validation/**: Code quality and guideline enforcement
- **integrations/**: External service connections
- **monitoring/**: Performance tracking and analysis
- **docs/**: All documentation in one place

### 2. **Consistent Naming Conventions**
- **snake_case** for all file names
- Descriptive names that clearly indicate functionality
- Removed redundant prefixes (e.g., `memory_` prefix from memory hooks)
- More intuitive names (e.g., `context_enrichment.py` vs `additional_context.py`)

### 3. **Proper Python Package Structure**
- `__init__.py` files in every directory
- Explicit exports and documentation
- Relative imports where appropriate
- Clean dependency management

### 4. **Updated Configuration**
All hook paths in `settings.json` have been updated to reflect the new structure:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/core/context_enrichment.py",
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/retrieve_hook.py"
    ],
    "PreToolUse": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/integrations/tavily_redirect.py",
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/pretool_hook.py",
      "$CLAUDE_PROJECT_DIR/.claude/hooks/validation/python_quality_validator.py",
      "$CLAUDE_PROJECT_DIR/.claude/hooks/validation/claude_guidelines_enforcer.py"
    ],
    "PostToolUse": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/validation/python_quality_validator.py",
      "$CLAUDE_PROJECT_DIR/.claude/hooks/monitoring/performance_monitor.py",
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/store_hook.py"
    ],
    "Notification": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/notification_hook.py"
    ],
    "Stop": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/stop_hook.py"
    ],
    "SubagentStop": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/subagent_stop_hook.py"
    ],
    "PreCompact": [
      "$CLAUDE_PROJECT_DIR/.claude/hooks/memory/precompact_hook.py"
    ]
  }
}
```

## File Mapping (Old → New)

| Old Name | New Location | Purpose |
|----------|--------------|---------|
| `additional_context.py` | `core/context_enrichment.py` | Context analysis and enhancement |
| `shared_state.py` | `core/shared_state.py` | State management utilities |
| `pattern_detector.py` | `core/pattern_detector.py` | Pattern detection and suggestions |
| `memory_retrieve_hook.py` | `memory/retrieve_hook.py` | Memory retrieval |
| `memory_store_hook.py` | `memory/store_hook.py` | Memory storage |
| `memory_notification_hook.py` | `memory/notification_hook.py` | Memory notifications |
| `memory_stop_hook.py` | `memory/stop_hook.py` | Session cleanup |
| `memory_subagent_stop_hook.py` | `memory/subagent_stop_hook.py` | Subagent cleanup |
| `memory_precompact_hook.py` | `memory/precompact_hook.py` | Memory optimization |
| `memory_pretool_hook.py` | `memory/pretool_hook.py` | Pre-tool preparation |
| `enforce_claude_md.py` | `validation/claude_guidelines_enforcer.py` | Guidelines enforcement |
| `python_tools_hook.py` | `validation/python_quality_validator.py` | Python quality checks |
| `redirect-to-tavily.py` | `integrations/tavily_redirect.py` | Web tool redirection |
| `performance_monitor_hook.py` | `monitoring/performance_monitor.py` | Performance monitoring |

## Benefits of New Structure

### 1. **Better Maintainability**
- Related functionality grouped together
- Clear responsibility boundaries
- Easier to locate and modify specific features

### 2. **Improved Developer Experience**
- Intuitive directory navigation
- Clear import paths
- Self-documenting structure

### 3. **Enhanced Scalability**
- Easy to add new hooks in appropriate categories
- Modular design supports independent development
- Clean separation allows for better testing

### 4. **Professional Standards**
- Follows Python packaging conventions
- Clear documentation and type hints
- Consistent coding standards across all files

## Usage

All hooks continue to function exactly as before. The reorganization is purely structural and doesn't change the hook functionality or API.

### Importing Core Utilities

```python
# Import shared utilities
from ..core.shared_state import HookStateManager, SessionTracker
from ..core.pattern_detector import PatternDetector, SmartSuggestions
```

### Adding New Hooks

1. Choose the appropriate directory based on functionality
2. Follow the naming convention (snake_case)
3. Update the relevant `__init__.py` file
4. Add the hook path to `settings.json`
5. Update this documentation

## Verification

The reorganization maintains full backward compatibility:
- ✅ All hook functionality preserved
- ✅ Settings.json updated with new paths
- ✅ Import statements corrected
- ✅ Package structure properly configured
- ✅ Documentation organized and accessible

This new structure provides a solid foundation for future development and makes the Claude Code hooks system much more maintainable and professional.