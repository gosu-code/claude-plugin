# codex-mcp

Integrates Codex CLI as a companion AI agent for Claude Code via MCP (Model Context Protocol), enabling delegation of complex workflows and MCP tool invocations.

## Overview

The codex-mcp plugin allows Claude Code to delegate tasks to another AI agent (Codex) when specialized MCP tools are needed or when complex multi-step workflows require interaction with multiple tools and commands. This enables powerful multi-agent collaboration where Claude can route specific tasks to Codex for execution.

## Features

- **MCP Tool Delegation**: Invoke MCP tools not directly available to Claude Code (e.g., context7, github, linear, jira)
- **Workflow Automation**: Execute complex multi-step workflows involving multiple MCP tools and bash commands
- **Conversation Continuity**: Continue conversations with the Codex agent using conversation IDs
- **Flexible Configuration**: Override default settings with custom config files and profiles
- **Sandbox Control**: Configure execution safety levels (read-only, workspace-write, danger-full-access)

## Installation

1. Install the plugin:
```
/plugin install codex-mcp@gosu-code
```

2. Install Codex CLI globally:
```bash
npm install -g @openai/codex
```

3. Authenticate with OpenAI:
```bash
codex login
```

4. Restart Claude Code

The plugin will automatically configure the Codex MCP server integration.

## Prerequisites

- **Node.js & npm**: Required to install Codex CLI
- **Codex CLI**: Install with `npm install -g @openai/codex`
- **OpenAI Account**: Required for Codex authentication
- **Active Internet Connection**: Required for Codex API calls

## Components

### Skills

#### codex-mcp

The primary skill that enables Claude to delegate tasks to Codex agent via MCP.

**Key Capabilities:**
- Run Codex sessions with custom prompts
- Continue conversations with follow-up prompts
- Configure sandbox mode and approval policies
- Override base instructions and model settings
- Use custom configuration profiles

## MCP Tools

### mcp__codex__codex

Runs a new Codex session with configurable parameters.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | Initial user prompt that seeds the Codex conversation |
| `approval-policy` | string | No | Approval policy: `untrusted`, `on-failure`, `on-request`, `never` |
| `base-instructions` | string | No | Override default base instructions |
| `config` | object | No | Path to custom config TOML file |
| `cwd` | string | No | Working directory for the session |
| `model` | string | No | Model override (e.g., `gpt-5`, `o4-mini`) |
| `profile` | string | No | Profile name from config.toml |
| `sandbox` | string | No | Sandbox mode: `read-only`, `workspace-write`, `danger-full-access` |

**Example Usage:**
```
Invoke context7 MCP tool to search for authentication implementations in the codebase
```

Claude will automatically:
1. Check if context7 MCP tool is available
2. If not available, delegate to Codex with appropriate prompt
3. Return the results from Codex execution

### mcp__codex__codex-reply

Continues an existing Codex session with a follow-up prompt.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | Next user prompt to continue the conversation |
| `conversationId` | string | Yes | Identifier of the conversation to continue |

**Example Usage:**

After receiving results from an initial Codex session:
```
Continue with the previous analysis and also check for error handling patterns
```

Claude will use the conversation ID from the previous response to continue the session.

## Usage Examples

### Example 1: Delegating MCP Tool Access

When you need to use an MCP tool that Claude doesn't have direct access to:

```
User: Use the context7 MCP tool to find all API endpoints in the project

Claude: [Checks available tools with ListMcpResourcesTool]
Claude: [Sees context7 is not available]
Claude: [Delegates to Codex via mcp__codex__codex with detailed prompt]
Claude: [Returns results to user]
```

### Example 2: Complex GitHub Workflow

When you need to execute a multi-step GitHub workflow:

```
User: Create GitHub project items for all open issues with label "bug"

Claude: [Identifies this requires github MCP server tools]
Claude: [Delegates to Codex with workflow instructions]
Codex: [Executes github-project-list-items and github-project-create-items]
Claude: [Reports completion status]
```

### Example 3: Filtering Large Command Output

When you need specific data from commands with large output:

```
User: Get the dependency tree but only show packages related to authentication

Claude: [Delegates to Codex with precise filtering instructions]
Codex: [Runs dependency command and filters output]
Claude: [Shows filtered results]
```

### Example 4: Conversation Continuation

When you need to follow up on a previous Codex session:

```
User: Analyze the database schema

Claude: [Delegates to Codex]
Codex: [Returns schema analysis with conversationId: "conv_123"]
Claude: [Shows results]

User: Now check for missing indexes on those tables

Claude: [Continues conversation using conversationId "conv_123"]
Codex: [Analyzes indexes in context of previous schema]
Claude: [Shows index recommendations]
```

## Operational Guidelines

### When Claude Uses Codex Delegation

Claude will automatically delegate to Codex when:

1. **MCP Tool Not Available**: User requests an MCP tool (context7, github, linear, jira) that Claude doesn't have access to
2. **Complex Workflows**: Task requires orchestrating multiple MCP tools and bash commands
3. **Large Output Filtering**: Command produces large output but only specific portions are needed
4. **Explicit Request**: User explicitly asks to use Codex or a specific MCP server

### Configuration Defaults

When delegating to Codex, Claude uses:
- **Sandbox mode**: `danger-full-access` (required for most operations)
- **Approval policy**: `never` (for automated execution)
- **Detailed prompts**: Including file references and context
- **Conversation tracking**: Maintains conversation IDs for follow-ups

### Known MCP Integrations

The plugin includes usage documentation for:
- **GitHub MCP Server**: See `mcp-github-usage.md` for GitHub tool patterns
- **Context7 MCP Server**: See `mcp-context7-usage.md` for codebase search patterns

## Configuration

### Custom Config File

Create a custom configuration TOML file to override defaults:

```toml
[profiles.custom]
model = "gpt-5"
sandbox = "workspace-write"
approval-policy = "on-failure"
base-instructions = "You are a specialized automation agent..."
```

Use with:
```
config = { path = "/path/to/custom-config.toml" }
```

### Working Directory

Specify a custom working directory for Codex sessions:

```
cwd = "/path/to/project"
```

Relative paths resolve from the server process root.

## Troubleshooting

### Codex CLI Not Found

**Problem:** Error indicating codex command not found

**Solutions:**
1. Install Codex CLI: `npm install -g @openai/codex`
2. Verify installation: `codex mcp list`
3. Check npm global bin path is in PATH
4. Restart terminal/shell after installation

### Authentication Errors

**Problem:** Codex fails with authentication errors

**Solutions:**
1. Login to OpenAI: `codex login`
2. Verify authentication status
3. Check OpenAI account has active credits/subscription
4. Try logging out and back in: `codex logout && codex login`

### MCP Server Not Connected

**Problem:** Codex MCP server shows as disconnected

**Solutions:**
1. Verify Codex CLI is installed and MCP server is available: `codex mcp list`
2. Check authentication: `codex login`
3. Restart Claude Code
4. Verify MCP server list: `claude mcp list`
5. Look for "codex: codex mcp-server - ✓ Connected"

### Delegation Failures

**Problem:** Tasks delegated to Codex fail or timeout

**Solutions:**
1. Check internet connection
2. Verify OpenAI API status
3. Review error messages for specific issues
4. Try with simpler prompt first
5. Check working directory permissions if using custom cwd

### Conversation Not Continuing

**Problem:** Follow-up prompts don't maintain context

**Solutions:**
1. Verify conversationId is being passed correctly
2. Check if original session timed out
3. Start a new session if conversation expired
4. Ensure follow-up prompt relates to original context

## Best Practices

### Crafting Delegation Prompts

When Claude delegates to Codex, it should:
1. **Be Specific**: Include all necessary context and file references
2. **State Requirements**: Clearly define expected output format
3. **Provide Constraints**: Specify any limitations or boundaries
4. **Include Context**: Reference relevant files, paths, and data

### Managing Conversations

For multi-turn interactions:
1. **Track IDs**: Save conversation IDs for follow-ups
2. **Maintain Context**: Reference previous results when continuing
3. **Stay Focused**: Keep follow-ups related to original topic
4. **Know Limits**: Start new session if context grows too large

### Sandbox Selection

Choose appropriate sandbox mode:
- **read-only**: For analysis and inspection tasks
- **workspace-write**: For tasks modifying project files
- **danger-full-access**: For tasks requiring system-level operations (used by default for delegation)

## License

Licensed under AGPL-3.0. See the LICENSE file for details.
