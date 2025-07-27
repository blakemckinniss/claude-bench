#!/usr/bin/env python3
"""
Stop Hook for Claude Code Memory System
Saves session summaries and key learnings when a session ends
"""
import json
import os
import sys
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


class SessionSummarizer:
    """Summarizes session activities and extracts key learnings"""

    def __init__(self, memory_manager):
        self.memory_manager = memory_manager

    def summarize_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive session summary"""
        summary = {
            "tools_used": {},
            "files_modified": set(),
            "errors_encountered": [],
            "patterns_discovered": [],
            "key_activities": [],
        }

        # Get session ID
        session_id = session_data.get("session_id", os.environ.get("CLAUDE_SESSION_ID"))

        # Query memories from this session
        if session_id:
            # Get all memories from this session
            memories = self.memory_manager.list_memories(limit=1000)
            session_memories = [
                m
                for m in memories
                if m.get("metadata", {}).get("session_id") == session_id
            ]

            # Analyze memories
            for memory in session_memories:
                memory_type = memory.get("memory_type", "")
                metadata = memory.get("metadata", {})

                # Track tool usage
                tool = metadata.get("tool")
                if tool:
                    summary["tools_used"][tool] = summary["tools_used"].get(tool, 0) + 1

                # Track files
                file_path = metadata.get("file_path")
                if file_path:
                    summary["files_modified"].add(file_path)

                # Track errors
                if memory_type == "error_solution":
                    summary["errors_encountered"].append(
                        {
                            "error": memory.get("content", "")[:100],
                            "type": metadata.get("error_type", "unknown"),
                        }
                    )

                # Track patterns
                if memory_type == "code_pattern":
                    summary["patterns_discovered"].append(
                        {
                            "pattern": metadata.get("pattern_type", ""),
                            "file": metadata.get("file_path", ""),
                        }
                    )

        # Convert sets to lists for JSON serialization
        summary["files_modified"] = list(summary["files_modified"])

        return summary

    def extract_key_learnings(self, summary: Dict[str, Any]) -> List[str]:
        """Extract key learnings from session summary"""
        learnings = []

        # Most used tools
        if summary["tools_used"]:
            top_tools = sorted(
                summary["tools_used"].items(), key=lambda x: x[1], reverse=True
            )[:3]
            tools_str = ", ".join([f"{tool} ({count}x)" for tool, count in top_tools])
            learnings.append(f"Primary tools used: {tools_str}")

        # Files worked on
        if summary["files_modified"]:
            learnings.append(f"Modified {len(summary['files_modified'])} files")

        # Errors encountered
        if summary["errors_encountered"]:
            error_types = set(e["type"] for e in summary["errors_encountered"])
            learnings.append(f"Resolved {len(error_types)} types of errors")

        # Patterns discovered
        if summary["patterns_discovered"]:
            pattern_types = set(p["pattern"] for p in summary["patterns_discovered"])
            learnings.append(f"Discovered {len(pattern_types)} code patterns")

        return learnings


def main():
    """Main hook entry point for Stop events"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # Stop hook specific fields
        session_id = input_data.get("session_id", os.environ.get("CLAUDE_SESSION_ID"))
        exit_reason = input_data.get("exit_reason", "normal")
        session_data = input_data.get("session_data", {})

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

        # Create session summary
        summarizer = SessionSummarizer(memory_manager)
        summary = summarizer.summarize_session(session_data)
        key_learnings = summarizer.extract_key_learnings(summary)

        # Create session summary content
        content = f"Session Summary (Exit: {exit_reason})\n"
        content += "=" * 50 + "\n"

        if key_learnings:
            content += "\nKey Activities:\n"
            for learning in key_learnings:
                content += f"• {learning}\n"

        if summary["tools_used"]:
            content += "\nTools Usage:\n"
            for tool, count in sorted(summary["tools_used"].items()):
                content += f"  - {tool}: {count} times\n"

        # Store session summary
        memory_metadata = {
            "hook": "stop",
            "session_id": session_id,
            "exit_reason": exit_reason,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }

        memory_manager.store_memory(
            content=content, metadata=memory_metadata, memory_type="session_summary"
        )

        # Update session record in database if session_id exists
        if session_id:
            memory_manager.db.execute(
                """
                UPDATE sessions 
                SET end_time = ?, summary = ?, memory_count = ?
                WHERE session_id = ?
            """,
                (
                    datetime.now(),
                    json.dumps(summary),
                    len(summary.get("files_modified", [])),
                    session_id,
                ),
            )
            memory_manager.db.commit()

        # Output success
        sys.exit(0)

    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
