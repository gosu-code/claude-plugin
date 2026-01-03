#!/usr/bin/env python3
# ------------------- LICENSE -------------------
# Copyright (C) 2025 gosu-code 0xgosu@gmail.com

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Source: http://opensource.org/licenses/AGPL-3.0
# ------------------- LICENSE -------------------
"""
Claude Code Hook: Session-based Temporary Hooks

This hook script enables per-session temporary hooks for Claude Code by reading
session-specific hook configurations from JSON files.

How It Works:
-------------
1. Reads JSON input from stdin containing session_id and hook_event_name
2. Looks for session-specific hooks at:
   - ./.claude/hooks/hooks.{session_id}.json (local project, checked first)
   - ~/.claude/hooks/hooks.{session_id}.json (user home, fallback)
3. If no session file exists, outputs {} and exits 0
4. Parses the hooks config and finds the first "command" type hook for the event
5. Executes the command with timeout (60s default or hook's specified timeout)
6. Passes stdout and exit code back to Claude Code

Input Format (from stdin):
--------------------------
{
  "session_id": "32502be3-59b3-4176-94c4-fd851d460417",
  "hook_event_name": "SessionStart",
  "source": "startup",
  ...
}

Session Hooks File Format (./.claude/hooks/hooks.{session_id}.json):
--------------------------------------------------------------------
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo hello",
            "timeout": 30
          }
        ]
      }
    ]
  }
}

Supported Hook Types:
---------------------
1. "command" - Execute a shell command
   - "command": Shell command to execute (required)
   - "timeout": Execution timeout in seconds (optional, default 15s)

2. "json" - Return a fixed JSON response
   - "json": JSON object to return (optional, default {})
   - "exitcode": Exit code to return (optional, default 0)

Supported Hook Event Types:
---------------------------
- PreToolUse, PostToolUse, PermissionRequest, Notification
- UserPromptSubmit, Stop, SubagentStop, PreCompact
- SessionStart, SessionEnd

Matcher Support:
----------------
Some events support optional "matcher" field to filter hooks:

1. PreCompact - matches against "trigger" field:
   - "manual": User manually triggered compaction
   - "auto": Automatic context compaction

2. SessionStart - matches against "source" field:
   - "startup": New session started
   - "resume": Resumed existing session
   - "clear": Session cleared with /clear
   - "compact": Session resumed after compaction

Example with matcher:
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{"type": "json", "json": {"msg": "welcome"}}]
      }
    ]
  }
}

Output Behavior:
----------------
- No session file found: Output {} and exit 0
- No hook for event: Output {} and exit 0
- Command succeeds: Output command's stdout and exit with command's exit code
- Command fails: Write error to stderr and exit with command's exit code
- Command timeout: Write timeout error to stderr and exit 1

Security:
---------
- Session ID must be a valid UUID format (prevents path traversal)
- Timeout is enforced to prevent hanging
- Commands come from trusted session-specific JSON files

Exit Codes:
-----------
- 0: Success (no session hook, or command executed successfully)
- 1: Timeout or other error
- >1: Command's exit code propagated
"""

import json
import os
import re
import subprocess
import sys
from typing import Dict, Optional, Tuple

# UUID regex pattern for session_id validation
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

# Default timeout for hook command execution (seconds)
DEFAULT_TIMEOUT = 15

# Maximum allowed timeout (1 minute) to prevent resource exhaustion
MAX_TIMEOUT = 60

# Maximum session hooks file size (1MB) to prevent memory exhaustion
MAX_FILE_SIZE = 1024 * 1024


def validate_session_id(session_id: str) -> bool:
    """
    Validate that session_id is a valid UUID format.

    This prevents path traversal attacks by ensuring the session_id
    only contains hexadecimal characters and hyphens in UUID format.

    Args:
        session_id: The session ID to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    if not session_id or not isinstance(session_id, str):
        return False
    return bool(UUID_PATTERN.match(session_id))


def find_session_hooks_file(session_id: str) -> Optional[str]:
    """
    Find the session-specific hooks file.

    Searches in order:
    1. ./.claude/hooks/hooks.{session_id}.json (local project)
    2. ~/.claude/hooks/hooks.{session_id}.json (user home)

    Args:
        session_id: The validated session ID

    Returns:
        Path to the hooks file if found, None otherwise
    """
    filename = f"hooks.{session_id}.json"

    # Check local project directory first
    local_path = os.path.join(".claude", "hooks", filename)
    if os.path.isfile(local_path):
        return local_path

    # Check user home directory
    home_path = os.path.join(os.path.expanduser("~"), ".claude", "hooks", filename)
    if os.path.isfile(home_path):
        return home_path

    return None


def load_hooks_config(file_path: str) -> Dict:
    """
    Load and parse the hooks configuration from a JSON file.

    Args:
        file_path: Path to the session hooks JSON file

    Returns:
        Parsed hooks configuration dict

    Raises:
        json.JSONDecodeError: If the file contains invalid JSON
        IOError: If the file cannot be read or exceeds maximum size
    """
    # Check file size to prevent memory exhaustion
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise IOError(
            f"Session hooks file exceeds maximum size ({MAX_FILE_SIZE} bytes): {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_matcher_field_for_event(event_name: str) -> Optional[str]:
    """
    Get the input field name used for matcher filtering for a given event.

    Different hook events use different input fields for matching:
    - PreCompact: matches against "trigger" field (values: "manual", "auto")
    - SessionStart: matches against "source" field (values: "startup", "resume", "clear", "compact")

    Args:
        event_name: The hook event name

    Returns:
        The field name to match against, or None if no matcher is supported
    """
    matcher_fields = {
        "PreCompact": "trigger",
        "SessionStart": "source",
    }
    return matcher_fields.get(event_name)


def matches_hook_entry(matcher_entry: Dict, event_name: str, input_data: Dict) -> bool:
    """
    Check if a hook entry matches the input data.

    If the hook entry has a "matcher" field and the event supports matchers,
    the matcher value must match the corresponding field in input_data.
    If no matcher is specified, the hook matches all inputs.

    Args:
        matcher_entry: The hook entry with optional "matcher" field
        event_name: The hook event name
        input_data: The original input data from Claude Code

    Returns:
        True if the hook entry matches, False otherwise
    """
    matcher = matcher_entry.get("matcher")
    if not matcher:
        # No matcher specified - matches everything
        return True

    # Get the field to match against for this event
    matcher_field = get_matcher_field_for_event(event_name)
    if not matcher_field:
        # Event doesn't support matchers - ignore the matcher field
        return True

    # Get the value from input data
    input_value = input_data.get(matcher_field, "")

    # Check if matcher matches (case-insensitive)
    return matcher.lower() == str(input_value).lower()


def get_hook_for_event(
    hooks_config: Dict, event_name: str, input_data: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Find the first supported hook for the given event name.

    Supported hook types:
    - "command": Execute a shell command (requires "command" field)
    - "json": Return a fixed JSON response (uses "json" and "exitcode" fields)

    Matcher support for specific events:
    - PreCompact: matcher matches "trigger" field ("manual" or "auto")
    - SessionStart: matcher matches "source" field ("startup", "resume", "clear", "compact")

    The hooks config follows the Claude Code settings schema:
    {
      "hooks": {
        "EventName": [
          {
            "matcher": "optional",  // Optional matcher pattern
            "hooks": [
              {
                "type": "command",
                "command": "...",
                "timeout": 30
              },
              {
                "type": "json",
                "json": {...},
                "exitcode": 0
              }
            ]
          }
        ]
      }
    }

    Args:
        hooks_config: The parsed hooks configuration
        event_name: The hook event name (e.g., "SessionStart")
        input_data: The original input data from Claude Code (for matcher filtering)

    Returns:
        The first supported hook dict, or None if not found
    """
    hooks = hooks_config.get("hooks", {})
    if not isinstance(hooks, dict):
        return None

    event_hooks = hooks.get(event_name, [])
    if not isinstance(event_hooks, list):
        return None

    # Default to empty dict if input_data not provided
    if input_data is None:
        input_data = {}

    # Iterate through hook matchers
    for matcher_entry in event_hooks:
        if not isinstance(matcher_entry, dict):
            continue

        # Check if this hook entry matches the input data
        if not matches_hook_entry(matcher_entry, event_name, input_data):
            continue

        hook_list = matcher_entry.get("hooks", [])
        if not isinstance(hook_list, list):
            continue

        # Find first supported hook (command or json type)
        for hook in hook_list:
            if not isinstance(hook, dict):
                continue
            hook_type = hook.get("type")
            if hook_type == "command" and hook.get("command"):
                return hook
            if hook_type == "json":
                return hook

    return None


def execute_hook_command(
    command: str, input_json: str, timeout: int = DEFAULT_TIMEOUT
) -> Tuple[str, str, int]:
    """
    Execute the hook command with timeout.

    The original JSON input is passed to the command via stdin,
    allowing the hook command to access all input data.

    Args:
        command: The shell command to execute
        input_json: The original JSON input string to pass via stdin
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (stdout, stderr, exit_code)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            input=input_json,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Hook command timed out after {timeout} seconds", 1
    except Exception as e:
        return "", f"Failed to execute hook command: {e}", 1


def execute_json_hook(hook: Dict) -> Tuple[str, str, int]:
    """
    Execute a JSON-type hook by returning a fixed JSON response.

    Args:
        hook: The hook configuration containing optional "json" and "exitcode" fields

    Returns:
        Tuple of (json_output, stderr, exit_code)
    """
    # Get the JSON to return (default to empty object)
    json_output = hook.get("json", {})

    # Validate json_output is a dict or can be serialized
    if not isinstance(json_output, dict):
        return "", "Invalid 'json' field: must be an object", 1

    # Get the exit code (default to 0)
    exit_code = hook.get("exitcode", 0)

    # Validate exit_code is an integer
    if not isinstance(exit_code, int):
        try:
            exit_code = int(exit_code)
        except (ValueError, TypeError):
            exit_code = 0

    # Serialize the JSON output
    try:
        output = json.dumps(json_output)
        return output, "", exit_code
    except (TypeError, ValueError) as e:
        return "", f"Failed to serialize JSON output: {e}", 1


def main():
    """Main entry point for the session hook script."""
    try:
        # Read JSON input from stdin
        input_text = sys.stdin.read()
        input_data = json.loads(input_text)

        # Validate input is a dictionary
        if not isinstance(input_data, dict):
            print("{}")
            sys.exit(0)

        # Extract session_id and hook_event_name
        session_id = input_data.get("session_id", "")
        hook_event_name = input_data.get("hook_event_name", "")

        # Validate session_id
        if not validate_session_id(session_id):
            print("{}")
            sys.exit(0)

        # Find session hooks file
        hooks_file = find_session_hooks_file(session_id)
        if not hooks_file:
            print("{}")
            sys.exit(0)

        # Load hooks configuration
        try:
            hooks_config = load_hooks_config(hooks_file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading session hooks file: {e}", file=sys.stderr)
            sys.exit(1)

        # Find hook for the event (pass input_data for matcher filtering)
        hook = get_hook_for_event(hooks_config, hook_event_name, input_data)
        if not hook:
            print("{}")
            sys.exit(0)

        # Determine hook type and execute accordingly
        hook_type = hook.get("type", "command")

        if hook_type == "json":
            # Execute JSON hook - return fixed JSON response
            stdout, stderr, exit_code = execute_json_hook(hook)
        else:
            # Execute command hook (default)
            command = hook.get("command", "")
            timeout = hook.get("timeout", DEFAULT_TIMEOUT)

            # Validate timeout (must be positive and not exceed MAX_TIMEOUT)
            if (
                not isinstance(timeout, (int, float))
                or timeout <= 0
                or timeout > MAX_TIMEOUT
            ):
                timeout = DEFAULT_TIMEOUT

            stdout, stderr, exit_code = execute_hook_command(
                command, input_text, int(timeout)
            )

        # Output results
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, file=sys.stderr, end="")

        sys.exit(exit_code)

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
