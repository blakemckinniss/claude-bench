# Performance Optimization Guidelines

## Core Principles

### ⚡ ALWAYS Use Optimal Bash Commands

1. **Modern Tool Replacements**
   - ❌ NEVER: Use `grep` when `rg` (ripgrep) is available
   - ❌ NEVER: Parse JSON with sed/awk when `jq` is available
   - ✅ ALWAYS: Use `rg` for fast pattern searching
   - ✅ ALWAYS: Use `jq` for JSON processing
   - ✅ ALWAYS: Use `fd` instead of `find` when available
   - ✅ ALWAYS: Use `bat` instead of `cat` for syntax highlighting

2. **Command Preferences**
   ```bash
   # Bad: Traditional slow commands
   grep -r "pattern" .
   find . -name "*.js"
   cat file.py | grep "function"
   
   # Good: Modern fast commands
   rg "pattern"
   fd "*.js"
   rg "function" file.py
   ```

3. **JSON Processing**
   ```bash
   # Bad: Complex sed/awk/grep chains
   cat package.json | grep version | sed 's/.*: "//' | sed 's/",//'
   
   # Good: Clean jq usage
   jq -r '.version' package.json
   ```

### 🤖 ALWAYS Use Task Subagents for Complex Operations

1. **Delegate to Specialized Agents**
   - ❌ NEVER: Do complex multi-step work yourself when a specialized agent exists
   - ✅ ALWAYS: Use Task tool to launch specialized subagents
   - ✅ ALWAYS: Check if task matches any agent description before starting work

2. **Reduce Context Usage**
   - ❌ NEVER: Perform extensive file searches yourself
   - ✅ ALWAYS: Use Task(subagent_type="general-purpose") for file discovery
   - ✅ ALWAYS: Let subagents handle large-scale analysis

3. **Common Subagent Usage**
   ```
   # Code Review
   Task(description="Review auth code", prompt="/review auth.py", subagent_type="code-reviewer")
   
   # Security Analysis
   Task(description="Security audit", prompt="Audit API endpoints", subagent_type="security-auditor")
   
   # Performance Issues
   Task(description="Find bottlenecks", prompt="Analyze slow queries", subagent_type="performance-engineer")
   
   # General Search/Analysis
   Task(description="Find login code", prompt="Find all authentication logic", subagent_type="general-purpose")
   ```

### 🚀 ALWAYS Batch and Parallelize Operations

1. **Batch Similar Operations**
   - ❌ NEVER: Make sequential tool calls for similar operations
   - ✅ ALWAYS: Group operations and execute in a single tool call
   - ✅ ALWAYS: Use tools that support batch operations when available

2. **Parallelize Independent Operations**
   - ❌ NEVER: Execute independent operations sequentially
   - ✅ ALWAYS: Send multiple tool calls in a single message
   - ✅ ALWAYS: Run git status, git diff, and other checks in parallel

3. **Examples of Parallel Execution**
   ```
   # Bad: Sequential calls
   1. Run git status
   2. Wait for result
   3. Run git diff
   4. Wait for result
   
   # Good: Parallel calls in single message
   1. Send message with:
      - git status (tool call 1)
      - git diff (tool call 2)
      - git log --oneline -10 (tool call 3)
   ```

## Tool Selection for File Operations

### Use Serena Tools for Code Files
When working with code files (.py, .js, .ts, .java, .cpp, etc.), **ALWAYS prefer Serena tools** over standard Read/Write operations:

1. **Reading Code**
   - ❌ AVOID: Using Read tool for entire source files
   - ✅ USE: `get_symbols_overview` → `find_symbol` with `include_body=True` for specific functions/classes
   - ✅ USE: `search_for_pattern` for finding specific code patterns

2. **Editing Code**
   - ❌ AVOID: Read entire file → modify → Write entire file
   - ✅ USE: `replace_symbol_body` for replacing entire functions/methods/classes
   - ✅ USE: `replace_regex` for small, targeted edits within functions
   - ✅ USE: `insert_before_symbol`/`insert_after_symbol` for adding new code

3. **Code Discovery**
   - ❌ AVOID: Reading multiple files to find implementations
   - ✅ USE: `find_symbol` with substring matching
   - ✅ USE: `find_referencing_symbols` to trace usage
   - ✅ USE: `search_for_pattern` for text-based searches

### Use Filesystem MCP for Bulk Operations
When working with multiple files or need file system metadata:

1. **Bulk File Operations** (ALWAYS BATCH!)
   - ✅ USE: `read_multiple_files` when reading several files at once
   - ✅ USE: `directory_tree` for visualizing project structure
   - ✅ USE: `search_files` for pattern-based file discovery across directories
   - 🚀 ALWAYS: Read all needed files in ONE `read_multiple_files` call
   - 🚀 ALWAYS: Batch file searches into single operations

2. **File System Management**
   - ✅ USE: `move_file` for renaming or moving files
   - ✅ USE: `create_directory` for setting up directory structures
   - ✅ USE: `get_file_info` for metadata (size, permissions, timestamps)
   - ✅ USE: `list_directory_with_sizes` for directory contents with sizes

3. **Exploration & Discovery**
   - ✅ USE: `search_files` with exclude patterns for targeted searches
   - ✅ USE: `directory_tree` before activating Serena to understand structure
   - ✅ USE: `list_allowed_directories` to check accessible paths

4. **Preview Operations**
   - ✅ USE: `edit_file` with `dryRun=true` to preview changes as diffs

### Use Standard Tools for Simple Operations
For basic single-file operations:
- ✅ USE: Read/Write/Edit for simple .json, .yaml, .md, .txt files
- ✅ USE: MultiEdit for multiple changes to the same non-code file
- ✅ USE: Standard Read when you need entire file content quickly

## Performance Rules

1. **ALWAYS use Task subagents** - Delegate complex work to specialized agents
2. **ALWAYS batch and parallelize** - Multiple operations in single messages
3. **ALWAYS use optimal commands** - rg > grep, jq for JSON, fd > find
4. **Never read an entire code file unless absolutely necessary** - This wastes tokens and time
5. **Use symbolic navigation** - Jump directly to the code you need
6. **Batch operations** - Use `find_symbol` with `depth=1` to see all methods before reading specific ones
7. **Smart searching** - Use `search_for_pattern` with context lines instead of reading entire files
8. **Parallel git operations** - Always run git status, diff, log in parallel
9. **Batch file reads** - Use `read_multiple_files` for reading 2+ files
10. **Parallel independent tasks** - Run unrelated operations simultaneously
11. **Delegate file searches** - Use Task for extensive searches to save context
12. **Use modern CLI tools** - Prefer fast, modern alternatives

## Examples

### Using Task Subagents

#### Bad Pattern (Doing everything yourself - SLOW!)
```
1. Search for authentication code manually
2. Read 20 files looking for patterns
3. Analyze security issues yourself
4. Write recommendations
```

#### Good Pattern (Delegate to subagent - FAST!)
```
1. Task(description="Audit auth", prompt="Find and audit all authentication code", subagent_type="security-auditor")
```

#### Bad Pattern (Complex debugging yourself)
```
1. Read error logs
2. Search for related code
3. Read multiple files
4. Trace execution paths
5. Find root cause
```

#### Good Pattern (Let debugger agent handle it)
```
1. Task(description="Debug error", prompt="Debug 'NullPointerException in UserService.authenticate()'", subagent_type="debugger")
```

### Code Operations

#### Bad Pattern (Slow)
```
1. Read entire user.py file (500 lines)
2. Find the login() method manually
3. Edit in memory
4. Write entire file back
```

#### Good Pattern (Fast with Serena)
```
1. find_symbol("User/login", relative_path="user.py", include_body=True)
2. replace_symbol_body("User/login", relative_path="user.py", body="new implementation")
```

### Bulk File Operations

#### Bad Pattern (Sequential calls - SLOW!)
```
1. Read file1.json
2. Wait for result
3. Read file2.json  
4. Wait for result
5. Read file3.json
6. Wait for result
7. Read config.yaml
8. Wait for result
```

#### Good Pattern (Batch read - FAST!)
```
1. read_multiple_files(["file1.json", "file2.json", "file3.json", "config.yaml"])
```

### Parallel Git Operations

#### Bad Pattern (Sequential - SLOW!)
```
1. Run git status
2. Wait for result
3. Run git diff
4. Wait for result  
5. Run git log
6. Wait for result
```

#### Good Pattern (Parallel - FAST!)
```
Send single message with 3 tool calls:
- Bash: git status
- Bash: git diff --staged
- Bash: git log --oneline -10
All execute in parallel!
```

### Code Analysis Pattern

#### Bad Pattern (Sequential searches - SLOW!)
```
1. find_symbol("login")
2. Wait for result
3. find_symbol("authenticate")  
4. Wait for result
5. find_symbol("validate")
6. Wait for result
```

#### Good Pattern (Batch discovery - FAST!)
```
Send single message with multiple tool calls:
- find_symbol("login", substring_matching=True)
- find_symbol("authenticate", substring_matching=True)
- find_symbol("validate", substring_matching=True)
- search_for_pattern("password.*hash")
All execute in parallel!
```

### File Discovery

#### Bad Pattern (Trial and error)
```
1. List directory /src
2. List directory /src/components
3. Read random files looking for a pattern
```

#### Good Pattern (Fast with Filesystem MCP)
```
1. search_files(path="/src", pattern="login.*handler", excludePatterns=["*test*"])
```

## Web Search Policy

### MANDATORY: Use Tavily MCP for All Web Operations
WebFetch and WebSearch tools are **BLOCKED**. Always use Tavily MCP tools instead:

1. **For Web Searches**
   - ❌ BLOCKED: WebSearch
   - ✅ USE: `mcp__tavily-remote__tavily_search`

2. **For Extracting Web Content**
   - ❌ BLOCKED: WebFetch
   - ✅ USE: `mcp__tavily-remote__tavily_extract`

3. **For Crawling Websites**
   - ✅ USE: `mcp__tavily-remote__tavily_crawl`

4. **For Site Mapping**
   - ✅ USE: `mcp__tavily-remote__tavily_map`

### Why Tavily MCP?
- More powerful search capabilities
- Better content extraction
- Site crawling and mapping features
- Consistent API across all web operations

## Exceptions
- Use standard Read when you need to understand overall file structure of a non-code file
- Use standard Write for creating new non-code files
- Use standard tools when Serena isn't activated or available

## 🚀 Batch & Parallel Processing Mandate

### CRITICAL: This is NOT optional!

1. **Multiple Files**: ALWAYS use `read_multiple_files` instead of multiple Read calls
2. **Git Operations**: ALWAYS run git commands in parallel (status, diff, log, etc.)
3. **Code Searches**: ALWAYS batch `find_symbol` and `search_for_pattern` calls
4. **Independent Tasks**: ALWAYS execute unrelated operations in parallel
5. **File Discovery**: ALWAYS batch directory listings and file searches

### Remember:
- **Sequential = Slow = Bad** ❌
- **Batch/Parallel = Fast = Good** ✅
- When in doubt, batch it!
- Multiple tool calls in ONE message = Parallel execution

## 🤖 Task Subagents Guide

### When to Use Subagents

1. **ALWAYS use subagents for:**
   - Complex multi-step tasks
   - Extensive file searches
   - Code reviews and analysis
   - Security audits
   - Performance debugging
   - Architecture decisions
   - Test generation
   - Documentation tasks

2. **Available Specialized Agents:**
   
   **Code Quality & Review:**
   - `code-reviewer`: Code reviews, quality analysis
   - `architect-reviewer`: Architectural consistency
   - `python-pro`: Python-specific optimizations
   - `nodejs-fullstack`: Node.js patterns
   - `golang-microservices`: Go service development
   - `react-specialist`: React performance
   - `rust-systems-programmer`: Rust code
   
   **Security & Compliance:**
   - `security-auditor`: OWASP compliance, vulnerability scanning
   - `penetration-tester`: Security testing
   - `compliance-officer`: GDPR, HIPAA, SOC2
   
   **Performance & Debugging:**
   - `performance-engineer`: Profiling, optimization
   - `debugger`: Error resolution
   - `memory-leak-detective`: Memory issues
   - `concurrency-debugger`: Race conditions
   - `network-troubleshooter`: Connectivity issues
   
   **Infrastructure & DevOps:**
   - `terraform-architect`: Infrastructure as Code
   - `kubernetes-operator`: K8s optimization
   - `cloud-architect`: AWS/Azure/GCP
   - `sre-engineer`: Reliability patterns
   - `deployment-engineer`: CI/CD pipelines
   - `devops-troubleshooter`: Production issues
   
   **Data & ML:**
   - `ml-engineer`: ML pipelines
   - `mlops-engineer`: Model deployment
   - `data-engineer`: ETL pipelines
   - `analytics-engineer`: dbt models
   - `data-scientist`: Data analysis
   - `computer-vision-engineer`: Image processing
   - `ai-engineer`: LLM applications
   - `llm-integration-specialist`: RAG implementation
   
   **Testing & Documentation:**
   - `test-automator`: Test suite creation
   - `technical-writer`: API docs
   - `api-documenter`: OpenAPI specs
   
   **Specialized Tasks:**
   - `legacy-modernizer`: Refactoring legacy code
   - `monolith-decomposer`: Microservices migration
   - `database-optimizer`: Query optimization
   - `database-migrator`: Schema evolution
   - `framework-upgrader`: Version migrations
   - `accessibility-champion`: WCAG compliance
   - `product-engineer`: Feature implementation
   - `dx-optimizer`: Developer experience
   - `incident-responder`: Production incidents
   
   **General Purpose:**
   - `general-purpose`: Complex searches, multi-step tasks

3. **Example Usage Patterns:**
   ```
   # Instead of searching files yourself:
   Task(description="Find auth code", prompt="Find all authentication and authorization logic", subagent_type="general-purpose")
   
   # Instead of reviewing code manually:
   Task(description="Review PR", prompt="Review changes in auth.py for security issues", subagent_type="security-auditor")
   
   # Instead of debugging yourself:
   Task(description="Debug error", prompt="Debug TypeError in user service", subagent_type="debugger")
   
   # Slash commands with Task:
   Task(description="Check file", prompt="/check-file path/to/file.py", subagent_type="general-purpose")
   ```

4. **Benefits:**
   - Saves context window space
   - Leverages specialized expertise
   - Faster execution
   - Better results
   - Allows parallel work

## ⚡ Optimal Bash Commands Reference

### CRITICAL: Always Use Modern Tools

1. **Text Search & Grep**
   ```bash
   # ❌ BAD: Traditional grep (slow)
   grep -r "TODO" .
   grep -n "function" file.py
   find . -type f -exec grep -l "pattern" {} \;
   
   # ✅ GOOD: ripgrep (10-100x faster)
   rg "TODO"
   rg -n "function" file.py
   rg -l "pattern"
   
   # ripgrep advanced features
   rg -t py "class.*User"         # Search only Python files
   rg -C 3 "error"                # Show 3 lines context
   rg --hidden "config"           # Include hidden files
   rg -g "!node_modules" "test"   # Exclude directories
   ```

2. **JSON Processing**
   ```bash
   # ❌ BAD: sed/awk/grep chains
   cat package.json | grep "\"version\"" | cut -d'"' -f4
   cat config.json | python -m json.tool
   
   # ✅ GOOD: jq (clean & powerful)
   jq -r '.version' package.json
   jq '.dependencies | keys[]' package.json
   jq -c '.scripts' package.json    # Compact output
   jq '.[] | select(.active)' users.json
   ```

3. **File Finding**
   ```bash
   # ❌ BAD: Traditional find (slow)
   find . -name "*.js"
   find . -type f -name "*test*"
   
   # ✅ GOOD: fd (simple & fast)
   fd ".js$"
   fd test
   fd -e py -e js              # Multiple extensions
   fd -H                       # Include hidden files
   ```

4. **File Viewing**
   ```bash
   # ❌ BAD: Plain cat
   cat main.py
   cat -n script.js
   
   # ✅ GOOD: bat (syntax highlighting)
   bat main.py
   bat -n script.js            # With line numbers
   bat -r 10:20 file.py        # Show lines 10-20
   ```

5. **Process & System Commands**
   ```bash
   # For counting lines/words
   rg -c "pattern"             # Count matches (faster than grep -c)
   
   # For parallel execution
   fd -e py -x pytest {}       # Run pytest on all Python files
   
   # For watching files
   fd . | entr -r npm test     # Re-run tests on file change
   ```

6. **Git Operations**
   ```bash
   # For better diffs
   git diff --color-words      # Word-level diff
   git log --oneline --graph   # Compact log view
   
   # For finding commits
   git log -S "string"         # Find commits containing string
   git grep "pattern"          # Search in git history
   ```

### Command Cheat Sheet

| Task | ❌ Don't Use | ✅ Use Instead |
|------|--------------|----------------|
| Search text | grep -r | rg |
| Find files | find | fd |
| View files | cat | bat |
| Process JSON | sed/awk | jq |
| Search code | grep | rg -t <type> |
| Count matches | grep -c | rg -c |
| List files | ls -la | eza -la or ls |
| Diff files | diff | delta or git diff |

### Remember:
- **ALWAYS check if rg is available before using grep**
- **ALWAYS use jq for JSON - never parse with regex**
- **ALWAYS prefer fd over find for file discovery**
- **Modern tools are 10-100x faster than traditional ones**