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
Claude Code Hook: Block Dangerous Tool Usages

This hook script intercepts and blocks dangerous tool usages, providing an additional
layer of safety when using Claude Code CLI. Supports both PreToolUse and PermissionRequest
hook events.

Security Categories:
-------------------
1. Dangerous rm commands:
   - Blocks `rm -rf` targeting system-critical paths (/, ~, $HOME, etc.)
   - Allows safe operations like `rm -rf ./build` or `rm -rf *.log`
   - Uses context-aware pattern matching to reduce false positives

2. Dangerous git commands:
   - Blocks destructive operations: reset --hard, clean -f/-fd/-fx, force push
   - Prevents accidental data loss from repository operations
   - Allows safe git operations like status, add, commit, pull

3. Sensitive file access:
   - Asks for confirmation when accessing .env files (may contain secrets)
   - Allows default*.env and .env.example files without prompting
   - Prevents accidental exposure of API keys and credentials

Hook Event Types:
----------------
This script supports two hook event types:

1. PreToolUse (default):
   - Intercepts tool calls before execution
   - Can deny, ask, or allow operations

2. PermissionRequest:
   - Controls permission requests shown to users
   - Can allow (optionally with modified input) or deny (with message and interrupt)

Input Format:
------------
Input (via stdin): JSON with hook event type, tool_name and tool_input
Full example payload:
  {
    "session_id": "abc123",
    "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
    "cwd": "/Users/...",
    "permission_mode": "default",
    "hook_event_name": "PreToolUse",  # or "PermissionRequest" (defaults to "PreToolUse" if omitted)
    "tool_name": "Write",
    "tool_input": {
      "file_path": "/path/to/file.txt",
      "content": "file content"
    },
    "tool_use_id": "toolu_01ABC123..."
  }

Minimal example:
  {
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "rm -rf /"}
  }

Output Formats:
--------------
PreToolUse output:
  {
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny|ask|allow",
      "permissionDecisionReason": "Reason for decision"
    }
  }

PermissionRequest output (allow):
  {
    "hookSpecificOutput": {
      "hookEventName": "PermissionRequest",
      "decision": {
        "behavior": "allow",
        "updatedInput": {...}  # Optional: modified tool parameters
      }
    }
  }

PermissionRequest output (deny):
  {
    "hookSpecificOutput": {
      "hookEventName": "PermissionRequest",
      "decision": {
        "behavior": "deny",
        "message": "Reason for denial",  # Optional
        "interrupt": true  # Optional: stop Claude
      }
    }
  }

Usage Modes:
-----------
1. Default mode (recommended):
   - Blocks dangerous operations with "deny" decision
   - Asks for .env file access with "ask" decision (PreToolUse) or "allow" (PermissionRequest)
   - Exits with code 0 (no output) for safe operations
   - Claude's permission system decides how to handle safe operations

2. Auto-allow mode (--and-auto-allow):
   - Explicitly outputs "allow" decision for safe operations
   - Use with caution as it bypasses the permission system

Exit Codes:
----------
- 0: Success (either safe operation or explicit decision made)
- Non-zero: Error occurred (malformed input, unexpected exception)
"""

import argparse
import json
import os
import sys
import re
import shlex

def classify_path(path: str) -> str:
    stripped = path.strip()
    lowered_path = stripped.lower()

    if not stripped or lowered_path in {'', '*'}:
        return 'dangerous'

    if lowered_path in {'.'}:
        return 'dangerous'

    # Parent traversal gets flagged as potentially dangerous.
    if lowered_path in {'..', '../'}:
        return 'potential'
    if lowered_path.startswith('../') or lowered_path.startswith('..\\'):
        return 'potential'
    if '/../' in lowered_path or '\\..' in lowered_path:
        return 'potential'
    if lowered_path.endswith('/..') or lowered_path.endswith('\\..'):
        return 'potential'

    # Home directory variants.
    if lowered_path.startswith('~'):
        return 'dangerous'
    if lowered_path.startswith('$home') or lowered_path.startswith('${home'):
        return 'dangerous'

    # Wildcard handling: allow filename globs, treat broad absolute globs as dangerous.
    if '*' in lowered_path:
        if lowered_path.strip('*') == '':
            return 'dangerous'
        if lowered_path.startswith('/'):
            wildcard_prefix_policies = {
                '/tmp/': 'potential',
                '/var/log/': 'potential',
                '/workspace/': 'potential',
                '/workspaces/': 'potential',
            }
            for prefix, classification in wildcard_prefix_policies.items():
                if lowered_path.startswith(prefix):
                    return classification
            return 'dangerous'
        return 'safe'

    # Absolute paths: allow general use except for critical system locations.
    if lowered_path.startswith('/'):
        safe_absolute_prefixes = ('/tmp', '/var/log')
        if any(lowered_path == prefix or lowered_path.startswith(f'{prefix}/') for prefix in safe_absolute_prefixes):
            return 'safe'

        high_risk_roots = (
            '/',
            '/bin', '/boot', '/dev', '/etc', '/lib', '/lib32', '/lib64',
            '/proc', '/root', '/run', '/sbin', '/sys', '/usr', '/var/lib', '/var/run',
        )
        if any(lowered_path == root or lowered_path.startswith(f'{root}/') for root in high_risk_roots):
            return 'dangerous'

        workspace_roots = ('/workspace', '/workspaces')
        if any(lowered_path == root for root in workspace_roots):
            return 'dangerous'
        if any(lowered_path.startswith(f'{root}/') for root in workspace_roots):
            return 'potential'

        return 'safe'

    # Relative project-scoped allowances.
    if lowered_path.startswith('./'):
        return 'safe'

    # Extensions on files (e.g. file.txt) are typically safe.
    if '.' in lowered_path and not lowered_path.startswith('.'):
        return 'safe'

    # Default: treat as dangerous (e.g., plain directory names).
    return 'dangerous'

def is_dangerous_rm_command(command) -> int:
    """
    Detect dangerous ``rm`` commands that could cause data loss.

    The heuristic errs on the side of caution:
      * Any invocation that combines recursive *and* force flags is inspected.
      * Commands that clearly target system roots (/, ~, $HOME, /workspaces, .., .)
        or broad globs like ``*`` are denied outright (return 2).
      * Commands aimed at project-scoped paths such as ``./build`` or filename
        patterns like ``*.log`` are allowed (return 0).
    """
    command = command.strip()
    if not command:
        return 0

    try:
        tokens = shlex.split(command)
    except ValueError:
        # Fallback to simple splitting if the command cannot be parsed safely.
        tokens = command.split()

    if not tokens:
        return 0

    lowered = [token.lower() for token in tokens]
    if lowered[0] != 'rm':
        return 0

    has_force = False
    has_recursive = False
    used_long_force = False
    used_long_recursive = False
    paths = []

    idx = 1
    while idx < len(tokens):
        token = tokens[idx]
        token_lower = lowered[idx]

        if token_lower == '--':
            paths.extend(tokens[idx + 1 :])
            break

        if token_lower.startswith('--'):
            if token_lower == '--force' or token_lower.startswith('--force='):
                has_force = True
                used_long_force = True
            elif token_lower == '--recursive' or token_lower.startswith('--recursive='):
                has_recursive = True
                used_long_recursive = True
            idx += 1
            continue

        if token_lower.startswith('-') and len(token_lower) > 1:
            for flag_char in token_lower[1:]:
                if flag_char == 'f':
                    has_force = True
                if flag_char == 'r':
                    has_recursive = True
            idx += 1
            continue

        paths.append(token)
        idx += 1

    if not (has_force and has_recursive):
        return 0

    # Long-form flags are rare in safe cleanups; treat them as high risk.
    if used_long_force or used_long_recursive:
        return 2

    if not paths:
        # "rm -rf" without specific target is catastrophic.
        return 2

    for path in paths:
        classification = classify_path(path)
        if classification == 'dangerous':
            return 2
        if classification == 'potential':
            return 1

    # No broad denials triggered; command is considered safe.
    return 0

def is_dangerous_git_command(command):
    """
    Detect dangerous git commands that could cause data loss or repository corruption.

    Security rationale:
    - git reset --hard: Discards all uncommitted changes permanently
    - git clean -f/-fx/-fX: Removes untracked/ignored files permanently
    - git push --force: Rewrites remote history, can lose others' work
    - git reflog expire: Removes recovery points for deleted commits

    Examples of blocked commands:
        - git reset --hard   # Discards uncommitted changes
        - git clean -f       # Removes untracked files
        - git clean -fd      # Removes untracked files and directories
        - git push --force   # Force pushes to remote

    Examples of allowed commands:
        - git status         # Safe read-only operation
        - git add .          # Stages changes
        - git commit -m ...  # Creates commit
        - git clean -n       # Dry-run (safe preview)

    Args:
        command (str): The git command to analyze

    Returns:
        bool: True if the command is dangerous and should be blocked, False otherwise
    """
    normalized = ' '.join(command.lower().split())
    patterns = [
        r'git\s+reset\s+--hard',  # git reset --hard
        # git clean patterns - all variants with -f are destructive:
        # -f alone removes untracked files
        # -fx removes untracked + ignored files
        # -fX removes only ignored files
        # -fd/-df removes untracked files and directories
        r'git\s+clean\s+-[a-z]*f[a-z]*d',  # git clean with f before d: -fd, -fxd, -fdx, etc.
        r'git\s+clean\s+-[a-z]*d[a-z]*f',  # git clean with d before f: -df, -dxf, -dfx, -xdf, etc.
        r'git\s+clean\s+-f[a-z]*(?:\s|$)',  # git clean -f/-fx/-fX: destructive even without -d
        r'git\s+reflog\s+expire\s+--expire=now\s+--all',  # git reflog expire --expire=now --all
        r'git\s+push\s+--force',  # git push --force
        r'git\s+push\s+-f',  # git push -f
        r'git\s+branch\s+-d\s+.*',  # git branch -d <branch>
        r'git\s+branch\s+-D\s+.*',  # git branch -D <branch>
        r'git\s+tag\s+-d\s+.*',  # git tag -d <tag>
        r'git\s+remote\s+remove\s+.*',  # git remote remove <name>
        r'git\s+filter-branch',  # git filter-branch
        r'git\s+update-ref\s+-d',  # git update-ref -d
        r'git\s+checkout\s+--orphan',  # git checkout --orphan
    ]
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True
    return False

def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.

    .env files typically contain:
    - API keys and tokens
    - Database credentials
    - Secret keys and passwords
    - Other sensitive configuration

    This function asks for user confirmation before accessing .env files,
    while allowing safe variants like default.env and .env.example.

    Args:
        tool_name (str): Name of the tool being used (e.g., 'Read', 'Bash', 'Edit')
        tool_input (dict): The input parameters for the tool

    Returns:
        bool: True if the tool is trying to access a .env file, False otherwise
    """
    # TODO: support blocking `Grep` tool access to .env files
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            # Ignore if file endswith .env.example
            if file_path.endswith('.env.example'):
                return False
            if '.env' in file_path and not re.search(r'default(\..*)?\.env$', file_path):
                return True
        
        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern to detect .env file access (but allow default*.env and .env.example)
            env_patterns = [
                r'(?<!\w)\.env(?!\w)(?!default(\..*)?\.env)(?!\.example)',  # .env but not default*.env or .env.example
                r'cat\s+.*(?<!\w)\.env(?!\w)(?!default(\..*)?\.env)(?!\.example)',  # cat .env
                r'echo\s+.*>\s*(?<!\w)\.env(?!\w)(?!default(\..*)?\.env)(?!\.example)',  # echo > .env
                r'touch\s+.*(?<!\w)\.env(?!\w)(?!default(\..*)?\.env)(?!\.example)',  # touch .env
                r'cp\s+.*(?<!\w)\.env(?!\w)(?!default(\..*)?\.env)(?!\.example)',  # cp .env
                r'mv\s+.*(?<!\w)\.env(?!\w)(?!default(\..*)?\.env)(?!\.example)',  # mv .env
            ]
            
            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True
    
    return False

def output_decision(decision, reason=None):
    """
    Output a permission decision in the expected JSON format.

    This function formats and prints the permission decision that Claude Code
    will use to determine whether to allow, deny, or ask about a tool usage.

    Args:
        decision (str): The permission decision - one of "allow", "deny", or "ask"
        reason (str, optional): Human-readable explanation for the decision

    Output format (to stdout):
        {
          "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny|ask|allow",
            "permissionDecisionReason": "Optional reason string"
          }
        }
    """
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }

    if reason:
        payload["hookSpecificOutput"]["permissionDecisionReason"] = reason

    print(json.dumps(payload))

def output_permission_request_decision(behavior, updated_input=None, message=None, interrupt=False):
    """
    Output a PermissionRequest decision in the expected JSON format.

    This function formats and prints the PermissionRequest decision that Claude Code
    will use to determine whether to allow or deny a permission request shown to the user.

    Args:
        behavior (str): The decision behavior - one of "allow" or "deny"
        updated_input (dict, optional): For "allow" behavior, modified tool input parameters
        message (str, optional): For "deny" behavior, explanation for why permission was denied
        interrupt (bool, optional): For "deny" behavior, whether to stop Claude (default: False)

    Output format (to stdout):
        For "allow" behavior:
        {
          "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
              "behavior": "allow",
              "updatedInput": {...}  # Optional
            }
          }
        }

        For "deny" behavior:
        {
          "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
              "behavior": "deny",
              "message": "Reason for denial",  # Optional
              "interrupt": true/false  # Optional
            }
          }
        }
    """
    decision = {"behavior": behavior}

    if behavior == "allow" and updated_input is not None:
        decision["updatedInput"] = updated_input
    elif behavior == "deny":
        if message is not None:
            decision["message"] = message
        if interrupt:
            decision["interrupt"] = interrupt

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": decision,
        }
    }

    print(json.dumps(payload))

def output_unified_decision(hook_event, decision_type, reason=None, updated_input=None, interrupt=False):
    """
    Unified decision output that routes to the correct format based on hook event type.

    Args:
        hook_event (str): The hook event type ("PreToolUse" or "PermissionRequest")
        decision_type (str): The decision - "allow", "deny", or "ask" (for PreToolUse only)
        reason (str, optional): Reason for the decision
        updated_input (dict, optional): For PermissionRequest allow, modified tool input
        interrupt (bool, optional): For PermissionRequest deny, whether to stop Claude
    """
    if hook_event == 'PermissionRequest':
        # Map decision types to PermissionRequest behaviors
        if decision_type == 'deny':
            output_permission_request_decision("deny", message=reason, interrupt=interrupt)
        elif decision_type == 'allow':
            # For 'ask', we allow and let the permission system handle the user prompt
            output_permission_request_decision("allow", updated_input=updated_input)
        else: # e.g: decision_type = 'ask'
            # PermissionRequest does not support 'ask' in output
            # So to retain the same behavior, we simply exit with code 0
            sys.exit(0)  # exit with code 0 (safe operation, no explicit action)
    else:
        # PreToolUse format
        output_decision(decision_type, reason)

def load_settings_from_path(path):
    """Best-effort JSON loader that returns a dict or an empty default."""
    if not path or not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        if isinstance(data, dict):
            return data
    except Exception:
        # Caller decides how to handle missing/invalid config data.
        pass

    return {}

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Hook script to block dangerous tool usages',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--and-auto-allow',
        action='store_true',
        help='Explicitly allow safe operations (bypasses permission system). '
             'By default, only blocks dangerous operations and exits with code 0 for safe ones.'
    )
    args = parser.parse_args()

    # Allow configuration-based override for auto-allow behavior.
    # Repository-local settings override user-level defaults.
    global_config_path = os.path.join(os.path.expanduser("~"), ".gosu", "settings.json")
    local_config_path = os.path.join(os.getcwd(), ".gosu", "settings.json")

    merged_config = load_settings_from_path(global_config_path)
    merged_config.update(load_settings_from_path(local_config_path))

    if merged_config.get("autoAllowNonDangerousToolUsage") is True:
        args.and_auto_allow = True

    # Initialize hook_event to None for error handling
    hook_event = None

    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Detect the hook event type (defaults to PreToolUse for backwards compatibility)
        hook_event = input_data.get('hook_event_name', 'PreToolUse')

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Validate that tool_input is a dictionary
        if not isinstance(tool_input, dict):
            output_unified_decision(
                hook_event,
                "deny",
                reason="Invalid tool_input format: expected a dictionary",
                interrupt=True
            )
            return

        # Check for .env file access (ask user for confirmation)
        if is_env_file_access(tool_name, tool_input):
            output_unified_decision(
                hook_event,
                "ask",
                reason="This tool is attempting to access .env files which may contain sensitive data. Do you want to allow this access?"
            )
            return

        # Check for dangerous rm -rf commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')

            # Block rm -rf commands with comprehensive pattern matching
            result_check =  is_dangerous_rm_command(command)
            if result_check == 2:
                output_unified_decision(
                    hook_event,
                    "deny",
                    reason="Dangerous rm command detected and prevented.",
                    interrupt=True
                )
                return
            elif result_check == 1:
                output_unified_decision(
                    hook_event,
                    "ask",
                    reason="Potentially Dangerous rm command detected. Do you want to run this command?"
                )
                return

            # Block dangerous git commands with comprehensive pattern matching
            if is_dangerous_git_command(command):
                output_unified_decision(
                    hook_event,
                    "deny",
                    reason="Dangerous git command detected and prevented.",
                    interrupt=True
                )
                return

        # If --and-auto-allow flag is set, explicitly allow safe operations
        # This bypasses the permission system for safe operations
        if args.and_auto_allow:
            output_unified_decision(hook_event, "allow")
        # Otherwise, exit with code 0 (safe operation, no explicit action)
        # We use sys.exit(0) here to indicate successful completion with no output,
        # which signals the permission system to pass through without intervention.
        # This is intentional: returning would fall through to the exception handlers,
        # while sys.exit(0) cleanly terminates with success status and no JSON output.
        else:
            sys.exit(0)

    except json.JSONDecodeError as e:
        # Handle JSON decode errors - use detected event type or default to PreToolUse
        event_type = hook_event if hook_event else 'PreToolUse'
        output_unified_decision(
            event_type,
            "deny",
            reason=f"Failed to parse JSON input: {e}",
            interrupt=True
        )
    except Exception as e:
        # Handle any other errors - use detected event type or default to PreToolUse
        event_type = hook_event if hook_event else 'PreToolUse'
        output_unified_decision(
            event_type,
            "deny",
            reason=f"Unexpected error occurred: {e}",
            interrupt=True
        )

if __name__ == '__main__':
    main()
