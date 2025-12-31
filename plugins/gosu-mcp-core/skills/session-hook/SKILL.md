---
name: session-hook
description: This skill should be used when the user asks to "create a session hook", "add a temporary hook", "create a hook for this session", "set up a hook that activates immediately", "configure a one-time hook", or mentions "session-specific hook", "per-session hook", or "temporary hook". Provides guidance for creating session-scoped hooks that activate immediately without restarting Claude Code.
---

# Session Hook

Create temporary, session-scoped hooks that activate immediately without restarting Claude Code. Session hooks enable dynamic hook configuration for the current session only, perfect for one-time workflows, debugging, or experimentation.

## Key Benefits

- **Immediate Activation**: Hooks take effect instantly, no Claude Code restart required
- **Session-Scoped**: Automatically inactive when session ends or ID changes
- **Safe Experimentation**: Test hook logic without modifying permanent configuration
- **Per-Project or Global**: Store in `./.claude/` (project) or `~/.claude/` (global)

## How Session Hooks Work

Session hooks are JSON configuration files named `hooks.{session_id}.json` stored in:

1. `./.claude/hooks.{session_id}.json` (local project, checked first)
2. `~/.claude/hooks.{session_id}.json` (user home, fallback)

The `session_hook.py` hook script (already registered in gosu-mcp-core) reads these files and executes the configured hooks for each event.

## Quick Start

### Step 1: Get Current Session ID

The session ID may be available in the Claude Code environment or current context. If you can't find it, MUST use `AskUserQuestion` tool to ask user to provide a value for the `session_id`. The value must be a valid UUID, repeat the question until user provide a valid UUID value.

### Step 2: Create Session Hook File

Create `.claude/hooks.{session_id}.json` with hook configuration:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "json",
            "json": {
              "decision": "block",
              "reason": "Please run tests before stopping"
            }
          }
        ]
      }
    ]
  }
}
```

### Step 3: Verify Hook Activation

The hook activates immediately. Trigger the event to verify it works.

## Session Hook File Format

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "optional-matcher-value",
        "hooks": [
          {
            "type": "command|json",
            ...hook-specific-fields
          }
        ]
      }
    ]
  }
}
```

### Hook Types

#### Type: `command`

Execute a shell command. The command receives the hook input via stdin.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"command"` |
| `command` | string | Yes | Shell command to execute |
| `timeout` | number | No | Timeout in seconds (default: 15, max: 60) |

```json
{
  "type": "command",
  "command": "python3 /path/to/script.py",
  "timeout": 30
}
```

#### Type: `json`

Return a fixed JSON response. Useful for blocking operations or injecting messages.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"json"` |
| `json` | object | No | JSON object to return (default: `{}`) |
| `exitcode` | number | No | Exit code to return (default: 0) |

```json
{
  "type": "json",
  "json": {"decision": "block", "reason": "Not allowed"},
  "exitcode": 0
}
```

## Supported Hook Events

| Event | When Triggered | Common Use Cases |
|-------|----------------|------------------|
| PreToolUse | Before any tool executes | Validation, blocking |
| PostToolUse | After tool completes | Logging, feedback |
| UserPromptSubmit | User submits prompt | Context injection |
| Stop | Main agent stopping | Completeness checks |
| SubagentStop | Subagent stopping | Task validation |
| SessionStart | Session begins | Context loading |
| SessionEnd | Session ends | Cleanup |
| PreCompact | Before compaction | Preserve context |
| Notification | User notified | Logging |
| PermissionRequest | Permission requested | Auto-approval/denial |

## Matcher Support

Two events support optional `matcher` field for filtering:

### SessionStart Matchers

Match against `source` field values:

| Matcher Value | When It Matches |
|---------------|-----------------|
| `startup` | New session started |
| `resume` | Resumed existing session |
| `clear` | Session cleared with /clear |
| `compact` | Session resumed after compaction |

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {"type": "json", "json": {"systemMessage": "Welcome to new session!"}}
        ]
      }
    ]
  }
}
```

### PreCompact Matchers

Match against `trigger` field values:

| Matcher Value | When It Matches |
|---------------|-----------------|
| `manual` | User manually triggered compaction |
| `auto` | Automatic context compaction |

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {"type": "json", "json": {"systemMessage": "Auto-compacting context..."}}
        ]
      }
    ]
  }
}
```

## Common Patterns

### Block Stopping Until Tests Pass

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "json",
            "json": {
              "decision": "block",
              "reason": "Run `make test` before completing the task"
            }
          }
        ]
      }
    ]
  }
}
```

### Inject Context on Session Start

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "Remember: This project uses strict TypeScript. Always add types."
            }
          }
        ]
      }
    ]
  }
}
```

### Run Custom Validation Script

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/validate_tool_use.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Log All Tool Usage

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "tee -a /tmp/claude-tool-log.json",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## Creating Session Hooks Programmatically

To create a session hook file for the current session:

```bash
# Get session ID (replace with actual session ID)
SESSION_ID="32502be3-59b3-4176-94c4-fd851d460417"

# Create .claude directory if needed
mkdir -p .claude

# Create session hook file
cat > ".claude/hooks.${SESSION_ID}.json" << 'EOF'
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "json",
            "json": {
              "decision": "block",
              "reason": "Please ensure all tests pass before stopping"
            }
          }
        ]
      }
    ]
  }
}
EOF
```

## Hook Input/Output Format

### Input (received via stdin for command hooks)

```json
{
  "session_id": "32502be3-59b3-4176-94c4-fd851d460417",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {"file_path": "/path/to/file", "content": "..."},
  "cwd": "/current/working/dir",
  "transcript_path": "/path/to/transcript.txt"
}
```

### Output (for decision hooks like Stop)

```json
{
  "decision": "approve|block",
  "reason": "Explanation for the decision",
  "systemMessage": "Additional context for Claude"
}
```

### Output (for PreToolUse permission hooks)

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow|deny|ask"
  },
  "systemMessage": "Explanation"
}
```

## Cleanup

Session hook files remain until manually deleted. To clean up:

```bash
# Remove specific session hook
rm .claude/hooks.{session_id}.json

# Remove all session hooks in project
rm .claude/hooks.*.json

# Remove all session hooks in home directory
rm ~/.claude/hooks.*.json
```

## Security Considerations

- Session IDs must be valid UUID format (prevents path traversal)
- Commands execute with user permissions
- Timeout enforced (max 60 seconds) to prevent hanging
- File size limited to 1MB to prevent memory exhaustion

## Troubleshooting

### Hook Not Activating

1. Verify session ID matches current session (use `/id` command)
2. Check file path: `.claude/hooks.{session_id}.json`
3. Validate JSON syntax: `jq . .claude/hooks.*.json`
4. Ensure hook event name is correct (case-sensitive)

### Command Hook Failing

1. Test command manually with sample input
2. Check command timeout (default 15s, max 60s)
3. Verify command has execute permissions
4. Check stderr output for error messages

### JSON Validation

```bash
# Validate session hook file
cat .claude/hooks.{session_id}.json | jq .
```

## Additional Resources

### Utility Scripts

Available in `scripts/`:

- **`create_session_hook.py`** - Create session hooks programmatically

```bash
# Block stopping with a message
python3 scripts/create_session_hook.py SESSION_ID Stop json --decision block --reason "Run tests first"

# Inject context on session start
python3 scripts/create_session_hook.py SESSION_ID SessionStart json --matcher startup --message "Welcome!"

# Add command hook for logging
python3 scripts/create_session_hook.py SESSION_ID PostToolUse command --command "tee -a /tmp/log.json"

# Dry run to preview
python3 scripts/create_session_hook.py SESSION_ID Stop json --decision block --reason "Test" --dry-run
```

### Examples

Working examples in `examples/`:

- **`block-stop-until-tests.json`** - Block stopping until tests pass
- **`inject-context-startup.json`** - Inject context on session start
- **`log-tool-usage.json`** - Log all tool usage to file
- **`precompact-reminder.json`** - Add reminder before context compaction

### References

For advanced patterns, see:

- **`references/advanced-patterns.md`** - Complex hook configurations
- **`references/hook-output-formats.md`** - Complete output format reference
