#!/usr/bin/env python3
"""
Notification Hook for Claude Code Memory System
Captures important events and errors for future reference
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

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


def main():
    """Main hook entry point for Notification events"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # Notification hook specific fields
        notification_type = input_data.get("notification_type", "")
        message = input_data.get("message", "")
        severity = input_data.get("severity", "info")  # info, warning, error
        metadata = input_data.get("metadata", {})

        # Skip non-important notifications
        if severity == "info" and "error" not in message.lower():
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

        # Determine memory type based on notification
        if "error" in notification_type.lower() or severity == "error":
            memory_type = "error_solution"
        elif "performance" in message.lower():
            memory_type = "performance_insight"
        else:
            memory_type = "project_context"

        # Create memory content
        content = f"[{severity.upper()}] {notification_type}: {message}"

        # Add context if available
        if "context" in metadata:
            content += f"\nContext: {metadata['context']}"

        # Store memory
        memory_metadata = {
            "hook": "notification",
            "notification_type": notification_type,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            **metadata,
        }

        # Get session ID from environment (currently unused)
        # session_id = os.environ.get("CLAUDE_SESSION_ID")

        memory_manager.store_memory(
            content=content, metadata=memory_metadata, memory_type=memory_type
        )

        # Output success
        sys.exit(0)

    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()
