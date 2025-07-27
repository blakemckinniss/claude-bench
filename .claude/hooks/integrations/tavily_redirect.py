#!/usr/bin/env python3
import json
import sys

# Load input from stdin
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

# Map WebFetch/WebSearch to appropriate Tavily tools
tavily_alternatives = {
    "WebFetch": {
        "tool": "mcp__tavily-remote__tavily_extract",
        "description": "Extract content from specific URLs",
        "example": 'Use tavily_extract with urls=["https://example.com"]',
    },
    "WebSearch": {
        "tool": "mcp__tavily-remote__tavily_search",
        "description": "Search the web for information",
        "example": 'Use tavily_search with query="your search terms"',
    },
}

if tool_name in tavily_alternatives:
    alternative = tavily_alternatives[tool_name]

    # Provide helpful error message to Claude
    error_message = f"""
The {tool_name} tool is blocked by policy. Please use Tavily MCP instead:

Tool: {alternative['tool']}
Purpose: {alternative['description']}
Example: {alternative['example']}

Original request details:
- Tool: {tool_name}
"""

    if tool_name == "WebFetch" and "url" in tool_input:
        error_message += f"- URL: {tool_input['url']}\n"
        error_message += (
            f"Suggested: Use {alternative['tool']} with urls=['{tool_input['url']}']"
        )
    elif tool_name == "WebSearch" and "query" in tool_input:
        error_message += f"- Query: {tool_input['query']}\n"
        error_message += (
            f"Suggested: Use {alternative['tool']} with query='{tool_input['query']}'"
        )

    print(error_message.strip(), file=sys.stderr)
    sys.exit(2)  # Exit code 2 blocks the tool and shows stderr to Claude

# Allow other tools to proceed
sys.exit(0)
