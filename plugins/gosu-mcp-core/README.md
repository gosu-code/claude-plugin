# gosu-mcp-core

Core plugin providing essential development workflow tools and integrations with the Gosu MCP server for Claude Code.

## Overview

The gosu-mcp-core plugin extends Claude Code with specialized AI agents, powerful task management tools, GitHub PR utilities, and git worktree management capabilities. It provides a comprehensive set of development workflow automation tools designed to enhance productivity and code quality.

## Features

- **6 Specialized AI Agents** for code review, specification management, testing, and problem-solving
- **Task List Management** with hierarchical markdown checklists and progress tracking
- **GitHub PR Utilities** for automated review comment handling
- **Git Worktree Tools** for isolated development environments
- **Safety Hooks** to prevent dangerous operations
- **MCP Server Integration** providing GitHub API access and embedded workflows

## Installation

1. Add the Gosu marketplace to Claude Code:
```
/plugin marketplace add gosu-code/claude-plugin
```

2. Install the gosu-mcp-core plugin:
```
/plugin install gosu-mcp-core@gosu-code
```

3. Restart Claude Code

4. Install and configure the Gosu MCP server:
```
/gosu-mcp-core:install-gosu-model-context-protocol
```

## Prerequisites

- **Docker**: Required for running the MCP server container
- **GitHub CLI (`gh`)**: Required for GitHub authentication (`gh auth login`)
- **Python 3.x**: Required for skill scripts
- **Bash**: Required for shell scripts

## Components

### Agents

Specialized AI sub-agents that handle specific development tasks:

#### gosu-code-reviewer

Reviews Python, Go, and TypeScript source code for best practices, code quality, and completeness.

**Usage:**
```
Review my TypeScript service class in src/services/user.service.ts for best practices
```

**When to use:**
- After implementing new functionality
- When reviewing test files
- To ensure code follows best practices and idioms

#### gosu-spec-reviewer

Reviews Markdown specification files (*.spec.md) for completeness, accuracy, and alignment with project requirements.

**Usage:**
```
Review the user-authentication.spec.md file for completeness
```

**When to use:**
- After creating or updating specification documents
- To validate spec structure and quality
- Before starting implementation

#### gosu-spec-verifier

Verifies that source code implementations match their corresponding specification files and cleans up fully implemented spec details.

**Usage:**
```
Verify that auth.go matches the auth.spec.md specification
```

**When to use:**
- After completing feature implementation
- To clean up spec files by removing implemented details
- To verify implementation compliance with specifications

#### gosu-test-runner

Executes test scripts, test suites, integration tests, and e2e tests, then analyzes failed test cases.

**Usage:**
```
Run the tests in test/integration and check if anything broke
```

**When to use:**
- After code changes to verify functionality
- When debugging failing tests
- To get comprehensive test execution reports

#### dual-persona-brainstormer

Provides comprehensive problem-solving combining analytical rigor with creative innovation for strategic planning, product development, and complex challenges.

**Usage:**
```
Help me brainstorm solutions for the scalability challenges in our backend
```

**When to use:**
- Strategic planning and architecture decisions
- Complex problem-solving requiring multiple perspectives
- Product development and feature design

#### dynamic

A flexible agent that adapts to various tasks based on user instructions and can use different system prompts dynamically.

**Usage:**
```
Use dynamic subagent with prompt ID "code-reviewer" to review the pkg/otel module
```

**When to use:**
- When explicitly instructed by the user
- For specialized tasks with specific prompt requirements

### Skills

Reusable capabilities that extend Claude Code's functionality:

#### task-list-md

Parse and manage hierarchical task lists in markdown files with progress tracking and metadata support.

**Features:**
- Hierarchical task structure with dot notation (1, 1.1, 1.2.1)
- Five status types: pending, in-progress, done, review, deferred
- Dependencies and requirements tracking
- Progress statistics and history
- Task filtering and search
- JSON export capabilities

**Common Commands:**
```bash
# List all tasks
python3 scripts/task_list_md.py list-tasks tasks.md

# Add a new task
python3 scripts/task_list_md.py add-task tasks.md 1.1 "Implement feature" \
  --dependencies 1 --requirements "API design complete"

# Update task status
python3 scripts/task_list_md.py set-status tasks.md 1.1 in-progress

# Get next actionable task
python3 scripts/task_list_md.py get-next-task tasks.md

# Check dependencies
python3 scripts/task_list_md.py check-dependencies tasks.md

# Show progress
python3 scripts/task_list_md.py show-progress tasks.md

# Filter tasks
python3 scripts/task_list_md.py filter-tasks tasks.md --status pending

# Search tasks
python3 scripts/task_list_md.py search-tasks tasks.md authentication

# List ready tasks
python3 scripts/task_list_md.py ready-tasks tasks.md

# Export to JSON
python3 scripts/task_list_md.py export tasks.md --output tasks.json
```

#### github-pr-utils

Utility scripts for GitHub pull request review comment management, specifically for handling bot-generated review feedback.

**Features:**
- Fetch bot-authored review comments
- Reply to review threads programmatically
- Resolve conversations automatically
- Filter by resolution and outdated status
- Include diff context for comments

**Requirements:**
- `gh` CLI version 2.60+
- `jq` CLI version 1.6+
- GitHub CLI authentication

**Common Commands:**
```bash
# Fetch all bot comments
scripts/get_pr_bot_review_comments.sh owner repo 123

# Fetch unresolved comments
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  owner repo 123

# Fetch comments with specific users
scripts/get_pr_bot_review_comments.sh \
  --include-github-user dependabot,renovate \
  owner repo 123

# Reply to a comment
scripts/reply-pr-review-comments-thread.sh \
  --body "Fixed in latest commit" \
  owner repo 2451122234

# Reply and resolve thread
scripts/reply-pr-review-comments-thread.sh \
  --body "Done!" \
  --thread-id PRRT_kwDODds1es5e2SRi \
  --resolve-thread \
  owner repo 2451122234
```

#### git-worktree

Utility tool to create new git worktrees with proper setup for development environments, including file synchronization and ownership management.

**Features:**
- Create new worktrees with auto-generated or custom branch names
- Copy gitignored files (node_modules, .env, .venv, vendor)
- Symlink local settings
- Copy staged, modified, or untracked files
- Change worktree ownership for agent workflows
- Environment verification checks

**Requirements:**
- Python 3.x
- `git` CLI
- sudo/root access (if using --agent-user)

**Common Commands:**
```bash
# Create worktree from task prompt
python3 scripts/create_git_worktree.py feature add user auth \
  --copy-untracked

# Create with explicit branch
python3 scripts/create_git_worktree.py \
  --branch feat/fix-bug \
  --copy-modified

# Create for agent workflow
python3 scripts/create_git_worktree.py "apply fixes" \
  --agent-user vscode \
  --plan-file plan.md

# Use existing worktree directory
python3 scripts/create_git_worktree.py "implement feature" \
  --worktree /path/to/worktree
```

### Commands

#### install-gosu-model-context-protocol

Installs and configures the Gosu MCP server using GitHub CLI authentication and Docker.

**Usage:**
```
/gosu-mcp-core:install-gosu-model-context-protocol
```

**Process:**
1. Verifies GitHub CLI authentication status
2. Installs MCP server via Docker
3. Configures Claude Code integration
4. Verifies successful connection

**Requirements:**
- Docker installed and running
- GitHub CLI authenticated (`gh auth login`)
- Active internet connection

### Hooks

#### block_dangerous_tool_usages

A safety hook that runs before Read, Edit, MultiEdit, Write, and Bash tool executions to prevent dangerous operations.

**Triggered by:** PreToolUse event
**Purpose:** Protect against accidental file operations or command executions that could cause data loss or security issues

#### task-list-md progress checker

Validates task progress conditions when Claude Code stops, ensuring completion targets are met.

**Triggered by:** Stop event
**Purpose:** Track and enforce task completion goals set via `track-progress` commands

## Usage Examples

### Example 1: Complete Code Review Workflow

```
1. "Implement the UserService class in src/services/user.service.py"
   [Claude implements the code]

2. "Now review the implementation for best practices"
   [gosu-code-reviewer agent automatically activates and reviews]

3. [Apply suggested improvements]

4. "Run the tests to verify everything works"
   [gosu-test-runner agent executes tests and reports results]
```

### Example 2: Spec-Driven Development

```
1. "Create a specification for the authentication module"
   [Claude creates auth.spec.md]

2. "Review the spec for completeness"
   [gosu-spec-reviewer agent reviews the specification]

3. [Implement the authentication module based on spec]

4. "Verify that auth.go matches auth.spec.md"
   [gosu-spec-verifier agent checks implementation compliance]
```

### Example 3: Task-Based Project Management

```bash
# Set up project tasks
python3 scripts/task_list_md.py add-task project.md 1 "Setup authentication"
python3 scripts/task_list_md.py add-task project.md 1.1 "Design auth flow"
python3 scripts/task_list_md.py add-task project.md 1.2 "Implement JWT tokens" \
  --dependencies 1.1

# Start working
python3 scripts/task_list_md.py get-next-task project.md
python3 scripts/task_list_md.py set-status project.md 1.1 in-progress

# Track progress
python3 scripts/task_list_md.py show-progress project.md

# Set completion goals
python3 scripts/task_list_md.py track-progress add project.md 1 1.1 1.2 \
  --valid-for 2h --complete-more 3
```

### Example 4: GitHub PR Review Automation

```bash
# Get all unresolved bot feedback
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  --exclude-outdated \
  gosu-code gosu-mcp-server 123 > bot_comments.json

# Process each comment
cat bot_comments.json | jq -r '.[].comment.databaseId' | while read id; do
  scripts/reply-pr-review-comments-thread.sh \
    --body "Addressed in commit abc123" \
    gosu-code gosu-mcp-server "$id"
done
```

### Example 5: Isolated Feature Development

```bash
# Create isolated environment for new feature
python3 scripts/create_git_worktree.py feature add payment integration \
  --copy-untracked \
  --plan-file payment-plan.md

# Verify worktree setup
cd ../worktree-agent-no1
git status
go mod verify  # for Go projects
npm list       # for Node.js projects
```

## Troubleshooting

### MCP Server Connection Issues

**Problem:** MCP server not connecting after installation

**Solutions:**
1. Verify Docker is running: `docker ps`
2. Check GitHub authentication: `gh auth status`
3. Verify MCP server status: `claude mcp list`
4. Restart Claude Code
5. Try manual Docker run: `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token) 0xgosu/gosu-mcp-server`

### Agent Not Activating

**Problem:** Specialized agents don't respond to requests

**Solutions:**
1. Ensure MCP server is connected (see above)
2. Restart Claude Code after plugin installation
3. Try explicit agent invocation in your request
4. Check if your request matches the agent's use cases

### Script Permission Errors

**Problem:** Python or bash scripts fail with permission denied

**Solutions:**
1. Make scripts executable: `chmod +x scripts/*.py scripts/*.sh`
2. Use explicit Python interpreter: `python3 scripts/task_list_md.py`
3. Check file ownership and permissions

### Task List File Issues

**Problem:** Task list operations fail or produce errors

**Solutions:**
1. Verify markdown file exists and is readable
2. Check `.tasks.local.json` permissions (should be writable)
3. Validate task ID format (use dot notation: 1, 1.1, 1.2.1)
4. Ensure dependencies reference existing task IDs

### GitHub PR Utils Authentication

**Problem:** PR utils scripts fail with authentication errors

**Solutions:**
1. Login to GitHub CLI: `gh auth login`
2. Verify authentication: `gh auth status`
3. Check token scopes include repo access
4. Ensure you have write access to the repository

### Git Worktree Creation Failures

**Problem:** Worktree creation fails or produces errors

**Solutions:**
1. Verify you're in a git repository
2. Check target directory doesn't already exist
3. Ensure branch name is valid (no special characters)
4. Try without `--agent-user` flag first
5. Don't attempt more than 3 times - ask user for manual creation

## License

Licensed under AGPL-3.0. See the LICENSE file for details.
