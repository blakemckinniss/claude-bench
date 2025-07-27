#!/usr/bin/env python3
"""
PreToolUse Hook for Claude Code Memory System
Provides memory-guided suggestions for tool usage
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


# Import memory manager with robust error handling
def import_memory_manager():
    """Import memory manager with fallback handling"""
    try:
        # Try using __file__ first
        memory_system_path = str(Path(__file__).parent.parent.parent / "memory_system")
    except NameError:
        # Fallback for contexts where __file__ is not defined
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        memory_system_path = str(Path(project_dir) / ".claude" / "memory_system")

    try:
        # Add path and import
        if memory_system_path not in sys.path:
            sys.path.insert(0, memory_system_path)

        # Import the module dynamically
        import importlib.util

        memory_manager_file = Path(memory_system_path) / "memory_manager.py"

        spec = importlib.util.spec_from_file_location(
            "memory_manager", memory_manager_file
        )
        if spec is None or spec.loader is None:
            raise ImportError("Could not load memory_manager module")

        memory_manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory_manager_module)

        return memory_manager_module.get_memory_manager

    except (ImportError, FileNotFoundError, AttributeError):
        # Return stub function for graceful degradation
        def get_memory_manager(*args, **kwargs):
            return None

        return get_memory_manager


# Import the function
get_memory_manager = import_memory_manager()


class ToolSuggestionEngine:
    """Provides memory-based suggestions for tool usage"""

    def __init__(self, memory_manager):
        self.memory_manager = memory_manager

    def get_tool_suggestions(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Optional[str]:
        """Get suggestions based on past tool usage"""
        suggestions = []

        if tool_name == "find_symbol":
            suggestions.extend(self._suggest_for_find_symbol(tool_input))
        elif tool_name == "Bash":
            suggestions.extend(self._suggest_for_bash(tool_input))
        elif tool_name == "Edit" or tool_name == "Write":
            suggestions.extend(self._suggest_for_edit(tool_input))
        elif tool_name == "search_for_pattern":
            suggestions.extend(self._suggest_for_search(tool_input))

        if suggestions:
            return self._format_suggestions(suggestions)
        return None

    def _suggest_for_find_symbol(self, tool_input: Dict[str, Any]) -> List[str]:
        """Suggestions for find_symbol tool"""
        suggestions = []
        name_path = tool_input.get("name_path", "")

        # Search for similar symbol searches
        memories = self.memory_manager.search_memories(
            query=f"find_symbol {name_path}",
            memory_types=["project_context", "code_pattern"],
            limit=3,
        )

        for memory in memories:
            metadata = memory.get("metadata", {})
            if metadata.get("tool") == "find_symbol" and metadata.get("success"):
                pattern = metadata.get("pattern", "")
                if pattern and pattern != name_path:
                    suggestions.append(
                        f"Similar symbol search: '{pattern}' was successful"
                    )

        return suggestions

    def _suggest_for_bash(self, tool_input: Dict[str, Any]) -> List[str]:
        """Suggestions for Bash commands"""
        suggestions = []
        command = tool_input.get("command", "")

        # Check for common error patterns
        if "npm" in command or "yarn" in command:
            # Search for package.json scripts
            memories = self.memory_manager.search_memories(
                query="package.json scripts", memory_types=["project_context"], limit=2
            )

            for memory in memories:
                if "scripts" in memory.get("content", ""):
                    suggestions.append("Check package.json for available scripts")

        # Search for similar commands that failed
        if any(cmd in command for cmd in ["test", "build", "lint"]):
            memories = self.memory_manager.search_memories(
                query=f"{command} error", memory_types=["error_solution"], limit=2
            )

            for memory in memories:
                content = memory.get("content", "")[:100]
                suggestions.append(f"Previous issue: {content}...")

        return suggestions

    def _suggest_for_edit(self, tool_input: Dict[str, Any]) -> List[str]:
        """Suggestions for Edit/Write operations"""
        suggestions = []
        file_path = tool_input.get("file_path", "")

        # Search for code patterns in similar files
        if file_path:
            file_ext = Path(file_path).suffix
            memories = self.memory_manager.search_memories(
                query=f"code pattern {file_ext}", memory_types=["code_pattern"], limit=2
            )

            for memory in memories:
                metadata = memory.get("metadata", {})
                pattern_type = metadata.get("pattern_type", "")
                if pattern_type:
                    suggestions.append(
                        f"Common pattern: {pattern_type} implementations exist"
                    )

        return suggestions

    def _suggest_for_search(self, tool_input: Dict[str, Any]) -> List[str]:
        """Suggestions for search operations"""
        suggestions = []
        pattern = tool_input.get("substring_pattern", "") or tool_input.get(
            "pattern", ""
        )

        # Look for previous successful searches
        memories = self.memory_manager.search_memories(
            query=f"search {pattern}", memory_types=["project_context"], limit=2
        )

        for memory in memories:
            metadata = memory.get("metadata", {})
            if metadata.get("success") and "file" in metadata:
                suggestions.append(f"Previously found in: {metadata['file']}")

        return suggestions

    def _format_suggestions(self, suggestions: List[str]) -> Optional[str]:
        """Format suggestions for output"""
        if not suggestions:
            return None

        output = "\n🧠 Memory-based suggestions:\n"
        for suggestion in suggestions[:3]:  # Limit to 3
            output += f"  • {suggestion}\n"

        return output


def main():
    """Main hook entry point for PreToolUse events"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # PreToolUse specific fields
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Skip if not a relevant tool
        relevant_tools = ["find_symbol", "Bash", "Edit", "Write", "search_for_pattern"]
        if tool_name not in relevant_tools:
            sys.exit(0)

        # Get project path
        project_path = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Load configuration
        config_path = Path(project_path) / ".claude/memory_system/config.json"
        if not config_path.exists():
            sys.exit(0)

        with open(config_path) as f:
            config = json.load(f)

        if not config.get("memory_system", {}).get("enabled", False):
            sys.exit(0)

        # Initialize memory manager
        memory_manager = get_memory_manager(project_path)

        # Only proceed if memory manager is available
        if memory_manager is None:
            sys.exit(0)

        # Get suggestions
        suggestion_engine = ToolSuggestionEngine(memory_manager)
        suggestions = suggestion_engine.get_tool_suggestions(tool_name, tool_input)

        if suggestions:
            # Output suggestions as feedback (exit code 2 with stderr)
            print(suggestions, file=sys.stderr)
            sys.exit(2)
        else:
            # No suggestions, allow tool to proceed
            sys.exit(0)

    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
