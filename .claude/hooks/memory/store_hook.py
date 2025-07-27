#!/usr/bin/env python3
"""
Memory Storage Hook for Claude Code
Automatically stores relevant code patterns, solutions, and insights
"""
import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional, List


# Add memory system to path - robust approach
def get_memory_system_path():
    """Get the memory system path robustly"""
    try:
        # Try using __file__ first
        return str(Path(__file__).parent.parent.parent / "memory_system")
    except NameError:
        # Fallback for contexts where __file__ is not defined
        # Get from CLAUDE_PROJECT_DIR or current working directory
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        return str(Path(project_dir) / ".claude" / "memory_system")


# Import memory manager with proper error handling
def import_memory_manager():
    """Import memory manager with fallback handling"""
    memory_system_path = get_memory_system_path()

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

        return (
            memory_manager_module.get_memory_manager,
            memory_manager_module.MemoryConfig,
        )

    except (ImportError, FileNotFoundError, AttributeError):
        # Return stub functions for graceful degradation
        def get_memory_manager(*args, **kwargs):
            return None

        class MemoryConfig:
            def __init__(self, *args, **kwargs):
                pass

        return get_memory_manager, MemoryConfig


# Import the functions
get_memory_manager, MemoryConfig = import_memory_manager()


class MemoryExtractor:
    """Extracts meaningful memories from tool interactions"""

    def __init__(self):
        self.patterns = {
            "error_solution": [
                r"(?i)error:?\s*(.+?)(?:\n|$)",
                r"(?i)exception:?\s*(.+?)(?:\n|$)",
                r"(?i)traceback.*?(?=\n\n|$)",
            ],
            "code_pattern": [
                r"def\s+\w+\s*\([^)]*\):[^}]+",
                r"class\s+\w+[^}]+",
                r"(?:async\s+)?function\s+\w+\s*\([^)]*\)[^}]+",
            ],
            "performance_insight": [
                r"(?i)performance:?\s*(.+?)(?:\n|$)",
                r"(?i)optimiz\w+:?\s*(.+?)(?:\n|$)",
                r"(?i)slow\w*:?\s*(.+?)(?:\n|$)",
            ],
        }

    def extract_memories(
        self, tool_name: str, tool_input: Dict[str, Any], tool_response: Any
    ) -> List[Dict[str, Any]]:
        """Extract memories from tool interaction"""
        memories = []

        # Handle different tool types
        if tool_name == "Edit" or tool_name == "Write":
            memories.extend(
                self._extract_from_code_edit(tool_name, tool_input, tool_response)
            )
        elif tool_name == "Debug" or tool_name == "Bash":
            memories.extend(
                self._extract_from_execution(tool_name, tool_input, tool_response)
            )
        elif tool_name in ["find_symbol", "search_for_pattern"]:
            memories.extend(
                self._extract_from_search(tool_name, tool_input, tool_response)
            )

        return memories

    def _extract_from_code_edit(
        self, tool_name: str, tool_input: Dict[str, Any], tool_response: Any
    ) -> List[Dict[str, Any]]:
        """Extract patterns from code edits"""
        memories = []

        if "new_string" in tool_input:
            content = tool_input["new_string"]
        elif "content" in tool_input:
            content = tool_input["content"]
        else:
            return memories

        # Extract function/class definitions
        for pattern in self.patterns["code_pattern"]:
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            for match in matches[:3]:  # Limit to avoid noise
                if len(match) > 50 and len(match) < 1000:
                    memories.append(
                        {
                            "content": match,
                            "memory_type": "code_pattern",
                            "metadata": {
                                "tool": tool_name,
                                "file_path": tool_input.get("file_path", "unknown"),
                                "pattern_type": (
                                    "function"
                                    if "def" in match or "function" in match
                                    else "class"
                                ),
                            },
                        }
                    )

        return memories

    def _extract_from_execution(
        self, tool_name: str, tool_input: Dict[str, Any], tool_response: Any
    ) -> List[Dict[str, Any]]:
        """Extract insights from command execution"""
        memories = []

        response_text = str(tool_response) if tool_response else ""

        # Look for errors and their resolutions
        if "error" in response_text.lower():
            error_context = self._extract_error_context(response_text)
            if error_context:
                memories.append(
                    {
                        "content": error_context,
                        "memory_type": "error_solution",
                        "metadata": {
                            "tool": tool_name,
                            "command": tool_input.get("command", ""),
                            "error_type": self._classify_error(error_context),
                        },
                    }
                )

        return memories

    def _extract_from_search(
        self, tool_name: str, tool_input: Dict[str, Any], tool_response: Any
    ) -> List[Dict[str, Any]]:
        """Extract insights from search results"""
        memories = []

        # Store successful search patterns
        if tool_response and "results" in str(tool_response):
            search_pattern = tool_input.get("pattern", "") or tool_input.get(
                "name_path", ""
            )
            if search_pattern:
                memories.append(
                    {
                        "content": f"Search pattern '{search_pattern}' found results in project",
                        "memory_type": "project_context",
                        "metadata": {
                            "tool": tool_name,
                            "pattern": search_pattern,
                            "success": True,
                        },
                    }
                )

        return memories

    def _extract_error_context(self, error_text: str) -> Optional[str]:
        """Extract meaningful error context"""
        lines = error_text.split("\n")
        error_lines = []

        for i, line in enumerate(lines):
            if "error" in line.lower() or "exception" in line.lower():
                # Get surrounding context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                error_lines = lines[start:end]
                break

        return "\n".join(error_lines) if error_lines else None

    def _classify_error(self, error_text: str) -> str:
        """Classify error type"""
        error_lower = error_text.lower()

        if "syntax" in error_lower:
            return "syntax_error"
        elif "type" in error_lower:
            return "type_error"
        elif "import" in error_lower or "module" in error_lower:
            return "import_error"
        elif "permission" in error_lower:
            return "permission_error"
        else:
            return "general_error"


def main():
    """Main hook entry point"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # Check if this is a relevant event
        hook_event = input_data.get("hook_event_name", "")
        if hook_event != "PostToolUse":
            return

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})

        # Skip certain tools
        excluded_tools = ["Read", "LS", "Bash", "TodoWrite"]
        if tool_name in excluded_tools:
            return

        # Get project path
        project_path = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Load configuration
        config_path = Path(project_path) / ".claude/memory_system/config.json"
        if not config_path.exists():
            return

        with open(config_path) as f:
            config = json.load(f)

        if not config.get("memory_system", {}).get("enabled", False):
            return

        # Initialize memory manager
        memory_manager = get_memory_manager(project_path)

        # Only proceed if memory manager is available
        if memory_manager is not None:
            # Extract memories
            extractor = MemoryExtractor()
            memories = extractor.extract_memories(tool_name, tool_input, tool_response)

            # Store memories
            stored_count = 0
            for memory in memories:
                if (
                    len(memory["content"])
                    >= config["memory_system"]["hooks"]["auto_store"][
                        "min_content_length"
                    ]
                ):
                    try:
                        memory_manager.store_memory(
                            content=memory["content"],
                            metadata=memory["metadata"],
                            memory_type=memory["memory_type"],
                        )
                        stored_count += 1
                    except Exception:
                        # Log but don't fail
                        pass

        # Output success (no feedback to user in PostToolUse)
        sys.exit(0)

    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
