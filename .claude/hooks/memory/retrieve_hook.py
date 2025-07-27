#!/usr/bin/env python3
"""
Memory Retrieval Hook for Claude Code
Provides context-aware suggestions based on stored memories
"""
import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List


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


class ContextAnalyzer:
    """Analyzes user prompts to determine relevant memories"""

    def __init__(self):
        self.intent_patterns = {
            "error_fixing": [
                r"(?i)error",
                r"(?i)exception",
                r"(?i)bug",
                r"(?i)fix",
                r"(?i)issue",
                r"(?i)problem",
                r"(?i)traceback",
            ],
            "code_implementation": [
                r"(?i)implement",
                r"(?i)create",
                r"(?i)add",
                r"(?i)write",
                r"(?i)function",
                r"(?i)class",
                r"(?i)method",
            ],
            "performance": [
                r"(?i)performance",
                r"(?i)optimize",
                r"(?i)slow",
                r"(?i)speed",
                r"(?i)fast",
                r"(?i)efficient",
            ],
            "search": [
                r"(?i)find",
                r"(?i)search",
                r"(?i)where",
                r"(?i)locate",
                r"(?i)look for",
            ],
        }

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze user prompt to determine intent and context"""
        analysis = {"intents": [], "keywords": [], "memory_types": []}

        # Detect intents
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt):
                    analysis["intents"].append(intent)
                    break

        # Map intents to memory types
        intent_to_memory_type = {
            "error_fixing": ["error_solution"],
            "code_implementation": ["code_pattern", "project_context"],
            "performance": ["performance_insight"],
            "search": ["project_context", "code_pattern"],
        }

        for intent in analysis["intents"]:
            analysis["memory_types"].extend(intent_to_memory_type.get(intent, []))

        # Extract potential keywords (simple approach)
        words = prompt.lower().split()
        # Filter out common words
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "about",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "cant",
        }

        analysis["keywords"] = [
            w for w in words if len(w) > 3 and w not in common_words
        ][:10]

        return analysis


def format_memories_as_tips(memories: List[Dict[str, Any]], max_tips: int = 5) -> str:
    """Format memories as helpful tips for the user"""
    if not memories:
        return ""

    tips = []
    tips.append("\n🧠 Relevant memories from this project:")

    for i, memory in enumerate(memories[:max_tips]):
        memory_type = memory["metadata"].get("memory_type", "general")
        similarity = memory.get("similarity", 0)

        # Format based on memory type
        if memory_type == "error_solution":
            icon = "🔧"
            prefix = "Previous error solution"
        elif memory_type == "code_pattern":
            icon = "📝"
            prefix = "Code pattern"
        elif memory_type == "performance_insight":
            icon = "⚡"
            prefix = "Performance insight"
        elif memory_type == "project_context":
            icon = "📍"
            prefix = "Project context"
        else:
            icon = "💡"
            prefix = "Memory"

        # Truncate content if too long
        content = memory["content"]
        if len(content) > 150:
            content = content[:150] + "..."

        tips.append(f"{icon} {prefix} (similarity: {similarity:.0%}): {content}")

        # Add file context if available
        if "file_path" in memory["metadata"]:
            tips.append(f"   Related file: {memory['metadata']['file_path']}")

    return "\n".join(tips)


def main():
    """Main hook entry point"""
    # Initialize input_data with default value to prevent UnboundLocalError
    input_data = {}

    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # Check if this is a UserPromptSubmit event
        hook_event = input_data.get("hook_event_name", "")
        if hook_event != "UserPromptSubmit":
            sys.exit(0)

        prompt = input_data.get("prompt", "")
        if not prompt:
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

        if not config["memory_system"]["hooks"]["auto_retrieve"]["enabled"]:
            sys.exit(0)

        # Initialize memory manager
        memory_manager = get_memory_manager(project_path)

        # Only proceed if memory manager is available
        if memory_manager is None:
            print(input_data.get("prompt", ""))
            sys.exit(0)

        # Analyze prompt
        analyzer = ContextAnalyzer()
        analysis = analyzer.analyze_prompt(prompt)

        # Search for relevant memories
        memories = []

        # Search by full prompt first
        memories.extend(
            memory_manager.search_memories(
                query=prompt,
                memory_types=(
                    analysis["memory_types"] if analysis["memory_types"] else None
                ),
                limit=config["memory_system"]["hooks"]["auto_retrieve"][
                    "max_suggestions"
                ],
            )
        )

        # If not enough results, search by keywords
        if len(memories) < 3 and analysis["keywords"]:
            keyword_query = " ".join(analysis["keywords"][:5])
            additional_memories = memory_manager.search_memories(
                query=keyword_query, limit=3
            )

            # Add unique memories
            existing_ids = {m["id"] for m in memories}
            for mem in additional_memories:
                if mem["id"] not in existing_ids:
                    memories.append(mem)

        # Format and output memories as tips
        if memories:
            tips = format_memories_as_tips(
                memories,
                max_tips=config["memory_system"]["hooks"]["auto_retrieve"][
                    "max_suggestions"
                ],
            )

            # Add existing prompt
            output = f"{prompt}{tips}"
            print(output)
        else:
            # No memories found, output original prompt
            print(prompt)

        sys.exit(0)

    except Exception:
        # On error, just output the original prompt
        print(input_data.get("prompt", ""))
        sys.exit(0)


if __name__ == "__main__":
    main()
