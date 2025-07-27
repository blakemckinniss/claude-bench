#!/usr/bin/env python3
"""
Claude Guidelines Enforcer Hook
Smartly refactored version with balanced functionality for reasonable enforcement
"""

import json
import sys
import re
import os
from typing import Dict, Any, List, Optional, Set, Tuple
from functools import lru_cache
from datetime import datetime


class CompiledPatterns:
    """Pre-compiled regex patterns for performance"""
    
    def __init__(self) -> None:
        # Bash command patterns
        self.grep_pattern = re.compile(r'\b(grep|egrep|fgrep)\s+(?!-[Vvh])', re.IGNORECASE)
        self.find_pattern = re.compile(r'\bfind\s+[^\s]+\s+-name', re.IGNORECASE)
        self.cat_pattern = re.compile(r'\bcat\s+[^\s]+\s*\|', re.IGNORECASE)
        self.json_parse_pattern = re.compile(r'(sed|awk|grep).*[\"\'].*:.*[\"\'].*json', re.IGNORECASE)
        
        # Sequential operation patterns
        self.sequential_git_pattern = re.compile(r'(git\s+(status|diff|log))', re.IGNORECASE)
        self.sequential_file_pattern = re.compile(r'(Read|read_file|get_file_contents)', re.IGNORECASE)
        
        # Complex task patterns
        self.security_pattern = re.compile(r'(security|vulnerability|audit|OWASP|penetration|exploit)', re.IGNORECASE)
        self.performance_pattern = re.compile(r'(performance|optimize|bottleneck|profil|slow|latency)', re.IGNORECASE)
        self.debug_pattern = re.compile(r'(debug|error|exception|stack\s*trace|bug|crash)', re.IGNORECASE)
        self.review_pattern = re.compile(r'(review|code\s*quality|best\s*practice|refactor)', re.IGNORECASE)


class SessionState:
    """Track session state for batch detection"""
    
    def __init__(self) -> None:
        self.tool_sequence: List[str] = []
        self.file_operations: List[str] = []
        self.git_operations: List[str] = []
        self.last_operation_time: Optional[datetime] = None
        self.complex_task_hints: Set[str] = set()
        
    def add_operation(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Track operation for pattern detection"""
        self.tool_sequence.append(tool_name)
        if len(self.tool_sequence) > 10:
            self.tool_sequence.pop(0)
            
        # Track specific operation types
        if tool_name in ["Read", "mcp__filesystem__read_file"]:
            file_path = tool_input.get("file_path", tool_input.get("path", ""))
            self.file_operations.append(file_path)
            
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if "git" in command:
                self.git_operations.append(command)
                
        self.last_operation_time = datetime.now()
        
    def detect_batch_opportunity(self) -> Optional[str]:
        """Detect if recent operations could be batched"""
        # Check for multiple file reads
        if len(self.file_operations) >= 3:
            recent_files = self.file_operations[-3:]
            self.file_operations = []  # Reset
            return f"Multiple file reads detected: {recent_files}. Consider using read_multiple_files for batch reading."
            
        # Check for sequential git operations
        if len(self.git_operations) >= 2:
            recent_git = self.git_operations[-2:]
            self.git_operations = []  # Reset
            return f"Sequential git operations detected. Consider running in parallel: {recent_git}"
            
        return None


class GuidelinesEnforcer:
    """Main enforcer with balanced functionality"""
    
    def __init__(self) -> None:
        self.patterns = CompiledPatterns()
        self.session_state = SessionState()
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with defaults"""
        return {
            "enforce_modern_tools": True,
            "suggest_batching": True,
            "detect_complex_tasks": True,
            "block_dangerous_operations": True,
            "suggest_subagents": True
        }
        
    @lru_cache(maxsize=100)
    def check_bash_command(self, command: str) -> Tuple[bool, List[str]]:
        """Check bash command for guideline violations"""
        issues: List[str] = []
        suggestions: List[str] = []
        
        # Check for grep usage
        if self.patterns.grep_pattern.search(command):
            suggestions.append("🚀 Use 'rg' (ripgrep) instead of grep - it's 10-100x faster!")
            
        # Check for find usage
        if self.patterns.find_pattern.search(command):
            suggestions.append("🚀 Use 'fd' instead of find - it's simpler and faster!")
            
        # Check for inefficient cat usage
        if self.patterns.cat_pattern.search(command):
            suggestions.append("🚀 Avoid 'cat file | grep' - use 'rg pattern file' directly!")
            
        # Check for JSON parsing with sed/awk
        if self.patterns.json_parse_pattern.search(command):
            issues.append("❌ Never parse JSON with sed/awk/grep! Use 'jq' instead.")
            
        # Dangerous operations check
        if self._is_dangerous_command(command):
            issues.append("🛑 DANGEROUS OPERATION DETECTED! This command could harm the system.")
            
        return (len(issues) > 0, suggestions + issues)
        
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous"""
        dangerous_patterns = [
            r'rm\s+-rf\s+/',  # rm -rf /
            r':()\s*{\s*:\|:&\s*}',  # Fork bomb
            r'dd\s+if=/dev/(zero|random)\s+of=/',  # Dangerous dd
            r'chmod\s+-R\s+777\s+/',  # Dangerous permissions
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False
        
    def detect_complex_task(self, prompt: str) -> Optional[str]:
        """Detect if task should use specialized subagent"""
        prompt_lower = prompt.lower()
        
        if self.patterns.security_pattern.search(prompt):
            return "security-auditor"
        elif self.patterns.performance_pattern.search(prompt):
            return "performance-engineer"
        elif self.patterns.debug_pattern.search(prompt):
            return "debugger"
        elif self.patterns.review_pattern.search(prompt):
            return "code-reviewer"
            
        # Check for general complex search
        if "find" in prompt_lower and ("all" in prompt_lower or "every" in prompt_lower):
            return "general-purpose"
            
        return None
        
    def validate_operation(self, hook_event: str, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Main validation logic"""
        should_block = False
        messages: List[str] = []
        
        # Track operation
        self.session_state.add_operation(tool_name, tool_input)
        
        # Pre-operation checks
        if hook_event == "PreToolUse":
            # Check bash commands
            if tool_name == "Bash" and self.config["enforce_modern_tools"]:
                command = tool_input.get("command", "")
                block, issues = self.check_bash_command(command)
                if block and self.config["block_dangerous_operations"]:
                    should_block = True
                messages.extend(issues)
                
            # Check for Task tool usage
            elif tool_name == "Task" and self.config["suggest_subagents"]:
                prompt = tool_input.get("prompt", "")
                if prompt.startswith("/"):
                    messages.append("✅ Executing slash command - good practice!")
                    
        # Post-operation checks
        elif hook_event == "PostToolUse":
            # Check for batch opportunities
            if self.config["suggest_batching"]:
                batch_suggestion = self.session_state.detect_batch_opportunity()
                if batch_suggestion:
                    messages.append(f"💡 BATCH OPPORTUNITY: {batch_suggestion}")
                    
        # User message analysis
        elif hook_event == "UserMessage" and self.config["detect_complex_tasks"]:
            message = tool_input.get("message", "")
            suggested_agent = self.detect_complex_task(message)
            if suggested_agent:
                messages.append(
                    f"💡 COMPLEX TASK DETECTED! Consider using Task with subagent_type='{suggested_agent}' "
                    f"for better results and to save context."
                )
                
        return (should_block, messages)


def main() -> None:
    """Main hook handler"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"❌ HOOK ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
        
    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    
    enforcer = GuidelinesEnforcer()
    should_block, messages = enforcer.validate_operation(hook_event, tool_name, tool_input)
    
    # Output messages
    if messages:
        print("=" * 60, file=sys.stderr)
        print("📋 CLAUDE GUIDELINES CHECK", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for message in messages:
            print(message, file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
    # Block only for dangerous operations
    if should_block:
        print("🛑 OPERATION BLOCKED FOR SAFETY! 🛑", file=sys.stderr)
        sys.exit(2)
        
    sys.exit(0)


if __name__ == "__main__":
    main()