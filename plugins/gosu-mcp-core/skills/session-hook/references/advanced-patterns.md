# Advanced Session Hook Patterns

This reference documents advanced patterns and configurations for session hooks.

## Multi-Event Hooks

Configure multiple events in a single session hook file:

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
              "systemMessage": "Welcome! Remember to follow project guidelines."
            }
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "json",
            "json": {
              "decision": "block",
              "reason": "Please run tests before completing"
            }
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "Preserving important context before compaction..."
            }
          }
        ]
      }
    ]
  }
}
```

## Conditional Hooks with Matchers

### SessionStart with Different Sources

Handle different session start scenarios:

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
              "systemMessage": "New session started. Loading project context..."
            }
          }
        ]
      },
      {
        "matcher": "resume",
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "Session resumed. Picking up where we left off."
            }
          }
        ]
      },
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "Session resumed after compaction. Key context may be summarized."
            }
          }
        ]
      }
    ]
  }
}
```

### PreCompact Manual vs Auto

Different handling for manual and automatic compaction:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "manual",
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "Manual compaction triggered. User intentionally compacting context."
            }
          }
        ]
      },
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "Auto-compacting due to context limits. Critical info:\n- Current task status\n- Key decisions made\n- Pending work items"
            }
          }
        ]
      }
    ]
  }
}
```

## Command Hook Patterns

### Validation Script

Create a validation script that processes hook input:

**Python validation script (`validate.py`):**
```python
#!/usr/bin/env python3
import json
import sys

input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

# Example: Block writes to sensitive files
if tool_name == "Write":
    file_path = tool_input.get("file_path", "")
    sensitive_patterns = [".env", "credentials", "secrets", "password"]

    for pattern in sensitive_patterns:
        if pattern in file_path.lower():
            result = {
                "hookSpecificOutput": {
                    "permissionDecision": "deny"
                },
                "systemMessage": f"Blocked: Cannot write to sensitive file matching '{pattern}'"
            }
            print(json.dumps(result))
            sys.exit(0)

# Allow by default
print("{}")
```

**Session hook configuration:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/validate.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Logging with Context

Log tool usage with additional context:

**Bash logging script (`log-tool.sh`):**
```bash
#!/bin/bash
# Read input and add timestamp
INPUT=$(cat)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create log entry with timestamp
echo "{\"timestamp\": \"$TIMESTAMP\", \"data\": $INPUT}" >> /tmp/claude-tool-log.jsonl

# Output empty JSON to not affect tool execution
echo "{}"
```

**Session hook configuration:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ./scripts/log-tool.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## Dynamic Message Injection

### Time-Based Reminders

Inject different messages based on time of day:

**Python time-based hook (`time-reminder.py`):**
```python
#!/usr/bin/env python3
import json
import datetime

hour = datetime.datetime.now().hour

if hour < 12:
    message = "Good morning! Let's start fresh."
elif hour < 17:
    message = "Afternoon session. Stay focused!"
else:
    message = "Evening work. Remember to take breaks."

result = {"systemMessage": message}
print(json.dumps(result))
```

**Session hook configuration:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/time-reminder.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### Git Branch Context

Inject context based on current git branch:

**Bash branch hook (`branch-context.sh`):**
```bash
#!/bin/bash
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
    MSG="WARNING: Working on main branch. Be extra careful with changes."
elif [[ "$BRANCH" == feature/* ]]; then
    MSG="Feature branch: ${BRANCH}. Focus on the feature scope."
elif [[ "$BRANCH" == fix/* || "$BRANCH" == bugfix/* ]]; then
    MSG="Bug fix branch: ${BRANCH}. Keep changes minimal and focused."
else
    MSG="Branch: ${BRANCH}"
fi

echo "{\"systemMessage\": \"$MSG\"}"
```

## Workflow Enforcement

### Require Code Review Before Stop

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
              "reason": "Before completing, please:\n1. Review changes with `git diff`\n2. Run tests with `make test`\n3. Run linter with `make lint`\n\nConfirm all checks pass before stopping."
            }
          }
        ]
      }
    ]
  }
}
```

### Staged Workflow

Block stopping with specific workflow stages:

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
              "reason": "Workflow checklist:\n[ ] Implementation complete\n[ ] Tests written and passing\n[ ] Documentation updated\n[ ] Code reviewed\n\nPlease confirm each step is complete."
            }
          }
        ]
      }
    ]
  }
}
```

## Chaining Hooks

Session hooks support multiple hooks per event. They execute in order:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "json",
            "json": {
              "systemMessage": "First message: Loading context..."
            }
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/load-additional-context.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Note: Only the first matching hook entry (with matcher) is executed per event.

## Error Handling in Command Hooks

### Graceful Degradation

Design command hooks to fail gracefully:

```python
#!/usr/bin/env python3
import json
import sys

try:
    input_data = json.load(sys.stdin)
    # ... processing logic ...
    result = {"systemMessage": "Processed successfully"}
    print(json.dumps(result))
except Exception as e:
    # On error, output empty JSON to not block operations
    print("{}")
    # Optionally log error to stderr
    print(f"Hook error: {e}", file=sys.stderr)
```

### Timeout Considerations

- Default timeout: 15 seconds
- Maximum timeout: 60 seconds
- Design hooks to complete quickly
- Use async patterns for slow operations
- Consider caching for expensive computations

## Debugging Session Hooks

### Enable Verbose Logging

Add logging to command hooks:

```bash
#!/bin/bash
set -x  # Enable debug output to stderr

INPUT=$(cat)
echo "DEBUG: Received input: $INPUT" >&2

# ... hook logic ...

echo "{}"
```

### Test Hook Independently

Test command hooks without Claude Code:

```bash
# Create test input
echo '{"session_id":"test","hook_event_name":"Stop"}' | python3 ./scripts/my-hook.py

# Check exit code
echo "Exit code: $?"
```

### Validate JSON Output

Ensure hooks output valid JSON:

```bash
echo '{"test":"input"}' | python3 ./scripts/my-hook.py | jq .
```

## Security Best Practices

### Input Validation

Always validate input in command hooks:

```python
#!/usr/bin/env python3
import json
import sys
import re

# Read and parse input
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    print("{}")
    sys.exit(0)

# Validate expected fields exist
if not isinstance(input_data, dict):
    print("{}")
    sys.exit(0)

# Validate session_id format (UUID)
session_id = input_data.get("session_id", "")
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)
if not UUID_PATTERN.match(session_id):
    print("{}")
    sys.exit(0)

# ... safe to proceed with validated input ...
```

### Avoid Shell Injection

When constructing shell commands from input, use proper escaping:

```python
import shlex
import subprocess

# UNSAFE - never do this
# subprocess.run(f"echo {user_input}", shell=True)

# SAFE - use argument list
subprocess.run(["echo", user_input])

# SAFE - use shlex.quote for shell commands
safe_input = shlex.quote(user_input)
subprocess.run(f"echo {safe_input}", shell=True)
```

### File Path Validation

Validate file paths to prevent traversal:

```python
import os

def is_safe_path(base_dir, path):
    """Check if path is within base_dir (prevent traversal)."""
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(os.path.join(base_dir, path))
    return abs_path.startswith(abs_base)

# Usage
if not is_safe_path("./allowed", file_path):
    print(json.dumps({"error": "Invalid path"}))
    sys.exit(1)
```
