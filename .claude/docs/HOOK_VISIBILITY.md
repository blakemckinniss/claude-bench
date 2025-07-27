# Hook Visibility to Claude Code

This document confirms what Claude Code can see from each hook output.

## Hook Output Rules

| Exit Code | Stdout | Stderr | Claude Sees | User Sees |
|-----------|--------|--------|-------------|-----------|
| 0 | Content | - | Only for UserPromptSubmit (as context) | In transcript mode (Ctrl-R) |
| 2 | - | Content | Yes (as feedback) | Yes |
| Other | - | Content | No | Yes |

## Our Hooks

### ✅ enforce_claude_md.py (PreToolUse)
- **Output**: Exit code 2 with stderr
- **Claude sees**: YES - All validation errors and suggestions
- **Example**: "Use 'rg' (ripgrep) instead of 'grep' for better performance"

### ✅ redirect-to-tavily.py (PreToolUse)
- **Output**: Exit code 2 with stderr
- **Claude sees**: YES - Redirect instructions with examples
- **Example**: "The WebFetch tool is blocked. Use mcp__tavily-remote__tavily_extract"

### ✅ additional_context.py (UserPromptSubmit)
- **Output**: Exit code 0 with stdout
- **Claude sees**: YES - Added as context before processing prompt
- **Example**: Performance reminders based on prompt keywords

### ✅ post_tool_feedback.py (PostToolUse)
- **Output**: JSON with "decision": "block" and "reason"
- **Claude sees**: YES - The reason field is shown to Claude
- **Example**: "Performance tip: Consider using read_multiple_files"

## Testing Claude Visibility

To verify Claude sees the output:

```bash
# Test 1: Block a grep command (Claude will see this)
echo '{"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "grep -r TODO ."}}' | ./enforce_claude_md.py

# Test 2: Block WebFetch (Claude will see this)
echo '{"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}}' | ./redirect-to-tavily.py

# Test 3: Add context for a search prompt (Claude will see this)
echo '{"hook_event_name": "UserPromptSubmit", "prompt": "search for authentication code"}' | ./additional_context.py

# Test 4: Provide post-execution feedback (Claude will see this)
echo '{"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "git status"}}' | ./post_tool_feedback.py
```

## Summary

All hooks are correctly configured to ensure Claude Code sees the feedback:
- PreToolUse hooks use exit code 2 with stderr ✓
- PostToolUse hook uses JSON with "decision": "block" ✓
- UserPromptSubmit hook uses exit code 0 with stdout ✓

This ensures Claude Code can learn from and respond to the performance optimization guidelines.