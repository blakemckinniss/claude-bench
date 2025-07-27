#!/usr/bin/env python3
"""
CLI tool for managing Claude Code memories
"""
import json
import sys
from pathlib import Path
import argparse

# Add memory system to path
sys.path.insert(0, str(Path(__file__).parent))

from memory_manager import get_memory_manager


def list_memories(args):
    """List memories in the project"""
    manager = get_memory_manager(args.project_path)

    memories = manager.list_memories(memory_type=args.type, limit=args.limit)

    if not memories:
        print("No memories found.")
        return

    print(f"\nMemories for project: {Path(args.project_path).name}")
    print("=" * 80)

    for memory in memories:
        print(f"\nID: {memory['id']}")
        print(f"Type: {memory['memory_type']}")
        print(f"Created: {memory['timestamp']}")
        print(f"Accessed: {memory['access_count']} times")
        print(f"Content: {memory['content'][:200]}...")

        if args.verbose and memory["metadata"]:
            print(f"Metadata: {json.dumps(memory['metadata'], indent=2)}")

        print("-" * 40)


def search_memories(args):
    """Search for memories"""
    manager = get_memory_manager(args.project_path)

    memories = manager.search_memories(
        query=args.query,
        memory_types=[args.type] if args.type else None,
        limit=args.limit,
    )

    if not memories:
        print(f"No memories found matching: '{args.query}'")
        return

    print(f"\nSearch results for: '{args.query}'")
    print("=" * 80)

    for memory in memories:
        print(f"\nID: {memory['id']}")
        print(f"Similarity: {memory['similarity']:.2%}")
        print(f"Type: {memory['metadata'].get('memory_type', 'general')}")
        print(f"Content: {memory['content'][:200]}...")

        if args.verbose and memory["metadata"]:
            print(f"Metadata: {json.dumps(memory['metadata'], indent=2)}")

        print("-" * 40)


def add_memory(args):
    """Manually add a memory"""
    manager = get_memory_manager(args.project_path)

    # Read content from file or stdin
    if args.file:
        with open(args.file) as f:
            content = f.read()
    else:
        print("Enter memory content (Ctrl+D to finish):")
        content = sys.stdin.read()

    metadata = {}
    if args.metadata:
        metadata = json.loads(args.metadata)

    memory_id = manager.store_memory(
        content=content.strip(), metadata=metadata, memory_type=args.type
    )

    print(f"\n✓ Memory stored with ID: {memory_id}")


def delete_memory(args):
    """Delete a memory"""
    manager = get_memory_manager(args.project_path)

    if args.all:
        count = manager.clear_project_memories()
        print(f"\n✓ Deleted {count} memories from project")
    else:
        if manager.delete_memory(args.id):
            print(f"\n✓ Deleted memory: {args.id}")
        else:
            print(f"\n✗ Memory not found: {args.id}")


def stats(args):
    """Show memory statistics"""
    manager = get_memory_manager(args.project_path)

    stats = manager.get_stats()

    print(f"\nMemory Statistics for: {Path(args.project_path).name}")
    print("=" * 80)
    print(f"Total memories: {stats['total']}")

    if stats["by_type"]:
        print("\nBy type:")
        for memory_type, type_stats in stats["by_type"].items():
            print(f"  {memory_type}: {type_stats['count']} memories")
            print(f"    Average access count: {type_stats['avg_access_count']:.1f}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Manage Claude Code memories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all memories
  %(prog)s list
  
  # Search for memories
  %(prog)s search "authentication error"
  
  # Add a memory
  %(prog)s add -t code_pattern -f pattern.py
  
  # Delete a memory
  %(prog)s delete <memory_id>
  
  # Show statistics
  %(prog)s stats
        """,
    )

    parser.add_argument(
        "--project-path",
        "-p",
        default=Path.cwd(),
        type=Path,
        help="Project path (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List memories")
    list_parser.add_argument("-t", "--type", help="Filter by memory type")
    list_parser.add_argument(
        "-l", "--limit", type=int, default=50, help="Limit results"
    )
    list_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show metadata"
    )
    list_parser.set_defaults(func=list_memories)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-t", "--type", help="Filter by memory type")
    search_parser.add_argument(
        "-l", "--limit", type=int, default=10, help="Limit results"
    )
    search_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show metadata"
    )
    search_parser.set_defaults(func=search_memories)

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a memory")
    add_parser.add_argument("-t", "--type", default="general", help="Memory type")
    add_parser.add_argument("-f", "--file", help="Read content from file")
    add_parser.add_argument("-m", "--metadata", help="JSON metadata")
    add_parser.set_defaults(func=add_memory)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete memory")
    delete_parser.add_argument("id", nargs="?", help="Memory ID to delete")
    delete_parser.add_argument("--all", action="store_true", help="Delete all memories")
    delete_parser.set_defaults(func=delete_memory)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.set_defaults(func=stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
