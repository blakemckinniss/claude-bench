#!/usr/bin/env python3
"""
Performance Monitoring Hook for Claude Code
Tracks execution times and provides performance insights
"""

import json
import sys
import os
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.shared_state import HookStateManager, PerformanceMonitor


class PerformanceAnalyzer:
    """Analyzes performance patterns and provides insights"""

    def __init__(self):
        self.state_manager = HookStateManager()
        self.perf_monitor = PerformanceMonitor()

    def analyze_tool_performance(
        self, tool_name: str, tool_input: Dict[str, Any], execution_time: float
    ) -> List[str]:
        """Analyze tool performance and provide insights"""
        insights = []

        # Get historical performance data
        state = self.state_manager.read_state()
        tool_metrics = state.get("tool_metrics", {}).get(tool_name, {})

        if tool_metrics:
            avg_time = tool_metrics.get("avg_time", 0)

            # Check if this execution was slower than average
            if execution_time > avg_time * 1.5:
                insights.append(
                    f"⚠️ This {tool_name} operation took {execution_time:.2f}s "
                    f"(50% slower than average: {avg_time:.2f}s)"
                )

                # Provide specific suggestions based on tool
                if tool_name == "Read" and execution_time > 0.5:
                    insights.append(
                        "💡 Consider using Serena's find_symbol for code files "
                        "to read only specific functions instead of entire files"
                    )
                elif tool_name == "Bash" and execution_time > 1.0:
                    command = tool_input.get("command", "")
                    if "find" in command:
                        insights.append(
                            "💡 Use 'fd' instead of 'find' for faster file discovery"
                        )
                    elif "grep" in command:
                        insights.append(
                            "💡 Use 'rg' (ripgrep) instead of 'grep' for 10-100x speedup"
                        )

        # Check for patterns that indicate inefficiency
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if file_path.endswith((".py", ".js", ".ts", ".java")):
                # Check file size
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > 10000:  # > 10KB
                        insights.append(
                            f"📊 Large code file ({file_size/1024:.1f}KB). "
                            "Use Serena's get_symbols_overview → find_symbol instead"
                        )
                except (OSError, FileNotFoundError):
                    pass

        return insights

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        state = self.state_manager.read_state()
        tool_metrics = state.get("tool_metrics", {})

        summary = {
            "slowest_tools": [],
            "most_used_tools": [],
            "total_operations": 0,
            "recommendations": [],
        }

        # Find slowest tools
        for tool, metrics in tool_metrics.items():
            avg_time = metrics.get("avg_time", 0)
            count = metrics.get("count", 0)

            if avg_time > 0.5:  # Slower than 500ms
                summary["slowest_tools"].append(
                    {"tool": tool, "avg_time": avg_time, "count": count}
                )

            summary["total_operations"] += count

        # Sort by slowness
        summary["slowest_tools"].sort(key=lambda x: x["avg_time"], reverse=True)

        # Find most used tools
        most_used = sorted(
            [(tool, metrics["count"]) for tool, metrics in tool_metrics.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        summary["most_used_tools"] = most_used

        # Generate recommendations
        if summary["slowest_tools"]:
            slowest = summary["slowest_tools"][0]
            if slowest["tool"] == "Read" and slowest["count"] > 5:
                summary["recommendations"].append(
                    "Consider batching Read operations with read_multiple_files"
                )
            elif slowest["tool"] == "Bash":
                summary["recommendations"].append(
                    "Use modern CLI tools: rg > grep, fd > find, jq for JSON"
                )

        return summary


def format_performance_feedback(insights: List[str], execution_time: float) -> str:
    """Format performance insights for display"""
    if not insights:
        return ""

    feedback = f"\n📊 Performance Insights (execution: {execution_time:.3f}s):\n"
    for insight in insights:
        feedback += f"{insight}\n"

    return feedback


def main():
    """Main hook handler for performance monitoring"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if hook_event == "PostToolUse":
        # Get execution time if available
        tool_response = input_data.get("tool_response", {})

        # Handle both string and dict responses
        if isinstance(tool_response, str):
            execution_time = 0.1  # Default for string responses
        elif isinstance(tool_response, dict):
            execution_time = tool_response.get("execution_time", 0.1)
        else:
            execution_time = 0.1  # Default fallback

        # Create analyzer
        analyzer = PerformanceAnalyzer()
        perf_monitor = PerformanceMonitor()

        # Record performance
        perf_monitor.record_validation_time(tool_name, execution_time)

        # Get performance insights
        insights = analyzer.analyze_tool_performance(
            tool_name, tool_input, execution_time
        )

        # Check for slow operations
        slow_ops = perf_monitor.get_slow_operations(threshold_ms=500)
        if slow_ops:
            insights.append(
                f"⚠️ {len(slow_ops)} tools averaging >500ms: "
                f"{', '.join(op['tool'] for op in slow_ops[:3])}"
            )

        # Provide feedback if there are insights
        if insights:
            feedback = format_performance_feedback(insights, execution_time)

            # Use JSON output for better control
            output = {
                "decision": "allow",  # Don't block, just inform
                "feedback": feedback,
            }
            print(json.dumps(output))

        # Periodically show performance summary
        state = analyzer.state_manager.read_state()
        total_ops = sum(
            m.get("count", 0) for m in state.get("tool_metrics", {}).values()
        )

        if total_ops % 50 == 0:  # Every 50 operations
            summary = analyzer.get_performance_summary()
            if summary["recommendations"]:
                print(
                    f"\n📈 Performance Summary after {total_ops} operations:",
                    file=sys.stderr,
                )
                for rec in summary["recommendations"]:
                    print(f"• {rec}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
