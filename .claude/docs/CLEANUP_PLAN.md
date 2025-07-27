# Claude Code Hook System - Cleanup Plan

## Technical Debt Files to Remove

### 1. Experimental Optimization Files (REMOVE)
These files use unsupported features like priority, condition, async, cache_key:
- `optimized_shared_state.py` - Memory-mapped state (incompatible)
- `optimized_pattern_detector.py` - Advanced pattern detection (incompatible)
- `hook_manager.py` - Uses priority/condition/async (NOT supported)
- `optimized_memory_manager.py` - Async ChromaDB (incompatible)
- `optimized_enforce_claude_md.py` - Uses caching/priorities (incompatible)
- `performance_dashboard.py` - Dashboard for unsupported metrics
- `migrate_to_optimized.py` - Migration script for incompatible features

### 2. Generated Analysis Files (REMOVE)
Files created by performance-engineer agent:
- `claude-hooks-performance-analysis.md`
- `hook-optimization-examples.py`
- `hook-performance-test.py`
- `hook-optimization-guide.md`

### 3. Implementation Documentation (REMOVE)
- `HOOK_OPTIMIZATION_IMPLEMENTATION.md` - Documents incompatible features

### 4. Performance Scripts (REMOVE IF EXIST)
- `check_performance.sh`
- `monitor_live.sh`

### 5. Backup Files (REMOVE IF EXIST)
- Any `*.bak` files
- Any `backup_*` directories

## Files to Keep (Compatible with Official Format)

### Core Hook Files
- `enforce_claude_md.py` - Main validation hook
- `shared_state.py` - JSON-based state management
- `pattern_detector.py` - Basic pattern detection
- `additional_context.py` - Context provider
- `redirect-to-tavily.py` - Web redirect hook

### Memory System Hooks
- `memory_store_hook.py`
- `memory_retrieve_hook.py`
- `memory_pretool_hook.py`
- `memory_notification_hook.py`
- `memory_stop_hook.py`
- `memory_subagent_stop_hook.py`
- `memory_precompact_hook.py`

### Other Standard Hooks
- `performance_monitor_hook.py` - Basic performance tracking
- `README.md` - Documentation

## Issues with Current settings.json

The current settings.json follows the official format correctly. No changes needed to structure.

## Incompatible Features We Must Remove

1. **Priority System** - Not supported in official format
2. **Condition Fields** - Python expressions not supported
3. **Async Execution** - Not supported
4. **Cache Keys** - Not supported
5. **Memory-Mapped Files** - Too complex
6. **Async ChromaDB** - Too complex
7. **Advanced Pattern Detection** - Too complex

## Migration Steps

1. Delete all experimental optimization files
2. Keep existing hook files that follow official format
3. Settings.json is already compliant - no changes needed
4. Remove any generated files and backups
5. Ensure all remaining hooks use simple command strings only