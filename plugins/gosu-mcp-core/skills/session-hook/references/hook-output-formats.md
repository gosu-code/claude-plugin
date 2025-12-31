# Hook Output Formats Reference

This reference documents the complete output formats for each hook event type.

## General Output Structure

All hooks can return a general structure:

```json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "Message shown to Claude"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `continue` | boolean | `true` | If false, halt processing |
| `suppressOutput` | boolean | `false` | Hide output from transcript |
| `systemMessage` | string | - | Message shown to Claude in context |

## Event-Specific Output Formats

### Stop / SubagentStop

Control whether Claude can stop:

```json
{
  "decision": "approve|block",
  "reason": "Explanation for the decision",
  "systemMessage": "Additional context for Claude"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision` | string | Yes | `"approve"` to allow stop, `"block"` to continue |
| `reason` | string | No | Explanation shown to Claude |
| `systemMessage` | string | No | Additional context |

**Example - Block stop:**
```json
{
  "decision": "block",
  "reason": "Tests have not been run yet. Please run `make test` first."
}
```

**Example - Approve stop:**
```json
{
  "decision": "approve",
  "reason": "All checks passed."
}
```

### PreToolUse

Control tool execution permission:

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow|deny|ask",
    "updatedInput": {}
  },
  "systemMessage": "Explanation"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hookSpecificOutput.permissionDecision` | string | `"allow"` to proceed, `"deny"` to block, `"ask"` for user confirmation |
| `hookSpecificOutput.updatedInput` | object | Modified tool input (optional) |
| `systemMessage` | string | Explanation shown to Claude |

**Example - Deny tool use:**
```json
{
  "hookSpecificOutput": {
    "permissionDecision": "deny"
  },
  "systemMessage": "Cannot write to .env files for security reasons"
}
```

**Example - Allow with modified input:**
```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow",
    "updatedInput": {
      "file_path": "/safe/path/file.txt",
      "content": "sanitized content"
    }
  }
}
```

**Example - Require user confirmation:**
```json
{
  "hookSpecificOutput": {
    "permissionDecision": "ask"
  },
  "systemMessage": "This operation modifies a critical file. User confirmation required."
}
```

### PostToolUse

React to tool execution results:

```json
{
  "systemMessage": "Feedback based on tool result",
  "suppressOutput": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `systemMessage` | string | Feedback or analysis of tool result |
| `suppressOutput` | boolean | Hide this output from transcript |

**Example - Provide feedback:**
```json
{
  "systemMessage": "File written successfully. Remember to add tests for new code."
}
```

### UserPromptSubmit

React to user prompts:

```json
{
  "hookSpecificOutput": {
    "updatedPrompt": "Modified user prompt"
  },
  "systemMessage": "Context to add"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hookSpecificOutput.updatedPrompt` | string | Modified prompt (optional) |
| `systemMessage` | string | Additional context |

**Example - Add context:**
```json
{
  "systemMessage": "Note: This project uses TypeScript strict mode. Ensure all types are properly defined."
}
```

### SessionStart

Add context when session starts:

```json
{
  "systemMessage": "Welcome message or project context"
}
```

**Example:**
```json
{
  "systemMessage": "Session started. Project: gosu-mcp-server\nBranch: main\nLast activity: Implementing session hooks"
}
```

### SessionEnd

Perform cleanup or logging:

```json
{
  "systemMessage": "Cleanup message"
}
```

### PreCompact

Add information before context compaction:

```json
{
  "systemMessage": "Important context to preserve"
}
```

**Example:**
```json
{
  "systemMessage": "Pre-compaction context:\n- Current task: Implementing session hooks\n- Progress: 80% complete\n- Next step: Write tests"
}
```

### PermissionRequest

Handle permission requests:

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow|deny|ask"
  },
  "systemMessage": "Explanation"
}
```

### Notification

React to notifications:

```json
{
  "systemMessage": "Response to notification"
}
```

## Exit Code Behavior

Hook exit codes affect behavior:

| Exit Code | Behavior |
|-----------|----------|
| 0 | Success - stdout shown in transcript |
| 2 | Blocking error - stderr fed back to Claude |
| Other | Non-blocking error - logged but continues |

## JSON Type Hook Output

For `"type": "json"` hooks, the entire `"json"` object is returned as output:

```json
{
  "type": "json",
  "json": {
    "decision": "block",
    "reason": "Custom reason"
  },
  "exitcode": 0
}
```

The `json` object is returned directly as hook output.

## Command Type Hook Output

For `"type": "command"` hooks:
- stdout is parsed as JSON and returned as hook output
- stderr is logged but not returned
- Exit code determines behavior

**Command script example:**
```python
#!/usr/bin/env python3
import json

result = {
    "decision": "block",
    "reason": "Tests required"
}
print(json.dumps(result))
```

## Empty Output

Return empty JSON `{}` to indicate no action:
- Hook executes but doesn't affect behavior
- Useful for logging-only hooks
- Default when no output needed

```json
{}
```

## Output Size Limits

- Maximum output: 100KB
- Output exceeding limit may be truncated
- For large outputs, write to file instead

## Common Patterns

### Blocking Stop

```json
{
  "type": "json",
  "json": {
    "decision": "block",
    "reason": "Complete the checklist before stopping"
  }
}
```

### Context Injection

```json
{
  "type": "json",
  "json": {
    "systemMessage": "Remember: Follow coding standards"
  }
}
```

### Tool Permission Control

```json
{
  "type": "json",
  "json": {
    "hookSpecificOutput": {
      "permissionDecision": "deny"
    },
    "systemMessage": "This operation is not allowed"
  }
}
```

### Silent Logging (No Output)

```json
{
  "type": "command",
  "command": "tee -a /tmp/log.json > /dev/null && echo '{}'"
}
```

The command logs to file and outputs empty JSON.
