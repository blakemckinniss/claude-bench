#!/usr/bin/env python3
"""
SubagentStop Hook for Claude Code Memory System
Captures discoveries and insights from Task subagents
"""
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add memory system to path
memory_system_path = str(Path(__file__).parent.parent.parent / "memory_system")
if memory_system_path not in sys.path:
    sys.path.insert(0, memory_system_path)


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


class SubagentAnalyzer:
    """Analyzes subagent results to extract valuable memories"""

    def __init__(self):
        self.agent_type_patterns = {
            "code-reviewer": {
                "patterns": [
                    r"(?i)issue found:?\s*(.+?)(?:\n|$)",
                    r"(?i)recommendation:?\s*(.+?)(?:\n|$)",
                    r"(?i)best practice:?\s*(.+?)(?:\n|$)",
                ],
                "memory_type": "code_quality",
            },
            "security-auditor": {
                "patterns": [
                    r"(?i)vulnerability:?\s*(.+?)(?:\n|$)",
                    r"(?i)security issue:?\s*(.+?)(?:\n|$)",
                    r"(?i)CVE-\d{4}-\d+",
                ],
                "memory_type": "security_finding",
            },
            "performance-engineer": {
                "patterns": [
                    r"(?i)bottleneck:?\s*(.+?)(?:\n|$)",
                    r"(?i)optimization:?\s*(.+?)(?:\n|$)",
                    r"(?i)performance.*?(\d+%)",
                ],
                "memory_type": "performance_insight",
            },
            "debugger": {
                "patterns": [
                    r"(?i)root cause:?\s*(.+?)(?:\n|$)",
                    r"(?i)fix:?\s*(.+?)(?:\n|$)",
                    r"(?i)solution:?\s*(.+?)(?:\n|$)",
                ],
                "memory_type": "error_solution",
            },
        }

    def extract_insights(self, agent_type: str, result: str) -> List[Dict[str, Any]]:
        """Extract insights based on agent type"""
        insights = []

        # Get patterns for this agent type
        agent_info = self.agent_type_patterns.get(agent_type, {})
        patterns = agent_info.get("patterns", [])
        memory_type = agent_info.get("memory_type", "subagent_discovery")

        # Extract matches
        for pattern in patterns:
            matches = re.findall(pattern, result, re.MULTILINE | re.IGNORECASE)
            for match in matches[:5]:  # Limit to avoid noise
                if isinstance(match, tuple):
                    match = match[0]

                if len(match) > 30:  # Meaningful content
                    insights.append(
                        {
                            "content": match.strip(),
                            "memory_type": memory_type,
                            "agent_type": agent_type,
                        }
                    )

        # Also extract code blocks if present
        code_blocks = re.findall(r"```[\w]*\n(.*?)\n```", result, re.DOTALL)
        for code in code_blocks[:3]:  # Limit code blocks
            if 20 < len(code) < 500:  # Reasonable size
                insights.append(
                    {
                        "content": code,
                        "memory_type": "code_pattern",
                        "agent_type": agent_type,
                    }
                )

        return insights

    def extract_files_analyzed(self, result: str) -> List[str]:
        """Extract files that were analyzed by the subagent"""
        files = []

        # Common patterns for file references
        patterns = [
            r"(?:file|File):\s*([^\s\n]+\.[a-zA-Z]+)",
            r"(?:in|In)\s+([^\s\n]+\.[a-zA-Z]+)",
            r"([\/\w\-\.]+\.[a-zA-Z]+)(?:\s|:|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, result)
            files.extend(matches)

        # Deduplicate and clean
        return list(set(f for f in files if len(f) > 5 and "/" in f))


def main():
    """Main hook entry point for SubagentStop events"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # SubagentStop specific fields
        agent_type = input_data.get("agent_type", "general-purpose")
        task_description = input_data.get("task_description", "")
        result = input_data.get("result", "")
        success = input_data.get("success", True)
        metadata = input_data.get("metadata", {})

        # Skip if no meaningful result
        if not result or len(result) < 50:
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

        # Analyze subagent results
        analyzer = SubagentAnalyzer()
        insights = analyzer.extract_insights(agent_type, result)
        files_analyzed = analyzer.extract_files_analyzed(result)

        # Store main subagent result summary
        summary_content = (
            f"Subagent [{agent_type}] completed: {task_description[:100]}...\n"
        )
        if not success:
            summary_content += "Status: FAILED\n"

        summary_content += f"\nKey insights discovered: {len(insights)}"
        if files_analyzed:
            summary_content += f"\nFiles analyzed: {len(files_analyzed)}"

        # Store summary
        summary_metadata = {
            "hook": "subagent_stop",
            "agent_type": agent_type,
            "task_description": task_description,
            "success": success,
            "files_analyzed": files_analyzed[:10],  # Limit for metadata
            "insight_count": len(insights),
            "timestamp": datetime.now().isoformat(),
            **metadata,
        }

        memory_manager.store_memory(
            content=summary_content,
            metadata=summary_metadata,
            memory_type="subagent_summary",
        )

        # Store individual insights
        for insight in insights:
            insight_metadata = {
                "hook": "subagent_stop",
                "agent_type": agent_type,
                "task_description": task_description[:100],
                "timestamp": datetime.now().isoformat(),
            }

            # Add file context if available
            if files_analyzed:
                insight_metadata["related_files"] = files_analyzed[:5]

            memory_manager.store_memory(
                content=insight["content"],
                metadata=insight_metadata,
                memory_type=insight["memory_type"],
            )

        # Output success
        sys.exit(0)

    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
