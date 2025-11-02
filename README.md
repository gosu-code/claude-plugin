# gosu-claude

Gosu Claude Code Plugins & Marketplace - A collection of plugins that extend Claude Code with specialized agents, skills, commands, and hooks for enhanced coding workflows.

## Features Overview

- **Specialized AI Agents**: Code reviewers, spec reviewers, test runners, and brainstorming agents
- **Task Management**: Advanced markdown-based task tracking with hierarchical structure and progress monitoring
- **GitHub PR Utilities**: Automated PR review comment management and bot feedback processing
- **Git Worktree Management**: Streamlined worktree creation and configuration for isolated development
- **Voice Coding**: Enhanced voice input processing for natural coding sessions
- **MCP Integration**: Direct integration with Model Context Protocol servers including Codex CLI

## Quick Start

### 1. Add the Gosu Marketplace

Run this slash command in Claude Code to add the `gosu-code` marketplace:

```
/plugin marketplace add gosu-code/claude-plugin
```

### 2. Install Plugins

Install the `gosu-mcp-core` plugin:

```
/plugin install gosu-mcp-core@gosu-code
```

Optional plugins:

```
/plugin install codex-mcp@gosu-code
/plugin install voice-coding@gosu-code
```

### 3. Configure MCP Server (gosu-mcp-core only)

After installing `gosu-mcp-core`, restart Claude Code, then run:

```
/gosu-mcp-core:install-gosu-model-context-protocol
```

**Prerequisites for MCP server installation:**
- Docker installed and running
- GitHub CLI (`gh`) installed and authenticated (`gh auth login`)

## Plugins

### gosu-mcp-core

Core plugin providing essential development workflow tools and integrations with the Gosu MCP server.

**Components:**
- 6 Specialized Agents (code review, spec review, spec verification, test running, brainstorming, dynamic)
- 3 Skills (task-list-md, github-pr-utils, git-worktree)
- 1 Command (MCP server installation)
- 1 Hook (dangerous tool usage blocker)

[View detailed documentation →](plugins/gosu-mcp-core/README.md)

### codex-mcp

Integrates Codex CLI as a companion AI agent via MCP, enabling delegation of complex workflows and MCP tool invocations.

**Components:**
- 1 Skill (codex-mcp for agent delegation)
- MCP server configuration for Codex integration

**Prerequisites:**
- `codex` CLI installed (`npm install -g @openai/codex`)
- OpenAI account authentication (`codex login`)

[View detailed documentation →](plugins/codex-mcp/README.md)

### voice-coding

Enhances voice coding sessions with intelligent prompt processing for natural speech-to-code workflows.

**Components:**
- 1 Hook (voice input prompt enhancer)

[View detailed documentation →](plugins/voice-coding/README.md)

## Usage Examples

### Using Task List Management
**Use script as CLI manual tool**
You can use the `task_list_md.py` script manually to manage tasks in markdown files by create a symbolic link to the script as follows:
```bash
sudo ln -s ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py /usr/local/bin/task_list_md.py
```
Now you can invoke the script from anywhere with `task_list_md.py` command. For example, To track your development tasks with hierarchical markdown checklists:

```bash
# List all tasks
task_list_md.py list-tasks tasks.md

# Add a new task
task_list_md.py add-task tasks.md 1.1 "Implement user authentication"

# Update task status
task_list_md.py set-status tasks.md 1.1 in-progress

# Get next actionable task
task_list_md.py get-next-task tasks.md
```
**Use skill within Claude Code**
You can also use the `task-list-md` skill within Claude Code to manage your tasks directly from the chat interface.For example:

```
Use skill to:
- add a new task "Implement user authentication" in tasks.md which depends on task 1.1
- add a new subtask "Design login page" under task 3 in tasks.md
- list all tasks in tasks.md
```

### Running Code Reviews

Ask Claude Code to review your code and the gosu-code-reviewer agent will automatically analyze it:

```
Review my TypeScript service class in src/services/user.service.ts for best practices
```

### Managing GitHub PR Comments

Ask Claude Code to Fetch and analyse bot-generated review comments using the `github-pr-utils` skill:

```
Use skill to fetch and analyze GitHub PR #42 comments for bot-generated feedback.
Then for each comment that you disagree with, reply with a polite explanation and resolve the comment.
```

### Creating Git Worktrees

Ask Claude Code to quickly create an isolated worktree environment for a new feature branch:

```
Use skill to create git worktree for branch feature/new-api and open it in a new Code editor window
```

## Troubleshooting

### Plugin Marketplace Not Found

If the marketplace add command fails:
1. Verify you're using a compatible version of Claude Code
2. Check your internet connection
3. Try again after a few minutes

### MCP Server Installation Fails

Common issues and solutions:

**"Not logged in to GitHub"**
- Run `gh auth login` to authenticate with GitHub CLI
- Verify authentication with `gh auth status`

**Docker connection errors**
- Ensure Docker is installed and running
- Test Docker: `docker run hello-world`
- Check Docker daemon status

**Permission errors**
- Verify your GitHub token has necessary scopes
- Ensure you have write access to repositories you're working with

### Agent Not Responding

If specialized agents don't activate:
1. Restart Claude Code after plugin installation
2. Verify the MCP server is connected: `claude mcp list`
3. Check for "gosu: ... - ✓ Connected" status

### Task List CLI Issues

**Script not found or not able to run**
- Find the script `task_list_md.py` under `~/.claude/plugins/` directory (the plugin may be installed under a different path/name based on your setup)
- Ensure the script has execute permissions: `chmod +x path/to/task_list_md.py`
- Create a symbolic link to the script in a directory included in your system PATH
- Ensure Python 3.x is installed

**Task file not found errors**
- Verify the markdown file path exists
- Check `.tasks.local.json` is writable

## License

All plugins are licensed under AGPL-3.0. See the LICENSE file in each plugin directory for details.