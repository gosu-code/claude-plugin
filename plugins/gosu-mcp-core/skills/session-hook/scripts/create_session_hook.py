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
Session Hook Creator

Creates session-specific hook files for Claude Code.

Usage:
    python3 create_session_hook.py <session_id> <event> <hook_type> [options]

Examples:
    # Block stopping with a message
    python3 create_session_hook.py abc123 Stop json --decision block --reason "Run tests first"

    # Inject context on session start
    python3 create_session_hook.py abc123 SessionStart json --message "Welcome!"

    # Add command hook
    python3 create_session_hook.py abc123 PostToolUse command --command "tee -a /tmp/log.json"

    # With matcher
    python3 create_session_hook.py abc123 SessionStart json --matcher startup --message "New session!"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# UUID regex pattern for session_id validation
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

# Supported hook events
HOOK_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "Notification",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
    "SessionStart",
    "SessionEnd",
]

# Events that support matchers
MATCHER_EVENTS = {
    "SessionStart": ["startup", "resume", "clear", "compact"],
    "PreCompact": ["manual", "auto"],
}


def validate_session_id(session_id: str) -> bool:
    """Validate that session_id is a valid UUID format."""
    return bool(UUID_PATTERN.match(session_id))


def get_hooks_file_path(session_id: str, global_scope: bool = False) -> Path:
    """Get the path to the session hooks file."""
    filename = f"hooks.{session_id}.json"

    if global_scope:
        return Path.home() / ".claude" / "hooks" / filename
    else:
        return Path(".claude") / "hooks" / filename


def load_existing_hooks(file_path: Path) -> Dict:
    """Load existing hooks from file or return empty structure."""
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"hooks": {}}


def create_json_hook(
    decision: Optional[str] = None,
    reason: Optional[str] = None,
    message: Optional[str] = None,
    exitcode: int = 0,
) -> Dict[str, Any]:
    """Create a JSON-type hook configuration."""
    hook: Dict[str, Any] = {"type": "json"}

    json_content: Dict[str, Any] = {}

    if decision:
        json_content["decision"] = decision
    if reason:
        json_content["reason"] = reason
    if message:
        json_content["systemMessage"] = message

    if json_content:
        hook["json"] = json_content

    if exitcode != 0:
        hook["exitcode"] = exitcode

    return hook


def create_command_hook(
    command: str,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Create a command-type hook configuration."""
    hook: Dict[str, Any] = {
        "type": "command",
        "command": command,
    }

    if timeout != 15:
        hook["timeout"] = timeout

    return hook


def add_hook_to_config(
    config: Dict,
    event: str,
    hook: Dict[str, Any],
    matcher: Optional[str] = None,
) -> Dict:
    """Add a hook to the configuration."""
    if "hooks" not in config:
        config["hooks"] = {}

    if event not in config["hooks"]:
        config["hooks"][event] = []

    # Create hook entry with optional matcher
    hook_entry: Dict[str, Any] = {"hooks": [hook]}

    if matcher:
        hook_entry["matcher"] = matcher

    config["hooks"][event].append(hook_entry)

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Create session-specific hook files for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Block stopping with a message
    python3 create_session_hook.py SESSION_ID Stop json --decision block --reason "Run tests first"

    # Inject context on session start
    python3 create_session_hook.py SESSION_ID SessionStart json --message "Welcome!"

    # Add command hook for logging
    python3 create_session_hook.py SESSION_ID PostToolUse command --command "tee -a /tmp/log.json"

    # With matcher for new sessions only
    python3 create_session_hook.py SESSION_ID SessionStart json --matcher startup --message "New session!"

    # Global scope (user home directory)
    python3 create_session_hook.py SESSION_ID Stop json --global --decision block --reason "Tests required"
""",
    )

    parser.add_argument(
        "session_id",
        help="Session ID (UUID format)",
    )
    parser.add_argument(
        "event",
        choices=HOOK_EVENTS,
        help="Hook event type",
    )
    parser.add_argument(
        "hook_type",
        choices=["json", "command"],
        help="Hook type (json or command)",
    )

    # Scope options
    parser.add_argument(
        "--global",
        dest="global_scope",
        action="store_true",
        help="Create hook in ~/.claude/hooks/ instead of ./.claude/hooks/",
    )

    # JSON hook options
    parser.add_argument(
        "--decision",
        choices=["approve", "block"],
        help="Decision for Stop/SubagentStop hooks",
    )
    parser.add_argument(
        "--reason",
        help="Reason for the decision",
    )
    parser.add_argument(
        "--message",
        help="System message to inject",
    )
    parser.add_argument(
        "--exitcode",
        type=int,
        default=0,
        help="Exit code for JSON hook (default: 0)",
    )

    # Command hook options
    parser.add_argument(
        "--command",
        help="Shell command to execute (required for command hook)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Command timeout in seconds (default: 15, max: 60)",
    )

    # Matcher option
    parser.add_argument(
        "--matcher",
        help="Matcher value for SessionStart or PreCompact events",
    )

    # Output options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the hook configuration without writing to file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing hooks for the same event",
    )

    args = parser.parse_args()

    # Validate session_id
    if not validate_session_id(args.session_id):
        print(f"Error: Invalid session ID format: {args.session_id}", file=sys.stderr)
        print("Session ID must be a valid UUID format.", file=sys.stderr)
        sys.exit(1)

    # Validate matcher
    if args.matcher:
        if args.event not in MATCHER_EVENTS:
            print(
                f"Error: Event '{args.event}' does not support matchers.",
                file=sys.stderr,
            )
            print(
                f"Matcher-supported events: {', '.join(MATCHER_EVENTS.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)

        valid_matchers = MATCHER_EVENTS[args.event]
        if args.matcher not in valid_matchers:
            print(
                f"Error: Invalid matcher '{args.matcher}' for {args.event}.",
                file=sys.stderr,
            )
            print(f"Valid matchers: {', '.join(valid_matchers)}", file=sys.stderr)
            sys.exit(1)

    # Create hook based on type
    if args.hook_type == "json":
        hook = create_json_hook(
            decision=args.decision,
            reason=args.reason,
            message=args.message,
            exitcode=args.exitcode,
        )
    else:
        if not args.command:
            print(
                "Error: --command is required for command hook type.", file=sys.stderr
            )
            sys.exit(1)

        timeout = min(args.timeout, 60)  # Cap at 60 seconds
        hook = create_command_hook(command=args.command, timeout=timeout)

    # Get file path
    file_path = get_hooks_file_path(args.session_id, args.global_scope)

    # Load or create config
    if args.force or not file_path.exists():
        config: Dict = {"hooks": {}}
    else:
        config = load_existing_hooks(file_path)

    # Add hook to config
    config = add_hook_to_config(config, args.event, hook, args.matcher)

    # Output
    if args.dry_run:
        print(json.dumps(config, indent=2))
        print(f"\nWould write to: {file_path}", file=sys.stderr)
    else:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write config
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")

        print(f"Session hook created: {file_path}")
        print(f"Event: {args.event}")
        print(f"Hook type: {args.hook_type}")
        if args.matcher:
            print(f"Matcher: {args.matcher}")
        print("\nHook configuration:")
        print(json.dumps(hook, indent=2))


if __name__ == "__main__":
    main()
