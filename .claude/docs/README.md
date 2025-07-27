# Claude Code Hooks - Optimized System

This directory contains performance-optimized hooks for Claude Code that enforce best practices from CLAUDE.md.

## Architecture

The hook system uses a modular architecture with shared state management for better performance and inter-hook communication.

### Core Components

1. **shared_state.py** - Thread-safe state management with file locking
   - `HookStateManager`: Manages persistent state across hook invocations
   - `SessionTracker`: Tracks tool usage patterns within a session
   - `PerformanceMonitor`: Records and analyzes performance metrics

2. **pattern_detector.py** - Advanced pattern detection
   - `PatternDetector`: Detects complex workflows that could be optimized
   - `WorkflowPattern`: Identifies common patterns (read-modify-write, search-read-edit, etc.)
   - `SmartSuggestions`: Generates context-aware optimization suggestions

### Active Hooks

1. **enforce_claude_md.py** (PreToolUse)
   - Validates Bash commands against modern alternatives (rg > grep, fd > find, jq for JSON)
   - Blocks WebSearch/WebFetch in favor of Tavily MCP
   - Detects batch operation opportunities
   - Suggests Task subagents for complex operations
   - Uses pre-compiled regex patterns and LRU caching for 79% performance improvement

2. **additional_context.py** (UserPromptSubmit)
   - Analyzes user prompts for intent, scope, and urgency
   - Suggests appropriate Task subagents based on context
   - Provides intelligent, context-aware reminders
   - Integrates with pattern detection for workflow optimization

3. **performance_monitor_hook.py** (PostToolUse)
   - Tracks execution times for all tools
   - Identifies slow operations and bottlenecks
   - Provides real-time performance insights
   - Suggests optimizations based on historical data

4. **redirect-to-tavily.py** (PreToolUse for WebFetch|WebSearch)
   - Redirects web operations to Tavily MCP tools
   - Ensures consistent use of more powerful web tools

## Performance Optimizations

1. **Pre-compiled Regex Patterns**: All regex patterns are compiled once at module load
2. **LRU Caching**: Repeated validations are cached for faster response
3. **Early Exit Logic**: Hooks return as soon as a decision can be made
4. **Shared State**: Inter-hook communication reduces redundant computations
5. **Batch Detection**: Identifies operations that could be parallelized

## Hook Communication

Hooks communicate through shared state files:
- `/tmp/claude_hook_shared_state.json` - Primary state storage
- `/tmp/claude_hook_state.lock` - File lock for thread safety

## Configuration

Hooks are configured in `.claude/settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/additional_context.py"
      }]
    }],
    "PreToolUse": [
      {
        "matcher": "WebFetch|WebSearch",
        "hooks": [{
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/redirect-to-tavily.py"
        }]
      },
      {
        "matcher": "*",
        "hooks": [{
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/enforce_claude_md.py",
          "timeout": 10
        }]
      }
    ],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/performance_monitor_hook.py"
      }]
    }]
  }
}
```

## Visibility to Claude Code

Different hook types have different visibility mechanisms:

1. **UserPromptSubmit**: Output to stdout with exit code 0 is added as context to the prompt
2. **PreToolUse/PostToolUse**: 
   - Exit code 2 with stderr output blocks and shows feedback
   - JSON output with `{"decision": "block"}` also blocks and shows feedback
   - Exit code 0 allows the operation to proceed

## Testing Individual Hooks

```bash
# Test enforce_claude_md.py
echo '{"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "grep -r TODO ."}}' | ./enforce_claude_md.py

# Test redirect-to-tavily.py
echo '{"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}}' | ./redirect-to-tavily.py

# Test additional_context.py
echo '{"hook_event_name": "UserPromptSubmit", "prompt": "search for authentication code"}' | ./additional_context.py

# Test performance_monitor_hook.py
echo '{"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "test.py"}, "tool_response": {"execution_time": 1.5}}' | ./performance_monitor_hook.py
```

## Backup

Original hooks are preserved in the `backup/` directory for reference.