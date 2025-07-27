#!/usr/bin/env python3
"""
PreCompact Hook for Claude Code Memory System
Preserves important memories before context compaction
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
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


class MemoryPreserver:
    """Preserves important memories before compaction"""

    def __init__(self, memory_manager):
        self.memory_manager = memory_manager

    def identify_important_memories(
        self, time_window: int = 24
    ) -> List[Dict[str, Any]]:
        """Identify memories that should be preserved"""
        important_memories = []

        # Get recent memories
        all_memories = self.memory_manager.list_memories(limit=500)

        # Filter by time window (hours)
        cutoff_time = datetime.now() - timedelta(hours=time_window)

        for memory in all_memories:
            memory_time = datetime.fromisoformat(memory["timestamp"])

            # Skip if too old
            if memory_time < cutoff_time:
                continue

            # Calculate importance score
            importance = self._calculate_importance(memory)

            if importance > 0.5:  # Threshold for preservation
                memory["importance_score"] = importance
                important_memories.append(memory)

        # Sort by importance
        important_memories.sort(key=lambda m: m["importance_score"], reverse=True)

        return important_memories[:50]  # Keep top 50

    def _calculate_importance(self, memory: Dict[str, Any]) -> float:
        """Calculate importance score for a memory"""
        score = 0.0

        memory_type = memory.get("memory_type", "")
        access_count = memory.get("access_count", 0)
        content_length = len(memory.get("content", ""))

        # Type-based scoring
        type_scores = {
            "error_solution": 0.8,
            "security_finding": 0.9,
            "architectural_decision": 0.9,
            "performance_insight": 0.7,
            "code_pattern": 0.6,
            "subagent_summary": 0.7,
            "session_summary": 0.5,
        }

        score += type_scores.get(memory_type, 0.3)

        # Access-based scoring
        if access_count > 5:
            score += 0.3
        elif access_count > 2:
            score += 0.2
        elif access_count > 0:
            score += 0.1

        # Content richness scoring
        if content_length > 200:
            score += 0.1

        # Recency bonus
        memory_time = datetime.fromisoformat(memory["timestamp"])
        hours_old = (datetime.now() - memory_time).total_seconds() / 3600

        if hours_old < 1:
            score += 0.2
        elif hours_old < 6:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def create_preservation_summary(self, memories: List[Dict[str, Any]]) -> str:
        """Create a summary of preserved memories"""
        summary = "Pre-Compaction Memory Preservation\n"
        summary += "=" * 50 + "\n"
        summary += f"Preserved {len(memories)} important memories\n\n"

        # Group by type
        by_type = {}
        for memory in memories:
            memory_type = memory.get("memory_type", "general")
            if memory_type not in by_type:
                by_type[memory_type] = []
            by_type[memory_type].append(memory)

        # Summarize each type
        for memory_type, type_memories in by_type.items():
            summary += (
                f"\n{memory_type.replace('_', ' ').title()} ({len(type_memories)}):\n"
            )

            for memory in type_memories[:5]:  # Top 5 per type
                content_preview = memory["content"][:100].replace("\n", " ")
                score = memory.get("importance_score", 0)
                summary += f"  • [{score:.2f}] {content_preview}...\n"

        return summary


def main():
    """Main hook entry point for PreCompact events"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # PreCompact specific fields
        context_size = input_data.get("context_size", 0)
        compaction_reason = input_data.get("reason", "context_limit")
        metadata = input_data.get("metadata", {})

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

        # Preserve important memories
        preserver = MemoryPreserver(memory_manager)
        important_memories = preserver.identify_important_memories()

        # Create preservation record
        preservation_summary = preserver.create_preservation_summary(important_memories)

        # Store preservation record
        preservation_metadata = {
            "hook": "precompact",
            "context_size": context_size,
            "compaction_reason": compaction_reason,
            "preserved_count": len(important_memories),
            "preserved_ids": [m["id"] for m in important_memories],
            "timestamp": datetime.now().isoformat(),
            **metadata,
        }

        memory_manager.store_memory(
            content=preservation_summary,
            metadata=preservation_metadata,
            memory_type="compaction_preservation",
        )

        # Mark preserved memories with higher importance
        for memory in important_memories:
            # Update access count to ensure preservation
            memory_manager._update_access_stats([memory["id"]])

        # If context is being compacted, we might want to output
        # a summary for Claude to see
        if compaction_reason == "user_requested":
            # Output summary for Claude to see (exit code 0 with stdout)
            print(
                f"\n💾 Preserved {len(important_memories)} important memories before compaction"
            )
            print("These memories will remain accessible for future reference.")

        sys.exit(0)

    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
