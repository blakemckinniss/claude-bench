# Claude Code Memory System

A local ChromaDB and SQLite-based memory system that integrates with Claude Code hooks to provide context-aware assistance based on project history.

## Features

- **Project Isolation**: Each project maintains its own memory database
- **Vector Search**: Uses ChromaDB for semantic similarity search
- **Automatic Memory Storage**: Captures code patterns, error solutions, and insights
- **Context-Aware Suggestions**: Provides relevant memories when you start new prompts
- **Configurable**: Customize what gets stored and retrieved

## Architecture

```
.claude/memory_system/
├── chroma/              # ChromaDB vector storage (per project)
├── db/                  # SQLite metadata storage (per project)
├── config.json          # Configuration file
├── memory_manager.py    # Core memory management
├── memory_cli.py        # CLI tool for memory management
└── setup.py            # Installation script

.claude/hooks/
├── memory_retrieve_hook.py      # UserPromptSubmit - Provides context-aware suggestions
├── memory_pretool_hook.py       # PreToolUse - Memory-guided tool usage suggestions
├── memory_store_hook.py         # PostToolUse - Stores code patterns and solutions
├── memory_notification_hook.py  # Notification - Captures important events/errors
├── memory_stop_hook.py          # Stop - Saves session summaries
├── memory_subagent_stop_hook.py # SubagentStop - Captures subagent discoveries
└── memory_precompact_hook.py    # PreCompact - Preserves important memories
```

## Installation

### For Current Project

```bash
python .claude/memory_system/setup.py
```

### For Different Project

```bash
python /path/to/memory_system/setup.py --project-path /path/to/project
```

## Memory Types

1. **code_pattern**: Reusable code patterns and implementations
2. **error_solution**: Error patterns and their solutions
3. **project_context**: Project-specific context and conventions
4. **performance_insight**: Performance observations and optimizations
5. **architectural_decision**: Important architectural decisions
6. **session_summary**: Session summaries and key activities
7. **subagent_summary**: Summaries from Task subagent executions
8. **subagent_discovery**: Discoveries and insights from subagents
9. **security_finding**: Security vulnerabilities and fixes
10. **code_quality**: Code quality issues and recommendations
11. **compaction_preservation**: Important memories preserved before compaction

## Usage

### Automatic Operation

Once installed, the memory system works automatically:

1. **Storing**: When you edit code, fix errors, or make discoveries, relevant patterns are automatically stored
2. **Retrieving**: When you start a new prompt, relevant memories are searched and displayed as tips

### Manual Management

Use the CLI tool to manage memories:

```bash
# List all memories
python .claude/memory_system/memory_cli.py list

# Search memories
python .claude/memory_system/memory_cli.py search "authentication"

# Add a memory manually
python .claude/memory_system/memory_cli.py add -t code_pattern -f pattern.py

# Delete a memory
python .claude/memory_system/memory_cli.py delete <memory_id>

# Show statistics
python .claude/memory_system/memory_cli.py stats
```

## Configuration

Edit `.claude/memory_system/config.json` to customize:

```json
{
  "memory_system": {
    "enabled": true,
    "search": {
      "default_limit": 10,
      "similarity_threshold": 0.7
    },
    "hooks": {
      "auto_store": {
        "enabled": true,
        "min_content_length": 50,
        "excluded_tools": ["Read", "LS", "Bash"]
      },
      "auto_retrieve": {
        "enabled": true,
        "max_suggestions": 5
      }
    }
  }
}
```

## How It Works

### Hook Lifecycle Integration

The memory system utilizes all Claude Code hook lifecycles:

1. **UserPromptSubmit**: Retrieves relevant memories and adds them as context
2. **PreToolUse**: Provides memory-guided suggestions for tool usage
3. **PostToolUse**: Extracts and stores patterns from tool interactions
4. **Notification**: Captures important events and errors
5. **Stop**: Creates session summaries and extracts key learnings
6. **SubagentStop**: Captures discoveries from Task subagents
7. **PreCompact**: Preserves important memories before context compaction

### Storage Flow

1. Various hooks intercept events throughout the lifecycle
2. Content analyzers extract meaningful patterns
3. Relevant content is embedded and stored in ChromaDB
4. Metadata is stored in SQLite for fast filtering

### Retrieval Flow

1. UserPromptSubmit hook intercepts user prompts
2. ContextAnalyzer determines intent and keywords
3. ChromaDB searches for similar memories
4. Top results are formatted as tips and added to prompt
5. PreToolUse hook provides additional guidance based on past usage

## Privacy & Security

- All data is stored locally in your project directory
- No external services are used (except for embedding model)
- Memories are isolated per project
- You have full control over what gets stored

## Troubleshooting

### Dependencies Installation Failed

If you see pip installation errors, install manually:

```bash
pip install --break-system-packages chromadb==0.5.3 pydantic==2.9.2
```

### Memories Not Being Stored

1. Check if hooks are properly registered in `.claude/settings.json`
2. Verify config.json has `enabled: true`
3. Check minimum content length in config

### Memories Not Retrieved

1. Ensure similarity threshold isn't too high
2. Check if memories exist: `memory_cli.py list`
3. Verify retrieval hook is enabled in config

## Extending the System

### Adding New Memory Types

1. Add type definition in `config.json`
2. Update pattern detection in `memory_store_hook.py`
3. Add formatting logic in `memory_retrieve_hook.py`

### Custom Extraction Patterns

Edit `MemoryExtractor` class in `memory_store_hook.py` to add new patterns:

```python
self.patterns['new_type'] = [
    r'pattern1',
    r'pattern2'
]
```

## Future Enhancements

- [ ] Memory importance scoring
- [ ] Cross-project memory sharing (opt-in)
- [ ] Memory expiration and cleanup
- [ ] Export/import functionality
- [ ] Web UI for memory browsing